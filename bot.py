"""Telegram Bridge cho Google Antigravity (qua Antigravity CLI `agy`).

Bot khởi chạy `agy acp` (Agent Client Protocol, JSON-RPC qua stdio) và chuyển
tiếp tin nhắn Telegram <-> Antigravity agent. Xác thực bằng tài khoản Google đã
đăng nhập trong `agy` (không cần API key).

Tính năng:
- Whitelist Telegram User ID (bắt buộc).
- Phiên hội thoại được lưu lại: bot khởi động lại vẫn tiếp tục đúng phiên cũ.
- Agent xin phép (lệnh shell, sửa file ngoài workspace...) -> nút bấm trên Telegram.
- Hiển thị tiến trình realtime, /stop để huỷ, đổi model / mode, xem & mở lại các
  phiên cũ (kể cả phiên tạo trong app Antigravity).
- Gửi ảnh kèm caption; các lệnh lạ như /goal, /plan được chuyển thẳng cho agent.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import html
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------
def _resolve_agy_path() -> str:
    env_val = os.getenv("AGY_PATH", "").strip()
    if env_val:
        expanded = os.path.expanduser(env_val)
        if os.path.isfile(expanded):
            return expanded
    found = shutil.which("agy")
    if found:
        return found
    candidates = [
        os.path.expanduser("~/.local/bin/agy"),
        os.path.expanduser("~/.local/bin/agy.exe"),
        os.path.expanduser("~/.local/bin/agy.cmd"),
    ]
    if os.name == "nt":
        local_app = os.getenv("LOCALAPPDATA", "")
        if local_app:
            candidates.append(os.path.join(local_app, "Programs", "Antigravity", "bin", "agy.cmd"))
            candidates.append(os.path.join(local_app, "Programs", "Antigravity", "bin", "agy.exe"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return os.path.expanduser(env_val or "~/.local/bin/agy")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_IDS = {
    int(x) for x in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x
}
AGY_PATH = _resolve_agy_path()
_DEFAULT_WS_FALLBACK = "~/AN_Projects" if os.path.isdir(os.path.expanduser("~/AN_Projects")) else "~"
DEFAULT_WORKSPACE = os.path.expanduser(os.getenv("DEFAULT_WORKSPACE", _DEFAULT_WS_FALLBACK))
PROJECTS_ROOT = os.path.expanduser(os.getenv("PROJECTS_ROOT", DEFAULT_WORKSPACE))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "").strip() or None
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "accept-edits").strip() or None
AUTO_APPROVE_DEFAULT = os.getenv("AUTO_APPROVE", "false").lower() in ("1", "true", "yes")
APPROVAL_TIMEOUT = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "600"))
STATE_FILE = BASE_DIR / "data" / "state.json"

MAX_TG_LEN = 4000
PROGRESS_EDIT_INTERVAL = 2.0

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("agy-bridge")


# ---------------------------------------------------------------------------
# ACP client (JSON-RPC 2.0 qua stdio của `agy acp`)
# ---------------------------------------------------------------------------
class AcpError(Exception):
    pass


class AcpClient:
    def __init__(
        self,
        cwd: str,
        on_update: Callable[[dict], None],
        on_permission: Callable[[dict], Awaitable[dict]],
    ):
        self.cwd = cwd
        self.on_update = on_update
        self.on_permission = on_permission
        self.proc: asyncio.subprocess.Process | None = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._tasks: list[asyncio.Task] = []

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def start(self) -> dict:
        self.proc = await asyncio.create_subprocess_exec(
            AGY_PATH, "acp", "--app-data-dir", "antigravity",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            limit=64 * 1024 * 1024,
        )
        self._tasks = [
            asyncio.create_task(self._read_stdout()),
            asyncio.create_task(self._read_stderr()),
        ]
        return await self.request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {
                    "fs": {"readTextFile": False, "writeTextFile": False},
                    "terminal": False,
                },
                "clientInfo": {"name": "telegram-bridge", "version": "1.0"},
            },
        )

    async def stop(self) -> None:
        if self.alive:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError:
                self.proc.kill()
        for t in self._tasks:
            t.cancel()
        self._fail_pending(AcpError("agy đã dừng"))

    async def _write(self, obj: dict) -> None:
        if not self.alive:
            raise AcpError("Tiến trình agy không chạy")
        self.proc.stdin.write((json.dumps(obj) + "\n").encode())
        await self.proc.stdin.drain()

    async def request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        rid = self._next_id
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        await self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return await fut

    async def notify(self, method: str, params: dict) -> None:
        await self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _fail_pending(self, exc: Exception) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(exc)
        self._pending.clear()

    async def _handle_agent_request(self, msg: dict) -> None:
        method, rid = msg.get("method"), msg.get("id")
        try:
            if method == "session/request_permission":
                result = await self.on_permission(msg.get("params", {}))
                await self._write({"jsonrpc": "2.0", "id": rid, "result": result})
            else:
                await self._write({
                    "jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"Method not supported: {method}"},
                })
        except Exception:  # noqa: BLE001
            log.exception("Lỗi xử lý request %s", method)
            with contextlib.suppress(Exception):
                await self._write({
                    "jsonrpc": "2.0", "id": rid,
                    "result": {"outcome": {"outcome": "cancelled"}},
                })

    async def _read_stdout(self) -> None:
        assert self.proc and self.proc.stdout
        try:
            while line := await self.proc.stdout.readline():
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    log.debug("agy (non-json): %s", line[:200])
                    continue
                if "method" in msg and "id" in msg:
                    asyncio.create_task(self._handle_agent_request(msg))
                elif "method" in msg:
                    if msg["method"] == "session/update":
                        try:
                            self.on_update(msg.get("params", {}))
                        except Exception:  # noqa: BLE001
                            log.exception("Lỗi xử lý session/update")
                elif msg.get("id") in self._pending:
                    fut = self._pending.pop(msg["id"])
                    if fut.done():
                        continue
                    if "error" in msg:
                        err = msg["error"]
                        fut.set_exception(AcpError(err.get("message") or str(err)))
                    else:
                        fut.set_result(msg.get("result") or {})
        finally:
            log.warning("agy acp đã thoát (code=%s)", self.proc.returncode if self.proc else None)
            self._fail_pending(AcpError("Tiến trình agy đã thoát"))

    async def _read_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        while line := await self.proc.stderr.readline():
            log.debug("agy stderr: %s", line.decode(errors="replace").rstrip())


# ---------------------------------------------------------------------------
# Trạng thái lưu trữ
# ---------------------------------------------------------------------------
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {str(cid): s.to_dict() for cid, s in SESSIONS.items()}
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ---------------------------------------------------------------------------
# Đồng bộ Project ID với ứng dụng Antigravity trên máy tính
# ---------------------------------------------------------------------------
GEMINI_DIR = Path.home() / ".gemini"
PROJECTS_CONFIG_DIR = GEMINI_DIR / "config" / "projects"
AGY_DATA_DIR = GEMINI_DIR / "antigravity"
CLI_DEFAULT_PROJECT_ID = "default-cli-project"


def _uri_to_path(uri: str) -> str | None:
    if not uri or not uri.startswith("file://"):
        return None
    raw = urllib.parse.unquote(uri[len("file://") :])
    # Trên Windows, URI dạng file:///C:/Users/... sau khi cắt file:// sẽ thành /C:/Users/...
    if os.name == "nt" and len(raw) >= 3 and raw[0] == "/" and raw[2] == ":":
        raw = raw[1:]
    return os.path.normpath(os.path.abspath(raw))


def resolve_project_for_workspace(workspace: str, auto_create: bool = True) -> tuple[str, str] | None:
    """Tìm (project_id, project_name) trong ~/.gemini/config/projects khớp với workspace.
    Nếu chưa có project riêng cho thư mục con, tự tạo cấu hình project mới để App hiển thị.
    """
    ws_norm = os.path.normpath(os.path.abspath(workspace))
    ws_cmp = os.path.normcase(ws_norm)
    best_match: tuple[int, str, str] | None = None

    if PROJECTS_CONFIG_DIR.is_dir():
        for pfile in PROJECTS_CONFIG_DIR.glob("*.json"):
            if pfile.name == f"{CLI_DEFAULT_PROJECT_ID}.json":
                continue
            try:
                cfg = json.loads(pfile.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            pid = cfg.get("id")
            pname = cfg.get("name") or pid
            if not pid:
                continue
            resources = (cfg.get("projectResources") or {}).get("resources") or []
            for r in resources:
                furi = r.get("folderUri") or (r.get("gitFolder") or {}).get("folderUri")
                fpath = _uri_to_path(furi) if furi else None
                if not fpath:
                    continue
                fpath_cmp = os.path.normcase(fpath)
                if ws_cmp == fpath_cmp:
                    return (pid, pname)
                if ws_cmp.startswith(fpath_cmp + os.sep):
                    if best_match is None or len(fpath) > best_match[0]:
                        best_match = (len(fpath), pid, pname)

    # Nếu workspace là một dự án con trong PROJECTS_ROOT mà chưa có project riêng trên App
    projects_root_cmp = os.path.normcase(os.path.normpath(os.path.abspath(PROJECTS_ROOT)))
    if auto_create and ws_cmp != projects_root_cmp and os.path.isdir(ws_norm):
        try:
            PROJECTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            new_pid = str(uuid.uuid4())
            new_name = os.path.basename(ws_norm)
            folder_uri = Path(ws_norm).as_uri()
            cfg = {
                "id": new_pid,
                "name": new_name,
                "projectResources": {"resources": [{"folderUri": folder_uri}]},
                "permissionGrants": {"v2Migrated": True},
                "settings": {},
                "isWorkspaceOnly": False,
            }
            (PROJECTS_CONFIG_DIR / f"{new_pid}.json").write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            log.info("Đã tạo cấu hình Project Antigravity mới: %s (%s)", new_name, new_pid)
            return (new_pid, new_name)
        except OSError:
            log.exception("Không thể tạo file project cho %s", ws_norm)

    if best_match:
        return (best_match[1], best_match[2])
    return None


def _encode_varint(val: int) -> bytes:
    out = bytearray()
    while val > 0x7F:
        out.append((val & 0x7F) | 0x80)
        val >>= 7
    out.append(val & 0x7F)
    return bytes(out)


def _replace_proto_project_id(blob: bytes | None, old_pid: str, new_pid: str) -> bytes | None:
    if not blob:
        return blob
    old_b = old_pid.encode("utf-8")
    new_b = new_pid.encode("utf-8")
    # Field 18 (string): wire tag 0x92 0x01 + varint length + utf8 bytes
    old_tag = b"\x92\x01" + _encode_varint(len(old_b)) + old_b
    new_tag = b"\x92\x01" + _encode_varint(len(new_b)) + new_b
    if old_tag in blob:
        return blob.replace(old_tag, new_tag)
    return blob


def sync_antigravity_projects(target_session_id: str | None = None, target_workspace: str | None = None) -> None:
    """Chuyển các phiên tạo từ CLI (default-cli-project) sang đúng Project trên App Máy tính
    và đồng bộ file cache protobuf (agyhub_summaries_proto.pb / jetbox_summaries_proto.pb).
    """
    summary_db = AGY_DATA_DIR / "conversation_summaries.db"
    if not summary_db.is_file():
        return

    try:
        conn = sqlite3.connect(str(summary_db), timeout=5.0)
    except sqlite3.Error:
        log.exception("Không mở được conversation_summaries.db")
        return

    updated_any = False
    try:
        with conn:
            rows = conn.execute(
                "SELECT conversation_id, workspace_uris, project_id, raw_summary FROM conversation_summaries"
            ).fetchall()

            for cid, ws_uris_json, cur_pid, raw_summary in rows:
                if target_session_id and cid != target_session_id:
                    if cur_pid not in ("", CLI_DEFAULT_PROJECT_ID):
                        continue

                # Xác định workspace của phiên
                ws_path = None
                if cid == target_session_id and target_workspace:
                    ws_path = target_workspace
                else:
                    try:
                        uris = json.loads(ws_uris_json or "[]")
                        if uris:
                            ws_path = _uri_to_path(uris[0])
                    except json.JSONDecodeError:
                        pass

                if not ws_path:
                    continue

                resolved = resolve_project_for_workspace(ws_path, auto_create=(cid == target_session_id))
                if not resolved:
                    continue
                new_pid, _ = resolved
                if cur_pid == new_pid:
                    continue
                if cur_pid not in ("", CLI_DEFAULT_PROJECT_ID) and cid != target_session_id:
                    continue

                old_pid = cur_pid or CLI_DEFAULT_PROJECT_ID
                new_raw = _replace_proto_project_id(raw_summary, old_pid, new_pid)
                conn.execute(
                    "UPDATE conversation_summaries SET project_id = ?, raw_summary = ? WHERE conversation_id = ?",
                    (new_pid, new_raw, cid),
                )
                with contextlib.suppress(sqlite3.Error):
                    conn.execute(
                        "UPDATE conversations_fts SET project = ? WHERE conversation_id = ?",
                        (new_pid, cid),
                    )
                updated_any = True

                # Cập nhật file db riêng của từng phiên
                conv_db = AGY_DATA_DIR / "conversations" / f"{cid}.db"
                if conv_db.is_file():
                    with contextlib.suppress(sqlite3.Error):
                        c2 = sqlite3.connect(str(conv_db), timeout=5.0)
                        try:
                            with c2:
                                r2 = c2.execute(
                                    "SELECT id, data FROM trajectory_metadata_blob"
                                ).fetchall()
                                for mid, mdata in r2:
                                    new_mdata = _replace_proto_project_id(mdata, old_pid, new_pid)
                                    if new_mdata != mdata:
                                        c2.execute(
                                            "UPDATE trajectory_metadata_blob SET data = ? WHERE id = ?",
                                            (new_mdata, mid),
                                        )
                        finally:
                            c2.close()

                log.info("Đã đồng bộ phiên %s sang project %s", cid[:8], new_pid)

            # Đồng bộ các bản ghi raw_summary sang agyhub_summaries_proto.pb & jetbox_summaries_proto.pb
            all_raws = conn.execute(
                "SELECT raw_summary FROM conversation_summaries WHERE raw_summary IS NOT NULL ORDER BY last_modified_time DESC"
            ).fetchall()
            proto_chunks = bytearray()
            for (rblob,) in all_raws:
                if rblob:
                    proto_chunks.extend(b"\x0a" + _encode_varint(len(rblob)) + rblob)
            if proto_chunks:
                for pb_name in ("agyhub_summaries_proto.pb", "jetbox_summaries_proto.pb"):
                    pb_path = AGY_DATA_DIR / pb_name
                    tmp_pb = pb_path.with_suffix(".pb.tmp")
                    with contextlib.suppress(OSError):
                        tmp_pb.write_bytes(bytes(proto_chunks))
                        tmp_pb.replace(pb_path)
    except Exception:  # noqa: BLE001
        log.exception("Lỗi khi đồng bộ project_id cho Antigravity")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Phiên theo từng chat Telegram
# ---------------------------------------------------------------------------
KIND_ICONS = {
    "execute": "💻", "read": "👀", "edit": "✏️", "delete": "🗑️", "move": "📦",
    "search": "🔎", "fetch": "🌐", "think": "💭", "switch_mode": "🔀", "other": "🔧",
}


class Session:
    def __init__(self, app: Application, chat_id: int, saved: dict | None = None):
        saved = saved or {}
        self.app = app
        self.chat_id = chat_id
        self.workspace: str = saved.get("workspace", DEFAULT_WORKSPACE)
        self.session_id: str | None = saved.get("session_id")
        self.model: str | None = saved.get("model", DEFAULT_MODEL)
        self.mode: str | None = saved.get("mode", DEFAULT_MODE)
        self.auto_approve: bool = saved.get("auto_approve", AUTO_APPROVE_DEFAULT)
        self.title: str = saved.get("title", "")
        self.client: AcpClient | None = None
        self.loaded = False  # session_id đã được new/load trong tiến trình hiện tại
        self.available_models: list[dict] = []
        self.task: asyncio.Task | None = None
        self.pending: dict[str, tuple[asyncio.Future, list[dict]]] = {}
        # Bộ thu cho lượt hiện tại
        self._collect: dict | None = None
        self._lock = asyncio.Lock()

    def to_dict(self) -> dict:
        return {
            "workspace": self.workspace, "session_id": self.session_id, "model": self.model,
            "mode": self.mode, "auto_approve": self.auto_approve, "title": self.title,
        }

    @property
    def busy(self) -> bool:
        return self.task is not None and not self.task.done()

    # ----- vòng đời -----
    async def ensure(self) -> AcpClient:
        async with self._lock:
            # agy dùng thư mục của tiến trình làm cwd cho lệnh shell -> đổi workspace thì khởi động lại.
            if self.client is not None and self.client.alive and self.client.cwd != self.workspace:
                await self.client.stop()
                self.client = None
            if self.client is None or not self.client.alive:
                self.client = AcpClient(self.workspace, self._on_update, self._on_permission)
                await self.client.start()
                self.loaded = False
                log.info("Đã khởi chạy agy acp cho chat %s", self.chat_id)
            if not self.loaded:
                if self.session_id:
                    try:
                        res = await self.client.request(
                            "session/load",
                            {"sessionId": self.session_id, "cwd": self.workspace, "mcpServers": []},
                        )
                    except AcpError as e:
                        log.warning("Không load được phiên %s: %s -> tạo mới", self.session_id, e)
                        res = await self._new_session()
                else:
                    res = await self._new_session()
                self.available_models = (res.get("models") or {}).get("availableModels", [])
                self.loaded = True
                await self._apply_settings()
                save_state()
                sync_antigravity_projects(self.session_id, self.workspace)
            return self.client

    async def _new_session(self) -> dict:
        res = await self.client.request(
            "session/new", {"cwd": self.workspace, "mcpServers": []}
        )
        self.session_id = res["sessionId"]
        self.title = ""
        return res

    async def _apply_settings(self) -> None:
        if self.model:
            with contextlib.suppress(AcpError):
                await self.client.request(
                    "session/set_model", {"sessionId": self.session_id, "modelId": self.model}
                )
        if self.mode:
            with contextlib.suppress(AcpError):
                await self.client.request(
                    "session/set_mode", {"sessionId": self.session_id, "modeId": self.mode}
                )

    async def reset(self, new_workspace: str | None = None, session_id: str | None = None) -> None:
        """Chuyển sang phiên mới (hoặc phiên cho trước) ở lần chat tiếp theo."""
        if new_workspace:
            self.workspace = new_workspace
        self.session_id = session_id
        self.title = ""
        self.loaded = False
        save_state()

    async def shutdown(self) -> None:
        self._resolve_all_pending()
        if self.client:
            await self.client.stop()
        self.client = None
        self.loaded = False

    # ----- sự kiện từ agent -----
    def _on_update(self, params: dict) -> None:
        if params.get("sessionId") != self.session_id:
            return
        u = params.get("update", {})
        kind = u.get("sessionUpdate")
        if kind == "session_info_update" and u.get("title"):
            self.title = u["title"]
            sync_antigravity_projects(self.session_id, self.workspace)
        c = self._collect
        if c is None:  # ví dụ: lịch sử được phát lại khi session/load
            return
        c["last_update"] = time.monotonic()
        if kind == "agent_message_chunk":
            content = u.get("content") or {}
            if content.get("type") == "text":
                if c["after_tool"] and c["text"]:
                    c["text"].append("\n\n")
                c["after_tool"] = False
                c["text"].append(content.get("text", ""))
        elif kind == "tool_call":
            icon = KIND_ICONS.get(u.get("kind", "other"), "🔧")
            title = (u.get("title") or u.get("name") or "tool").replace("\n", " ")
            c["steps"].append(f"{icon} {title[:150]}")
            c["after_tool"] = True
            c["dirty"] = True
        elif kind == "plan":
            entries = u.get("entries") or []
            c["plan"] = [
                ("✅" if e.get("status") == "completed" else "▫️") + " " + e.get("content", "")
                for e in entries
            ]
            c["dirty"] = True

    async def _on_permission(self, params: dict) -> dict:
        options: list[dict] = params.get("options") or []
        tool = params.get("toolCall") or {}

        def pick(*kinds: str) -> str | None:
            for k in kinds:
                for o in options:
                    if o.get("kind") == k:
                        return o["optionId"]
            return None

        if self.auto_approve:
            oid = pick("allow_once", "allow_always")
            if oid:
                return {"outcome": {"outcome": "selected", "optionId": oid}}

        key = uuid.uuid4().hex[:12]
        fut = asyncio.get_running_loop().create_future()
        self.pending[key] = (fut, options)

        title = tool.get("title") or tool.get("name") or "tool"
        args = tool.get("rawInput") or tool.get("args") or {}
        detail = args.get("CommandLine") or title
        cwd = args.get("Cwd") or ""
        text = (
            f"🔐 <b>Agent xin phép</b> ({html.escape(str(tool.get('kind') or tool.get('name') or ''))})\n"
            f"<pre>{html.escape(str(detail))[:3000]}</pre>"
        )
        if cwd:
            text += f"\n📁 {html.escape(cwd)}"
        text += f"\n<i>Tự từ chối sau {APPROVAL_TIMEOUT // 60} phút.</i>"

        labels = {
            "allow_once": "✅ Cho phép", "allow_always": "✅ Luôn cho phép",
            "reject_once": "❌ Từ chối", "reject_always": "⛔ Luôn từ chối",
        }
        row = [
            InlineKeyboardButton(labels.get(o.get("kind"), o.get("name", "?")),
                                 callback_data=f"p:{key}:{i}")
            for i, o in enumerate(options)
        ]
        kb = InlineKeyboardMarkup([row, [InlineKeyboardButton("⚡ Cho phép & bật /auto", callback_data=f"p:{key}:auto")]])
        msg = await self.app.bot.send_message(self.chat_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
        try:
            oid = await asyncio.wait_for(fut, APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            oid = pick("reject_once", "reject_always")
            with contextlib.suppress(Exception):
                await msg.edit_reply_markup(None)
                await msg.reply_text("⌛ Hết thời gian → đã từ chối.")
        finally:
            self.pending.pop(key, None)
        if oid is None:
            return {"outcome": {"outcome": "cancelled"}}
        if self._collect is not None and any(
            o.get("optionId") == oid and o.get("kind", "").startswith("reject") for o in options
        ):
            self._collect["rejected"] = True
        return {"outcome": {"outcome": "selected", "optionId": oid}}

    def _resolve_all_pending(self) -> None:
        for fut, _ in self.pending.values():
            if not fut.done():
                fut.set_result(None)
        self.pending.clear()

    # ----- một lượt hội thoại -----
    async def run_turn(self, prompt: list[dict]) -> None:
        bot, chat_id = self.app.bot, self.chat_id
        status = await bot.send_message(chat_id, "⏳ Đang kết nối Antigravity…")
        started = time.monotonic()
        c = {"text": [], "steps": [], "plan": [], "after_tool": False, "dirty": True}

        async def progress_loop() -> None:
            n = 0
            while True:
                await asyncio.sleep(PROGRESS_EDIT_INTERVAL)
                n += 1
                if n % 2 == 0:
                    with contextlib.suppress(Exception):
                        await bot.send_chat_action(chat_id, ChatAction.TYPING)
                if not c["dirty"]:
                    continue
                c["dirty"] = False
                steps = c["steps"]
                lines = [f"⚙️ <b>Đang làm việc</b> (<code>{int(time.monotonic() - started)}s</code>)"]
                if c["plan"]:
                    lines += ["", "📋 <b>Kế hoạch:</b>"] + [html.escape(p) for p in c["plan"][:10]] + [""]
                if len(steps) > 12:
                    lines.append(f"<i>… +{len(steps) - 12} bước trước</i>")
                lines += [html.escape(st) for st in steps[-12:]] or ["💭 <i>Đang suy nghĩ…</i>"]
                with contextlib.suppress(BadRequest):
                    await status.edit_text("\n".join(lines)[:MAX_TG_LEN], parse_mode=ParseMode.HTML)

        progress = asyncio.create_task(progress_loop())
        try:
            client = await self.ensure()
            self._collect = c  # bật thu sau khi load xong (tránh lịch sử phát lại)
            res = await client.request("session/prompt", {"sessionId": self.session_id, "prompt": prompt})
            stop = res.get("stopReason", "end_turn")
            # agy đôi khi gửi nốt vài đoạn text ngay sau khi trả kết quả (vd sau khi bị từ chối)
            # -> chờ tới khi im lặng 2s (tối đa 15s) để gom đủ.
            deadline = time.monotonic() + 15
            c["last_update"] = time.monotonic()
            while time.monotonic() < deadline and time.monotonic() - c["last_update"] < 2:
                await asyncio.sleep(0.3)
            save_state()
            sync_antigravity_projects(self.session_id, self.workspace)
            elapsed = int(time.monotonic() - started)
            icon = {
                "end_turn": "✅ <b>Hoàn tất</b>",
                "cancelled": "🛑 <b>Đã huỷ</b>",
                "refusal": "🚫 <b>Từ chối</b>",
            }.get(stop, f"⚠️ <b>{html.escape(str(stop))}</b>")
            head = f"{icon} sau <code>{elapsed}s</code> · <b>{len(c['steps'])}</b> bước"
            with contextlib.suppress(BadRequest):
                await status.edit_text(head, parse_mode=ParseMode.HTML)
            text = "".join(c["text"])
            if not text and stop == "end_turn":
                text = ("❌ Agent đã dừng vì yêu cầu bị từ chối. Hãy nhắn hướng xử lý khác."
                        if c.get("rejected") else "<i>(Không có phản hồi văn bản)</i>")
            await send_long(self.app, chat_id, text)
            if os.path.exists(__file__) and os.path.getmtime(__file__) != _BOT_START_MTIME:
                log.info("Phát hiện bot.py thay đổi -> tự động nạp lại sau lượt chat")
                os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("Lượt chat lỗi")
            hint = ""
            if "auth" in str(e).lower() or "login" in str(e).lower():
                hint = "\n👉 Chạy <code>./service.sh login</code> hoặc <code>agy</code> trong Terminal để đăng nhập lại Google."
            with contextlib.suppress(Exception):
                await status.edit_text(
                    f"❌ <b>Lỗi:</b> <code>{html.escape(str(e))}</code>{hint}"[:MAX_TG_LEN],
                    parse_mode=ParseMode.HTML,
                )
            if self.client and not self.client.alive:
                self.client = None
        finally:
            progress.cancel()
            self._collect = None

    async def cancel(self) -> None:
        self._resolve_all_pending()
        if self.client and self.client.alive and self.session_id:
            with contextlib.suppress(Exception):
                await self.client.notify("session/cancel", {"sessionId": self.session_id})


SESSIONS: dict[int, Session] = {}
_SAVED = load_state()


def get_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> Session:
    if chat_id not in SESSIONS:
        SESSIONS[chat_id] = Session(context.application, chat_id, _SAVED.get(str(chat_id)))
    return SESSIONS[chat_id]


# ---------------------------------------------------------------------------
# Định dạng Markdown -> Telegram HTML & Chia nhỏ tin nhắn thông minh
# ---------------------------------------------------------------------------
_BOT_START_MTIME = os.path.getmtime(__file__) if os.path.exists(__file__) else 0.0
_RE_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_RE_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_RE_BOLD_ITALIC = re.compile(r"\*\*\*(.+?)\*\*\*")
_RE_BOLD_AST = re.compile(r"\*\*(.+?)\*\*")
_RE_BOLD_UND = re.compile(r"__(.+?)__")
_RE_ITALIC_AST = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
_RE_ITALIC_UND = re.compile(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)")
_RE_STRIKE = re.compile(r"~~(.+?)~~")
_RE_HEADING_MAIN = re.compile(r"^#{1,2}\s+(.+)$")
_RE_HEADING_SUB = re.compile(r"^#{3,6}\s+(.+)$")
_RE_UL_ITEM = re.compile(r"^(\s*)[-*+]\s+(.+)$")
_RE_HR = re.compile(r"^\s*[-*_]{3,}\s*$")
_RE_FENCE = re.compile(r"^\s*(`{3,}|~{3,})([\w+-]*)\s*$")
_RE_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
_ALERT_LABELS = {
    "NOTE": "ℹ️ **Lưu ý:** ",
    "TIP": "💡 **Mẹo:** ",
    "IMPORTANT": "❗ **Quan trọng:** ",
    "WARNING": "⚠️ **Cảnh báo:** ",
    "CAUTION": "🚨 **Thận trọng:** ",
}


def _split_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def _strip_outer_bold(s: str) -> str:
    s = s.strip()
    if (s.startswith("**") and s.endswith("**") and len(s) > 4) or (
        s.startswith("__") and s.endswith("__") and len(s) > 4
    ):
        return s[2:-2].strip()
    return s


def _format_inline(line: str) -> str:
    """Chuyển đổi các cú pháp inline Markdown sang Telegram HTML an toàn."""
    codes: list[str] = []
    links: list[str] = []

    def _save_code(m: re.Match) -> str:
        idx = len(codes)
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00CODE{idx}\x00"

    def _save_link(m: re.Match) -> str:
        label, url = m.group(1).strip(), m.group(2).strip()
        # Escape các ký tự HTML bên ngoài placeholder CODE và khôi phục nội dung bên trong CODE
        clean_label = re.sub(
            r"\x00CODE(\d+)\x00",
            lambda cm: codes[int(cm.group(1))][6:-7],
            html.escape(label),
        )
        idx = len(links)
        if url.startswith(("http://", "https://", "tg://")):
            links.append(f'<a href="{html.escape(url, quote=True)}">{clean_label}</a>')
        else:
            # Telegram không cho phép giao thức file:// hoặc conversation:// trong thẻ <a>
            # -> Hiển thị tên file/symbol dạng monospace <code> gọn đẹp, thân thiện.
            links.append(f"<code>{clean_label}</code>")
        return f"\x00LINK{idx}\x00"

    line = _RE_INLINE_CODE.sub(_save_code, line)
    line = _RE_MD_LINK.sub(_save_link, line)
    line = html.escape(line)

    line = _RE_BOLD_ITALIC.sub(r"<b><i>\1</i></b>", line)
    line = _RE_BOLD_AST.sub(r"<b>\1</b>", line)
    line = _RE_BOLD_UND.sub(r"<b>\1</b>", line)
    line = _RE_ITALIC_AST.sub(r"<i>\1</i>", line)
    line = _RE_ITALIC_UND.sub(r"<i>\1</i>", line)
    line = _RE_STRIKE.sub(r"<s>\1</s>", line)

    for idx, val in enumerate(links):
        line = line.replace(f"\x00LINK{idx}\x00", val)
    for idx, val in enumerate(codes):
        line = line.replace(f"\x00CODE{idx}\x00", val)
    return line


def md_to_tg_html(md_text: str) -> str:
    """Chuyển đổi văn bản Markdown của Agent sang chuẩn HTML của Telegram."""
    lines = md_text.splitlines()
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    fence_lang = ""
    code_buf: list[str] = []
    quote_buf: list[str] = []
    table_buf: list[str] = []

    def _flush_quote() -> None:
        if quote_buf:
            out.append("<blockquote>" + "\n".join(quote_buf) + "</blockquote>")
            quote_buf.clear()

    def _flush_table() -> None:
        if not table_buf:
            return
        parsed_rows = [
            _split_table_row(t_line)
            for t_line in table_buf
            if not _RE_TABLE_SEP.match(t_line)
        ]
        table_buf.clear()
        if not parsed_rows:
            return
        if len(parsed_rows) == 1:
            out.append(" · ".join(_format_inline(c) for c in parsed_rows[0] if c))
            return

        headers = [_strip_outer_bold(h) for h in parsed_rows[0]]
        data_rows = parsed_rows[1:]
        for r in data_rows:
            if not any(r):
                continue
            if len(headers) <= 2 and len(r) >= 2:
                k = _format_inline(_strip_outer_bold(r[0]))
                v = _format_inline(r[1])
                if r[1] and r[1] not in ("—", "-"):
                    out.append(f"• <b>{k}:</b> {v}")
                else:
                    out.append(f"• <b>{k}</b>")
            else:
                first_hdr = headers[0].lower() if headers else ""
                if len(r) >= 2 and (first_hdr in ("#", "stt", "no", "no.") or r[0].isdigit()):
                    title_html = f"{html.escape(r[0])}. {_format_inline(_strip_outer_bold(r[1]))}"
                    start_col = 2
                else:
                    title_html = _format_inline(_strip_outer_bold(r[0]))
                    start_col = 1
                out.append(f"🔹 <b>{title_html}</b>")
                for c_idx in range(start_col, len(r)):
                    val = r[c_idx].strip()
                    if not val or val in ("—", "-"):
                        continue
                    hdr = headers[c_idx] if c_idx < len(headers) else ""
                    if hdr:
                        out.append(f"  • <i>{_format_inline(hdr)}:</i> {_format_inline(val)}")
                    else:
                        out.append(f"  • {_format_inline(val)}")

    for raw_line in lines:
        m_fence = _RE_FENCE.match(raw_line)
        if not in_fence and m_fence:
            _flush_quote()
            _flush_table()
            in_fence = True
            fence_marker = m_fence.group(1)[:3]
            fence_lang = m_fence.group(2).strip()
            code_buf.clear()
            continue

        if in_fence:
            if raw_line.strip().startswith(fence_marker) and raw_line.strip().strip(fence_marker[0]) == "":
                escaped_code = html.escape("\n".join(code_buf))
                if fence_lang:
                    out.append(f'<pre><code class="language-{html.escape(fence_lang)}">{escaped_code}</code></pre>')
                else:
                    out.append(f"<pre>{escaped_code}</pre>")
                in_fence = False
                fence_marker = ""
                fence_lang = ""
                code_buf.clear()
            else:
                code_buf.append(raw_line)
            continue

        # Bảng Markdown (dòng bắt đầu và kết thúc bằng |)
        stripped = raw_line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 2:
            _flush_quote()
            table_buf.append(raw_line)
            continue
        else:
            _flush_table()

        # Blockquote (> ...)
        if stripped.startswith(">"):
            q_content = re.sub(r"^>\s?", "", stripped)
            # Đổi nhãn GitHub Alert như [!NOTE], [!IMPORTANT] sang icon tiếng Việt trực quan
            q_content = re.sub(
                r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*",
                lambda m: _ALERT_LABELS.get(m.group(1), f"**[{m.group(1)}]** "),
                q_content,
            )
            quote_buf.append(_format_inline(q_content))
            continue
        else:
            _flush_quote()

        # Đường kẻ ngang
        if _RE_HR.match(raw_line):
            out.append("────────────────────")
            continue

        # Tiêu đề # / ## và ###..######
        m_h1 = _RE_HEADING_MAIN.match(raw_line)
        if m_h1:
            out.append(f"\n📌 <b>{_format_inline(m_h1.group(1).strip())}</b>")
            continue

        m_h2 = _RE_HEADING_SUB.match(raw_line)
        if m_h2:
            out.append(f"\n🔹 <b>{_format_inline(m_h2.group(1).strip())}</b>")
            continue

        # Danh sách bullet (- / * / +)
        m_ul = _RE_UL_ITEM.match(raw_line)
        if m_ul:
            indent, item_text = m_ul.group(1), m_ul.group(2)
            out.append(f"{indent}• {_format_inline(item_text)}")
            continue

        out.append(_format_inline(raw_line))

    if in_fence and code_buf:
        escaped_code = html.escape("\n".join(code_buf))
        out.append(f"<pre>{escaped_code}</pre>")
    _flush_quote()
    _flush_table()
    return "\n".join(out).strip()


def split_markdown_chunks(text: str, max_len: int = 3300) -> list[str]:
    """Chia văn bản Markdown dài thành các đoạn an toàn, tự động đóng/mở lại code fence."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    cur_lines: list[str] = []
    cur_len = 0
    active_fence: str | None = None
    fence_char = ""

    for line in text.splitlines():
        line_len = len(line) + 1
        if cur_lines and cur_len + line_len > max_len:
            if active_fence:
                cur_lines.append(fence_char)
                chunks.append("\n".join(cur_lines))
                cur_lines = [active_fence]
                cur_len = len(active_fence) + 1
            else:
                chunks.append("\n".join(cur_lines))
                cur_lines = []
                cur_len = 0

        # Nếu 1 dòng đơn lẻ quá dài (vượt max_len)
        while len(line) > max_len:
            part = line[:max_len]
            line = line[max_len:]
            cur_lines.append(part)
            if active_fence:
                cur_lines.append(fence_char)
                chunks.append("\n".join(cur_lines))
                cur_lines = [active_fence]
            else:
                chunks.append("\n".join(cur_lines))
                cur_lines = []
            cur_len = sum(len(x) + 1 for x in cur_lines)

        m_fence = _RE_FENCE.match(line)
        if m_fence:
            if active_fence is None:
                fence_char = m_fence.group(1)[:3]
                active_fence = line.strip()
            elif line.strip().startswith(fence_char) and line.strip().strip(fence_char[0]) == "":
                active_fence = None
                fence_char = ""

        cur_lines.append(line)
        cur_len += line_len

    if cur_lines:
        if active_fence:
            cur_lines.append(fence_char)
        chunks.append("\n".join(cur_lines))
    return chunks


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------
async def send_long(app: Application, chat_id: int, text: str) -> None:
    for md_chunk in split_markdown_chunks(text):
        html_chunk = md_to_tg_html(md_chunk)
        if not html_chunk:
            continue
        try:
            await app.bot.send_message(
                chat_id,
                html_chunk[:MAX_TG_LEN],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest:
            # Fallback an toàn nếu thẻ HTML vượt giới hạn hoặc có ký tự đặc biệt
            await app.bot.send_message(chat_id, md_chunk[:MAX_TG_LEN])


def authorized(update: Update) -> bool:
    user = update.effective_user
    ok = bool(user and user.id in ALLOWED_USER_IDS)
    if not ok:
        log.warning("Từ chối truy cập: user=%s", user.id if user else None)
    return ok


def short_path(p: str) -> str:
    home = str(Path.home())
    return "~" + p[len(home):] if p.startswith(home) else p


async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: list[dict]) -> None:
    s = get_session(context, update.effective_chat.id)
    if s.busy:
        await update.message.reply_text(
            "⏳ <b>Agent đang bận.</b> Gửi <code>/stop</code> để huỷ tác vụ hiện tại.",
            parse_mode=ParseMode.HTML,
        )
        return
    s.task = context.application.create_task(s.run_turn(prompt))


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
HELP = (
    "🤖 <b>Antigravity qua Telegram</b>\n"
    "<i>Gửi tin nhắn văn bản hoặc ảnh kèm chú thích để giao việc cho Agent.</i>\n\n"
    "📌 <b>Quản lý Phiên &amp; Dự án:</b>\n"
    "• <code>/status</code> – Trạng thái hệ thống &amp; phiên hiện tại\n"
    "• <code>/sessions</code> – Mở lại các phiên gần đây (App &amp; Telegram)\n"
    "• <code>/projects</code> – Liệt kê danh sách dự án\n"
    "• <code>/cd &lt;TênDựÁn | ĐườngDẫn&gt;</code> – Chuyển workspace\n"
    "• <code>/new</code> – Bắt đầu hội thoại mới\n"
    "• <code>/stop</code> – Huỷ tác vụ đang chạy\n\n"
    "⚙️ <b>Cấu hình &amp; Quyền hạn:</b>\n"
    "• <code>/model [id]</code> – Xem hoặc đổi model AI\n"
    "• <code>/mode [default|accept-edits|plan]</code> – Chế độ duyệt\n"
    "• <code>/auto [on|off]</code> – Tự động duyệt mọi yêu cầu\n"
    "• <code>/restart</code> – Khởi động lại bot từ xa\n\n"
    "💡 <i>Các lệnh khác như <code>/goal</code>, <code>/plan</code>, <code>/browser</code> được chuyển thẳng cho Agent.</i>"
)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(
            f"⛔ <b>Không có quyền truy cập.</b>\nID Telegram của bạn: <code>{update.effective_user.id}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    s = get_session(context, update.effective_chat.id)
    await update.message.reply_text(
        HELP + f"\n\n📁 Workspace hiện tại: <code>{html.escape(short_path(s.workspace))}</code>",
        parse_mode=ParseMode.HTML,
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    proj = resolve_project_for_workspace(s.workspace, auto_create=False)
    proj_str = f"<b>{html.escape(proj[1])}</b> (<code>{proj[0][:8]}…</code>)" if proj else "<i>CLI Project</i>"
    await update.message.reply_text(
        f"📊 <b>Trạng thái Antigravity Bridge</b>\n\n"
        f"📁 <b>Workspace:</b> <code>{html.escape(short_path(s.workspace))}</code>\n"
        f"🗂 <b>App Project:</b> {proj_str}\n"
        f"💬 <b>Phiên:</b> {html.escape(s.title or '(mới)')}\n"
        f"🆔 <b>Session ID:</b> <code>{s.session_id or '-'}</code>\n"
        f"🧩 <b>Model:</b> <code>{html.escape(s.model or 'mặc định')}</code> · <b>Mode:</b> <code>{html.escape(s.mode or 'default')}</code>\n"
        f"⚡ <b>Auto-approve:</b> {'<b>BẬT ⚠️</b>' if s.auto_approve else '<i>tắt</i>'}\n"
        f"⚙️ <b>Trạng thái:</b> {'⏳ Đang chạy tác vụ' if s.busy else '✅ Rảnh'} · <b>agy:</b> {'🟢 đang chạy' if s.client and s.client.alive else '⚪ chưa khởi động'}",
        parse_mode=ParseMode.HTML,
    )


async def new_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if s.busy:
        await update.message.reply_text(
            "⏳ <b>Đang có tác vụ chạy.</b> Hãy gửi <code>/stop</code> trước.",
            parse_mode=ParseMode.HTML,
        )
        return
    await s.reset()
    await update.message.reply_text(
        "🆕 <b>Đã tạo phiên mới.</b> Tin nhắn tiếp theo sẽ bắt đầu cuộc hội thoại mới.",
        parse_mode=ParseMode.HTML,
    )


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if not s.busy:
        await update.message.reply_text("ℹ️ <i>Hiện không có tác vụ nào đang chạy.</i>", parse_mode=ParseMode.HTML)
        return
    await s.cancel()
    await update.message.reply_text("🛑 <b>Đã gửi yêu cầu dừng tác vụ…</b>", parse_mode=ParseMode.HTML)


async def cd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if not context.args:
        await update.message.reply_text(
            f"📁 <b>Workspace hiện tại:</b> <code>{html.escape(s.workspace)}</code>\n"
            f"👉 Cú pháp: <code>/cd TenDuAn</code> hoặc <code>/cd /đường/dẫn</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    raw = os.path.expanduser(" ".join(context.args))
    target = os.path.abspath(raw if os.path.isabs(raw) else os.path.join(PROJECTS_ROOT, raw))
    if not os.path.isdir(target):
        await update.message.reply_text(
            f"❌ <b>Thư mục không tồn tại:</b> <code>{html.escape(target)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    if s.busy:
        await update.message.reply_text(
            "⏳ <b>Đang có tác vụ chạy.</b> Hãy gửi <code>/stop</code> trước.",
            parse_mode=ParseMode.HTML,
        )
        return
    await s.reset(new_workspace=target)
    await update.message.reply_text(
        f"✅ <b>Đã chuyển Workspace sang:</b> <code>{html.escape(short_path(target))}</code>\n"
        f"<i>(Hội thoại mới sẽ bắt đầu từ tin nhắn tiếp theo)</i>",
        parse_mode=ParseMode.HTML,
    )


async def projects_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    try:
        names = sorted(
            n for n in os.listdir(PROJECTS_ROOT)
            if not n.startswith(".") and os.path.isdir(os.path.join(PROJECTS_ROOT, n))
        )
    except OSError as e:
        await update.message.reply_text(f"❌ <b>Lỗi:</b> <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
        return
    body = "\n".join(f"• <code>{html.escape(n)}</code>" for n in names) or "<i>(trống)</i>"
    await update.message.reply_text(
        f"📂 <b>Danh sách dự án</b> (<code>{html.escape(short_path(PROJECTS_ROOT))}</code>):\n\n"
        f"{body}\n\n"
        f"👉 Dùng lệnh: <code>/cd TenDuAn</code>"[:MAX_TG_LEN],
        parse_mode=ParseMode.HTML,
    )


async def sessions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    try:
        client = await s.ensure()
        res = await client.request("session/list", {})
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"❌ <b>Lỗi:</b> <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
        return
    items = (res.get("sessions") or [])[:10]
    if not items:
        await update.message.reply_text("ℹ️ <i>Chưa có phiên hội thoại nào.</i>", parse_mode=ParseMode.HTML)
        return
    context.chat_data["session_list"] = {it["sessionId"][:8]: it for it in items}
    rows, lines = [], []
    for i, it in enumerate(items, 1):
        mark = " 👈 <i>(đang mở)</i>" if it["sessionId"] == s.session_id else ""
        when = (it.get("updatedAt") or "")[:16].replace("T", " ")
        title_esc = html.escape(it.get("title") or "(không tên)")
        cwd_esc = html.escape(short_path(it.get("cwd", "")))
        lines.append(f"<b>{i}. {title_esc}</b>{mark}\n    📁 <code>{cwd_esc}</code> · 🕒 <i>{html.escape(when)} UTC</i>")
        rows.append([InlineKeyboardButton(f"{i}. {(it.get('title') or '?')[:40]}", callback_data=f"r:{it['sessionId'][:8]}")])
    await update.message.reply_text(
        "🗂 <b>Các phiên làm việc gần đây</b> <i>(bấm nút bên dưới để mở lại)</i>:\n\n"
        + "\n\n".join(lines)
        + "\n\n⚠️ <i>Lưu ý: Tránh mở cùng lúc một phiên đang thao tác trên App máy tính.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def resume_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not authorized(update):
        await q.answer("⛔", show_alert=True)
        return
    s = get_session(context, update.effective_chat.id)
    it = (context.chat_data.get("session_list") or {}).get(q.data[2:])
    if not it:
        await q.answer("Danh sách đã cũ, gọi lại /sessions")
        return
    if s.busy:
        await q.answer("Đang có tác vụ chạy, /stop trước", show_alert=True)
        return
    await s.reset(new_workspace=it.get("cwd") or s.workspace, session_id=it["sessionId"])
    s.title = it.get("title", "")
    save_state()
    await q.answer("Đã chọn phiên")
    await q.edit_message_text(
        f"▶️ <b>Tiếp tục phiên:</b> {html.escape(it.get('title') or it['sessionId'])}\n"
        f"📁 <b>Workspace:</b> <code>{html.escape(short_path(s.workspace))}</code>\n\n"
        f"<i>Hãy gửi tin nhắn để tiếp tục công việc.</i>",
        parse_mode=ParseMode.HTML,
    )


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if context.args:
        s.model = context.args[0]
        save_state()
        if s.loaded and s.client and s.client.alive:
            try:
                await s.client.request("session/set_model", {"sessionId": s.session_id, "modelId": s.model})
            except AcpError as e:
                await update.message.reply_text(f"❌ <b>Lỗi:</b> <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
                return
        await update.message.reply_text(f"🧩 <b>Đã chuyển sang Model:</b> <code>{html.escape(s.model)}</code>", parse_mode=ParseMode.HTML)
        return
    try:
        await s.ensure()
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"❌ <b>Lỗi:</b> <code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)
        return
    lines = [f"• <code>{html.escape(m['modelId'])}</code> – {html.escape(m.get('name', ''))}" for m in s.available_models]
    await update.message.reply_text(
        f"🧩 <b>Model hiện tại:</b> <code>{html.escape(s.model or 'mặc định')}</code>\n\n"
        + "\n".join(lines)
        + "\n\n👉 Dùng lệnh: <code>/model &lt;id&gt;</code>",
        parse_mode=ParseMode.HTML,
    )


async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if not context.args or context.args[0] not in ("default", "accept-edits", "plan"):
        await update.message.reply_text(
            f"🔀 <b>Chế độ hiện tại:</b> <code>{html.escape(s.mode or 'default')}</code>\n\n"
            "• <code>default</code> – Hỏi trước khi sửa file &amp; chạy lệnh\n"
            "• <code>accept-edits</code> – Tự sửa file trong workspace, hỏi khi chạy lệnh\n"
            "• <code>plan</code> – Lập kế hoạch kỹ trước khi thực thi\n\n"
            "👉 Dùng lệnh: <code>/mode accept-edits</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    s.mode = context.args[0]
    save_state()
    if s.loaded and s.client and s.client.alive:
        with contextlib.suppress(AcpError):
            await s.client.request("session/set_mode", {"sessionId": s.session_id, "modeId": s.mode})
    await update.message.reply_text(f"🔀 <b>Đã chuyển Mode:</b> <code>{html.escape(s.mode)}</code>", parse_mode=ParseMode.HTML)


async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    s = get_session(context, update.effective_chat.id)
    if context.args and context.args[0].lower() in ("on", "off"):
        s.auto_approve = context.args[0].lower() == "on"
        save_state()
    await update.message.reply_text(
        "⚡ <b>Auto-approve:</b> "
        + ("<b>BẬT ⚠️</b> <i>(Agent tự động chạy mọi lệnh)</i>" if s.auto_approve else "<b>TẮT</b> <i>(Hỏi trước qua nút bấm)</i>"),
        parse_mode=ParseMode.HTML,
    )


async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    save_state()
    await update.message.reply_text("🔄 <b>Đang khởi động lại bot…</b>", parse_mode=ParseMode.HTML)
    for s in SESSIONS.values():
        with contextlib.suppress(Exception):
            await s.shutdown()
    os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])


async def permission_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not authorized(update):
        await q.answer("⛔ Không có quyền", show_alert=True)
        return
    _, key, choice = (q.data or "").split(":", 2)
    s = get_session(context, update.effective_chat.id)
    entry = s.pending.get(key)
    if entry is None or entry[0].done():
        await q.answer("Yêu cầu đã hết hạn.")
        with contextlib.suppress(Exception):
            await q.edit_message_reply_markup(None)
        return
    fut, options = entry
    if choice == "auto":
        s.auto_approve = True
        save_state()
        opt = next((o for o in options if o.get("kind", "").startswith("allow")), None)
        label = "⚡ Đã cho phép & bật auto"
    else:
        opt = options[int(choice)]
        label = ("✅ " if opt.get("kind", "").startswith("allow") else "❌ ") + opt.get("name", "")
    fut.set_result(opt["optionId"] if opt else None)
    await q.answer(label)
    with contextlib.suppress(Exception):
        await q.edit_message_text((q.message.text_html or "") + f"\n\n<b>{html.escape(label)}</b>", parse_mode=ParseMode.HTML)


async def text_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    await submit(update, context, [{"type": "text", "text": update.message.text}])


async def photo_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    f = await update.message.photo[-1].get_file()
    data = base64.b64encode(bytes(await f.download_as_bytearray())).decode()
    await submit(update, context, [
        {"type": "text", "text": update.message.caption or "Hãy xem ảnh này."},
        {"type": "image", "mimeType": "image/jpeg", "data": data},
    ])


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Lỗi không xử lý được", exc_info=context.error)


BOT_COMMANDS = [
    ("status", "Trạng thái"), ("new", "Hội thoại mới"), ("stop", "Huỷ tác vụ"),
    ("cd", "Đổi workspace"), ("projects", "Liệt kê dự án"), ("sessions", "Phiên gần đây"),
    ("model", "Xem/đổi model"), ("mode", "Chế độ duyệt"), ("auto", "Tự cho phép on/off"),
    ("restart", "Khởi động lại bot"),
    ("goal", "Agent làm tới khi xong mục tiêu"), ("plan", "Lập kế hoạch trước"),
    ("help", "Trợ giúp"),
]


async def post_init(app: Application) -> None:
    sync_antigravity_projects()
    await app.bot.set_my_commands(BOT_COMMANDS)
    for uid in ALLOWED_USER_IDS:
        with contextlib.suppress(Exception):
            await app.bot.send_message(
                uid,
                "🟢 <b>Antigravity Bridge (<code>agy</code>) đã khởi động!</b>\nGõ <code>/help</code> để xem danh sách lệnh.",
                parse_mode=ParseMode.HTML,
            )


async def post_shutdown(app: Application) -> None:
    for s in SESSIONS.values():
        await s.shutdown()


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN trong .env")
    if not ALLOWED_USER_IDS:
        raise SystemExit("Thiếu ALLOWED_USER_IDS trong .env (bắt buộc)")
    if not (os.path.isfile(AGY_PATH) and (os.name == "nt" or os.access(AGY_PATH, os.X_OK))):
        raise SystemExit(f"Không tìm thấy hoặc không thể thực thi agy tại: {AGY_PATH}")
    if not os.path.isdir(DEFAULT_WORKSPACE):
        raise SystemExit(f"DEFAULT_WORKSPACE không tồn tại: {DEFAULT_WORKSPACE}")

    app = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init).post_shutdown(post_shutdown).build()
    )
    app.add_handler(CommandHandler(["start", "help"], start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("new", new_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler(["cd", "pwd"], cd_cmd))
    app.add_handler(CommandHandler("projects", projects_cmd))
    app.add_handler(CommandHandler("sessions", sessions_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(CommandHandler("auto", auto_cmd))
    app.add_handler(CommandHandler("restart", restart_cmd))
    app.add_handler(CallbackQueryHandler(permission_cb, pattern=r"^p:"))
    app.add_handler(CallbackQueryHandler(resume_cb, pattern=r"^r:"))
    app.add_handler(MessageHandler(filters.PHOTO, photo_msg))
    # Văn bản thường + các lệnh lạ (/goal, /plan, /browser...) -> chuyển cho agent
    app.add_handler(MessageHandler(filters.TEXT, text_msg))
    app.add_error_handler(on_error)

    log.info("🚀 Bridge đang chạy. agy=%s · whitelist=%s", AGY_PATH, sorted(ALLOWED_USER_IDS))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
