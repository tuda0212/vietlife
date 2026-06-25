#!/usr/bin/env python3
"""
git_sync.py — Tự động đồng bộ 2 chiều giữa local và GitHub.

Chiều 1 (Local → GitHub):
  - Dùng watchdog theo dõi thay đổi file
  - Debounce 15 giây → git add -A → commit → push

Chiều 2 (GitHub → Local):
  - Polling mỗi 5 phút → git fetch
  - Nếu remote có commit mới và KHÔNG phải do mình vừa push → pull --rebase

Cách chạy:
  python git_sync.py     (foreground, Ctrl+C để dừng)
  start_sync.bat         (ẩn nền trên Windows)
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ─── CẤU HÌNH ────────────────────────────────────────────────────────────────
REPO_DIR          = os.path.dirname(os.path.abspath(__file__))
STATE_FILE        = os.path.join(REPO_DIR, ".sync_state.json")
LOG_FILE          = os.path.join(REPO_DIR, ".sync.log")
DEBOUNCE_SEC      = 15     # Chờ 15s sau thay đổi cuối trước khi commit+push
POLL_INTERVAL_SEC = 300    # Kiểm tra remote mỗi 5 phút
BRANCH            = "auto-backup"
REMOTE            = "origin"
COMMIT_PREFIX     = "auto-sync"

# Tên thư mục / extension / file không theo dõi
IGNORE_DIRS  = {".git", "__pycache__", ".venv", "node_modules"}
IGNORE_EXT   = {".pyc", ".pyo", ".pyd", ".log"}
IGNORE_FILES = {".sync_state.json", ".sync.log", ".DS_Store", "Thumbs.db"}
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("git_sync")


# ═══════════════════════════════════════════════════════════════════════════════
#  GIT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def git(args: list, cwd: str = REPO_DIR) -> tuple:
    """Chạy lệnh git. Trả về (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        logger.error("Khong tim thay lenh 'git'. Hay cai Git va them vao PATH.")
        sys.exit(1)


def get_local_commit() -> str:
    _, out, _ = git(["rev-parse", "HEAD"])
    return out


def get_remote_commit() -> str:
    """Fetch origin rồi lấy hash commit mới nhất của remote branch."""
    git(["fetch", REMOTE, BRANCH, "--quiet"])
    _, out, _ = git(["rev-parse", f"{REMOTE}/{BRANCH}"])
    return out


def has_local_changes() -> bool:
    _, out, _ = git(["status", "--porcelain"])
    return bool(out.strip())


# ═══════════════════════════════════════════════════════════════════════════════
#  STATE — lưu hash commit lần push gần nhất
# ═══════════════════════════════════════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_pushed_commit": ""}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Khong luu duoc state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  CHIEU 1: LOCAL → GITHUB
# ═══════════════════════════════════════════════════════════════════════════════

def push_local_changes() -> bool:
    """git add -A → commit → push. Lưu commit hash vào state."""
    msg = f"{COMMIT_PREFIX}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # git add -A
    code, _, err = git(["add", "-A"])
    if code != 0:
        logger.error(f"git add loi: {err}")
        return False

    # git commit
    code, out, err = git(["commit", "-m", msg])
    if code != 0:
        combined = (out + err).lower()
        if "nothing to commit" in combined:
            return False
        logger.error(f"git commit loi: {err or out}")
        return False

    logger.info(f"Committed: {msg}")

    # git push
    code, out, err = git(["push", REMOTE, BRANCH])
    if code != 0:
        logger.warning(f"Push that bai ({err}). Thu pull --rebase roi push lai...")
        code2, _, err2 = git(["pull", "--rebase", REMOTE, BRANCH])
        if code2 != 0:
            logger.error(f"pull --rebase loi: {err2}")
            return False
        code3, _, err3 = git(["push", REMOTE, BRANCH])
        if code3 != 0:
            logger.error(f"Push lan 2 loi: {err3}")
            return False

    new_commit = get_local_commit()
    state = load_state()
    state["last_pushed_commit"] = new_commit
    save_state(state)
    logger.info(f"[LOCAL->GITHUB] Pushed thanh cong [{new_commit[:8]}]")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  CHIEU 2: GITHUB → LOCAL (remote poller)
# ═══════════════════════════════════════════════════════════════════════════════

class RemotePoller(threading.Thread):
    """Thread chạy nền, poll remote định kỳ."""

    def __init__(self, pulling_flag: threading.Event):
        super().__init__(daemon=True, name="RemotePoller")
        self._pulling = pulling_flag

    def run(self):
        logger.info(f"RemotePoller bat dau (moi {POLL_INTERVAL_SEC}s)")
        time.sleep(30)  # chờ hệ thống ổn định trước
        while True:
            try:
                self._check_remote()
            except Exception as exc:
                logger.error(f"Poller exception: {exc}")
            time.sleep(POLL_INTERVAL_SEC)

    def _check_remote(self):
        remote_commit = get_remote_commit()
        local_commit  = get_local_commit()
        state         = load_state()
        last_pushed   = state.get("last_pushed_commit", "")

        # Không có gì mới
        if remote_commit == local_commit:
            return

        # Remote có commit mới, nhưng đó chính là commit mình vừa push
        if remote_commit == last_pushed:
            return

        # ── Commit mới từ người khác (hoặc từ máy khác) ──
        logger.info(
            f"[GITHUB->LOCAL] Phat hien commit moi tren remote "
            f"[{remote_commit[:8]}] (local={local_commit[:8]}) → pull ve..."
        )

        # Stash nếu có thay đổi local chưa commit
        stashed = False
        if has_local_changes():
            code, _, err = git(["stash", "push", "-m", "git-sync-auto-stash"])
            if code == 0:
                stashed = True
                logger.info("Stash local changes truoc khi pull.")
            else:
                logger.warning(f"Stash loi (tiep tuc pull): {err}")

        # Set flag để watchdog không trigger push trong lúc pull
        self._pulling.set()
        try:
            code, out, err = git(["pull", "--rebase", REMOTE, BRANCH])
            if code != 0:
                logger.error(f"pull --rebase loi: {err or out}")
            else:
                new_local = get_local_commit()
                logger.info(f"[GITHUB->LOCAL] Pull OK — HEAD gio la [{new_local[:8]}]")
                state["last_pushed_commit"] = new_local
                save_state(state)
        finally:
            self._pulling.clear()

        # Khôi phục stash nếu có
        if stashed:
            code2, _, err2 = git(["stash", "pop"])
            if code2 != 0:
                logger.warning(
                    f"stash pop loi — co the xay ra conflict: {err2}\n"
                    "Chay 'git stash list' de kiem tra thu cong."
                )
            else:
                logger.info("Khoi phuc local changes sau pull thanh cong.")


# ═══════════════════════════════════════════════════════════════════════════════
#  WATCHDOG FILE WATCHER
# ═══════════════════════════════════════════════════════════════════════════════

def _should_ignore(path: str) -> bool:
    p = Path(path)
    if p.name in IGNORE_FILES:
        return True
    if p.suffix in IGNORE_EXT:
        return True
    if IGNORE_DIRS & set(p.parts):
        return True
    return False


def _load_watchdog():
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        return Observer, FileSystemEventHandler
    except ImportError:
        return None, None


def _make_handler(pulling_flag: threading.Event, base_cls):
    class _H(base_cls):
        def __init__(self):
            super().__init__()
            self._timer = None
            self._lock  = threading.Lock()

        def on_any_event(self, event):
            if event.is_directory:
                return
            if _should_ignore(event.src_path):
                return
            if pulling_flag.is_set():
                # Đang pull → bỏ qua (những thay đổi này do pull tạo ra)
                return
            self._restart_timer()

        def _restart_timer(self):
            with self._lock:
                if self._timer and self._timer.is_alive():
                    self._timer.cancel()
                self._timer = threading.Timer(DEBOUNCE_SEC, self._trigger_push)
                self._timer.daemon = True
                self._timer.start()

        def _trigger_push(self):
            if pulling_flag.is_set():
                return
            if has_local_changes():
                logger.info("File local thay doi → push len GitHub...")
                push_local_changes()
    return _H


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    logger.info("=" * 60)
    logger.info("  Git Sync Daemon — Vietlife")
    logger.info(f"  Repo     : {REPO_DIR}")
    logger.info(f"  Remote   : {REMOTE}/{BRANCH}")
    logger.info(f"  Debounce : {DEBOUNCE_SEC}s  |  Poll : {POLL_INTERVAL_SEC}s")
    logger.info("=" * 60)

    # Khởi tạo state
    state = load_state()
    if not state.get("last_pushed_commit"):
        head = get_local_commit()
        if not head:
            logger.error("Khong lay duoc HEAD commit. Kiem tra lai repo git.")
            sys.exit(1)
        state["last_pushed_commit"] = head
        save_state(state)
        logger.info(f"State khoi tao: HEAD = {head[:8]}")

    pulling_flag = threading.Event()

    # Khởi động Remote Poller
    poller = RemotePoller(pulling_flag)
    poller.start()

    # Khởi động Watchdog
    Observer, FileSystemEventHandler = _load_watchdog()
    observer = None
    if Observer and FileSystemEventHandler:
        HandlerCls = _make_handler(pulling_flag, FileSystemEventHandler)
        observer = Observer()
        observer.schedule(HandlerCls(), REPO_DIR, recursive=True)
        observer.start()
        logger.info(f"Watchdog dang theo doi: {REPO_DIR}")
    else:
        logger.warning(
            "Thu vien 'watchdog' chua duoc cai.\n"
            "  Chi chay remote polling (local->GitHub se khong tu dong).\n"
            "  Cai dat bang lenh: pip install watchdog"
        )

    logger.info("Daemon dang chay. Nhan Ctrl+C de dung.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Dang dung daemon...")
    finally:
        if observer:
            observer.stop()
            observer.join()
        logger.info("Da dung.")


if __name__ == "__main__":
    main()
