"""
services/bunny_shield_resolver.py

Zero-bloat Bunny Shield JS Proof-of-Work (PoW) resolver using the host OS browser
in headless mode. Works identically in PyQt6 GUI mode and headless CLI mode
(--name=, --number=).

Supports:
- Chromium family (Edge, Chrome, Chromium, Brave) via local CDP WebSocket.
- Firefox family (firefox, firefox-esr, Flatpak Firefox) via WebDriver BiDi WebSocket
  with a fallback to zero-flag headless execution + direct cookies.sqlite harvesting.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class _LocalWebSocket:
    """Minimal RFC 6455 WebSocket client for localhost (127.0.0.1) browser protocols."""

    def __init__(self, ws_url: str, timeout: float = 5.0) -> None:
        parsed = urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode("ascii"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("WebSocket handshake closed prematurely")
            response += chunk

        header_line = response.split(b"\r\n", 1)[0]
        if b"101" not in header_line:
            raise ConnectionError(f"WebSocket upgrade failed: {header_line.decode('ascii', 'ignore')}")

        # Retain any frame bytes that arrived in the same packet after the HTTP headers
        self._buffer = response.split(b"\r\n\r\n", 1)[1]

    def _recv_exact(self, n: int) -> bytes:
        while len(self._buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("WebSocket connection closed while reading frame")
            self._buffer += chunk
        result, self._buffer = self._buffer[:n], self._buffer[n:]
        return result

    def send_json(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        mask_key = os.urandom(4)
        header = bytearray([0x81])  # FIN + Text frame
        length = len(data)

        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))

        header.extend(mask_key)
        masked_data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + masked_data)

    def recv_json(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        self.sock.settimeout(timeout)
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F

            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]

            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

            if opcode == 0x8:  # Close frame
                return None
            if opcode == 0x9:  # Ping -> reply with masked Pong
                pong = bytearray([0x8A, 0x80, 0, 0, 0, 0])
                self.sock.sendall(pong)
                continue
            if opcode in (0x1, 0x2):  # Text or Binary frame
                return json.loads(payload.decode("utf-8", errors="replace"))

    def call_command(self, cmd_id: int, method: str, params: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        self.send_json({"id": cmd_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(0.2, deadline - time.monotonic())
            msg = self.recv_json(timeout=remaining)
            if msg is None:
                break
            if msg.get("id") == cmd_id:
                return msg
        raise TimeoutError(f"Timed out waiting for response to {method} (id={cmd_id})")

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


class BunnyShieldResolver:
    """Solves Bunny Shield JS PoW challenges on GoComics using the host OS browser."""

    CHALLENGE_MARKERS = (
        "data-pow",
        "shield-challenge.js",
        "challenge-styles.css",
        "challenge.html",
        "establishing a secure connection",
        "<title>bunny shield",
    )

    RATE_LIMIT_MARKERS = (
        "429 too many requests",
        "too many requests",
        "ratelimit.html",
        "rate limit",
        "error 429",
    )

    def __init__(self, cache_dir: Optional[os.PathLike | str] = None, debug: bool = False) -> None:
        self.debug = debug or ("--debug" in sys.argv)
        self._lock = threading.Lock()
        self._circuit_broken_until: float = 0.0  # Cooldown timestamp for circuit breaker

        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self._default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.cache_dir / "gocomics_shield_state.json"

    @staticmethod
    def _default_cache_dir() -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / "ComicStripBrowser" / "cache"
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".cache")
        return base / "comic-strip-browser"

    @staticmethod
    def _mk_profile_dir(prefix: str) -> str:
        """
        Creates an isolated temporary browser profile directory in the OS temp folder
        (/tmp on Linux, %TEMP% on Windows) so Flatpak --filesystem=/tmp sandboxes can
        access it and browser cache churn stays out of ~/.cache/comic-strip-browser.
        """
        tmp_root = Path(tempfile.gettempdir())
        tmp_root.mkdir(parents=True, exist_ok=True)
        return tempfile.mkdtemp(prefix=prefix, dir=str(tmp_root))

    def _log(self, msg: str) -> None:
        logger.debug(msg)
        if self.debug and not logging.getLogger().handlers:
            print(f"[BunnyShieldResolver] {msg}", file=sys.stderr)

    @classmethod
    def is_rate_limited(cls, status_code: int, html: str, url: str) -> bool:
        """
        Returns True if GoComics returned a hard HTTP 429 rate-limit response that
        is NOT a solvable Bunny Shield PoW challenge.
        """
        if "gocomics.com" not in (url or "").lower():
            return False
        html_lower = (html or "").lower()
        if "og:image" in html_lower:
            return False
        if status_code == 429:
            return True
        if "429 too many requests" in html_lower:
            return True
        if "shield-templates-prod.b-cdn.net" in html_lower and "ratelimit.html" in html_lower:
            return True
        return False

    @classmethod
    def is_blocked(
        cls,
        status_code: int,
        html: str,
        url: str,
        headers: Optional[Dict[str, str] | Any] = None,
    ) -> bool:
        """
        Returns True if GoComics returned a hard HTTP 403 Forbidden IP block response that
        is NOT a solvable Bunny Shield PoW challenge.
        """
        if "gocomics.com" not in (url or "").lower():
            return False
        html_lower = (html or "").lower()
        if "og:image" in html_lower:
            return False

        # If it has explicit challenge indicators, it is a challenge, NOT a block!
        if headers:
            try:
                headers_lower = {str(k).lower(): str(v).lower() for k, v in headers.items()}
                if headers_lower.get("cdn-challenge") == "true":
                    return False
            except Exception:
                pass

        if "establishing a secure connection" in html_lower or "shield-challenge.js" in html_lower:
            return False

        # Hard block indicators
        if "shield-templates-prod.b-cdn.net" in html_lower and "block.html" in html_lower:
            return True
        if "<title>403 forbidden</title>" in html_lower:
            return True
        if (
            "blocked from accessing this page" in html_lower
            or "triggered the service and blocked your request" in html_lower
        ):
            return True
        return False

    @classmethod
    def is_bunny_shield_challenge(
        cls,
        status_code: int,
        html: str,
        url: str,
        headers: Optional[Dict[str, str] | Any] = None,
    ) -> bool:
        """
        Returns True if the HTTP response from GoComics is a solvable Bunny Shield
        JS challenge, False if it is normal HTML, a hard 429, or a hard 403 block.
        """
        if "gocomics.com" not in (url or "").lower():
            return False
        if cls.is_rate_limited(status_code, html, url):
            return False
        if cls.is_blocked(status_code, html, url, headers=headers):
            return False
        html_lower = (html or "").lower()
        if "og:image" in html_lower:
            return False

        # 1. Check HTTP response headers for explicit Bunny Shield CDN-Challenge flag
        if headers:
            try:
                headers_lower = {str(k).lower(): str(v).lower() for k, v in headers.items()}
                if headers_lower.get("cdn-challenge") == "true":
                    return True
            except Exception:
                pass

        # 2. Check HTML markers (independent of whether title was parsed separately)
        if "establishing a secure connection" in html_lower:
            return True
        if "shield-templates-prod.b-cdn.net" in html_lower and "challenge.html" in html_lower:
            return True
        if (
            "data-pow" in html_lower
            or "shield-challenge.js" in html_lower
            or "challenge-styles.css" in html_lower
            or "<title>bunny shield" in html_lower
        ):
            return True
        return False

    def load_cached_state(self) -> Optional[Dict[str, Any]]:
        """Loads previously solved cookies, User-Agent, and browser impersonation profile."""
        if not self.state_file.exists():
            return None
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("cookies"):
                return data
        except Exception as exc:
            self._log(f"Failed to load cached shield state: {exc}")
        return None

    def save_cached_state(self, impersonate: str, cookies: Dict[str, str], user_agent: str) -> None:
        """Persists solved cookies and browser family so CLI and GUI runs reuse the session."""
        payload = {
            "impersonate": impersonate,
            "cookies": cookies,
            "user_agent": user_agent,
            "timestamp": int(time.time()),
        }
        try:
            self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            self._log(f"Failed to write cached shield state: {exc}")

    def clear_cached_state(self) -> None:
        """Removes expired or invalidated shield cookies from disk and resets circuit breaker."""
        self._circuit_broken_until = 0.0
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass

    @staticmethod
    def _get_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    @staticmethod
    def _clean_env_for_browser() -> Dict[str, str]:
        """
        Sanitizes the process environment so host system browsers (e.g. system Firefox on Debian)
        do not inherit PyInstaller's or AppImage's bundled shared libraries or GTK/GIO overrides.
        """
        env = os.environ.copy()

        # 1. PyInstaller: restore original LD_LIBRARY_PATH if available, or remove bundled path
        meipass = getattr(sys, "_MEIPASS", None)
        if "LD_LIBRARY_PATH_ORIG" in env:
            orig = env.pop("LD_LIBRARY_PATH_ORIG")
            if orig:
                env["LD_LIBRARY_PATH"] = orig
            else:
                env.pop("LD_LIBRARY_PATH", None)
        elif "LD_LIBRARY_PATH" in env:
            if getattr(sys, "frozen", False) or meipass:
                if meipass:
                    parts = [p for p in env["LD_LIBRARY_PATH"].split(os.pathsep) if p and not p.startswith(meipass)]
                    if parts:
                        env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
                    else:
                        env.pop("LD_LIBRARY_PATH", None)
                else:
                    env.pop("LD_LIBRARY_PATH", None)

        # 2. AppImage environment variables
        for var in ("APPDIR", "APPIMAGE", "OWD"):
            env.pop(var, None)

        # 3. GIO / GTK overrides that might interfere with system browsers
        for var in ("GIO_MODULE_DIR", "GIO_USE_VFS", "GIO_USE_VOLUME_MONITOR", "QT_NO_XDG_DESKTOP_PORTAL"):
            env.pop(var, None)

        return env

    def _popen_kwargs(self, log_handle: Optional[Any] = None) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "env": self._clean_env_for_browser(),
            "stdin": subprocess.DEVNULL,
        }
        if log_handle is not None:
            kwargs["stdout"] = log_handle
            kwargs["stderr"] = subprocess.STDOUT
        else:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL

        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return kwargs

    @classmethod
    def detect_system_browsers(cls) -> List[Tuple[str, List[str]]]:
        """
        Returns a prioritized list of available browsers on the host system as:
        [(family, base_command_list), ...] where family is 'chrome' or 'firefox'.
        """
        found: List[Tuple[str, List[str]]] = []

        if sys.platform == "win32":
            prog_files = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                os.environ.get("LocalAppData", ""),
            ]
            win_candidates = [
                ("chrome", r"Microsoft\Edge\Application\msedge.exe"),
                ("chrome", r"Google\Chrome\Application\chrome.exe"),
                ("chrome", r"BraveSoftware\Brave-Browser\Application\brave.exe"),
                ("firefox", r"Mozilla Firefox\firefox.exe"),
            ]
            for family, rel_path in win_candidates:
                for base in prog_files:
                    if not base:
                        continue
                    full = Path(base) / rel_path
                    if full.is_file():
                        cmd = [str(full)]
                        if (family, cmd) not in found:
                            found.append((family, cmd))
                        break

        # PATH binaries (prioritize Firefox on Linux/Debian, Chromium/Edge on Windows/others)
        if sys.platform.startswith("linux"):
            path_candidates = [
                ("firefox", "firefox-esr"),
                ("firefox", "firefox"),
                ("chrome", "chromium"),
                ("chrome", "chromium-browser"),
                ("chrome", "google-chrome"),
                ("chrome", "google-chrome-stable"),
                ("chrome", "brave-browser"),
                ("chrome", "microsoft-edge"),
                ("chrome", "msedge"),
            ]
        else:
            path_candidates = [
                ("chrome", "chromium"),
                ("chrome", "chromium-browser"),
                ("chrome", "google-chrome"),
                ("chrome", "google-chrome-stable"),
                ("chrome", "brave-browser"),
                ("chrome", "microsoft-edge"),
                ("chrome", "msedge"),
                ("firefox", "firefox"),
                ("firefox", "firefox-esr"),
            ]
        for family, binary in path_candidates:
            resolved = shutil.which(binary)
            if resolved:
                cmd = [resolved]
                if (family, cmd) not in found:
                    found.append((family, cmd))

        # Flatpak fallback on Linux (Firefox first)
        if sys.platform.startswith("linux") and shutil.which("flatpak"):
            tmp_dir = str(Path(tempfile.gettempdir()).resolve())
            flatpak_candidates = [
                ("firefox", "org.mozilla.firefox"),
                ("chrome", "org.chromium.Chromium"),
                ("chrome", "com.google.Chrome"),
                ("chrome", "com.brave.Browser"),
            ]
            for family, app_id in flatpak_candidates:
                try:
                    res = subprocess.run(
                        ["flatpak", "info", app_id],
                        timeout=2.0,
                        **cls._popen_kwargs(),
                    )
                    if res.returncode == 0:
                        found.append(
                            (
                                family,
                                [
                                    "flatpak",
                                    "run",
                                    "--filesystem=/tmp",
                                    f"--filesystem={tmp_dir}",
                                    app_id,
                                ],
                            )
                        )
                except Exception:
                    pass

        return found

    def solve_challenge(
        self,
        url: str,
        timeout_sec: float = 25.0,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Thread-safe method to solve the Bunny Shield challenge on `url` using any available OS browser.
        Returns:
            {
                "ok": bool,
                "rate_limited": bool,
                "impersonate": "chrome" | "firefox",
                "cookies": Dict[str, str],
                "user_agent": str,
                "html": str,
            }
        """
        with self._lock:
            now = time.monotonic()
            if now < self._circuit_broken_until:
                self._log("Circuit breaker is active; skipping headless browser invocation.")
                if progress_callback:
                    progress_callback("Security circuit breaker active. Please wait a moment.")
                return {
                    "ok": False,
                    "rate_limited": False,
                    "impersonate": "chrome",
                    "cookies": {},
                    "user_agent": "",
                    "html": "",
                }

            browsers = self.detect_system_browsers()
            if not browsers:
                self._log("No supported system browser (Chromium/Edge/Chrome/Firefox) found.")
                self._circuit_broken_until = time.monotonic() + 15.0
                if progress_callback:
                    progress_callback("No system browser found to solve challenge.")
                return {
                    "ok": False,
                    "rate_limited": False,
                    "impersonate": "chrome",
                    "cookies": {},
                    "user_agent": "",
                    "html": "",
                }

            for family, base_cmd in browsers:
                browser_name = "Edge" if any("edge" in p.lower() for p in base_cmd) else (
                    "Chrome" if any("chrome" in p.lower() for p in base_cmd) else (
                        "Brave" if any("brave" in p.lower() for p in base_cmd) else (
                            "Firefox" if any("firefox" in p.lower() for p in base_cmd) else family.title()
                        )
                    )
                )
                self._log(f"Attempting Bunny Shield resolution via {family} ({' '.join(base_cmd)})...")
                if progress_callback:
                    progress_callback(f"Bypassing GoComics challenge via {browser_name}...")

                try:
                    if family == "chrome":
                        result = self._solve_with_chromium(base_cmd, url, timeout_sec)
                    else:
                        result = self._solve_with_firefox(base_cmd, url, timeout_sec)

                    if result.get("rate_limited"):
                        self._log("Detected HTTP 429 rate-limit inside browser; tripping circuit breaker.")
                        self._circuit_broken_until = time.monotonic() + 30.0
                        if progress_callback:
                            progress_callback("GoComics rate limit (429) detected. Please wait.")
                        return result

                    if result.get("ok"):
                        self._log(
                            f"Solved challenge via {family}. Cookies captured: {list(result['cookies'].keys())}"
                        )
                        if progress_callback:
                            progress_callback(f"Challenge solved via {browser_name}! Loading strip...")
                        self.save_cached_state(
                            result["impersonate"],
                            result["cookies"],
                            result["user_agent"],
                        )
                        return result
                except Exception as exc:
                    self._log(f"Browser resolver ({' '.join(base_cmd)}) failed: {exc}")

            # All detected browsers failed to solve the challenge; trip circuit breaker with 15s cooldown
            self._log("All browser resolvers failed; tripping circuit breaker for 15s.")
            self._circuit_broken_until = time.monotonic() + 15.0
            if progress_callback:
                progress_callback("Unable to solve security challenge in browser.")
            return {
                "ok": False,
                "rate_limited": False,
                "impersonate": "chrome",
                "cookies": {},
                "user_agent": "",
                "html": "",
            }

    def _solve_with_chromium(self, base_cmd: List[str], url: str, timeout_sec: float) -> Dict[str, Any]:
        port = self._get_free_port()
        profile_dir = self._mk_profile_dir("csb_chr_")
        console_log_path = Path(profile_dir) / "browser_console.log"
        log_handle = open(console_log_path, "w", encoding="utf-8", errors="replace")
        proc: Optional[subprocess.Popen] = None
        ws: Optional[_LocalWebSocket] = None

        default_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            if sys.platform == "win32"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )

        try:
            cmd = base_cmd + [
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled",
                "--mute-audio",
                f"--user-agent={default_ua}",
                f"--user-data-dir={profile_dir}",
                f"--remote-debugging-port={port}",
                "about:blank",
            ]
            self._log(f"Spawning Chromium: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, **self._popen_kwargs(log_handle))
            self._log(f"Chromium PID: {proc.pid}")

            ws_url = None
            startup_deadline = time.monotonic() + 6.0
            self._log(f"Connecting to Chromium remote debugging port {port}...")
            while time.monotonic() < startup_deadline:
                if proc.poll() is not None:
                    self._log(f"Chromium process died during startup with exit code {proc.poll()}")
                    break
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1.0) as resp:
                        targets = json.loads(resp.read().decode("utf-8"))
                        for t in targets:
                            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                                ws_url = t["webSocketDebuggerUrl"]
                                break
                    if ws_url:
                        self._log(f"Chromium WebSocket target: {ws_url}")
                        break
                except Exception:
                    time.sleep(0.15)

            if not ws_url:
                raise RuntimeError(f"Chromium remote debugging port did not expose a page target (exit code: {proc.poll()}).")

            ws = _LocalWebSocket(ws_url, timeout=5.0)
            cmd_id = 1

            ws.call_command(cmd_id, "Page.enable", {})
            cmd_id += 1
            ws.call_command(cmd_id, "Network.enable", {})
            cmd_id += 1
            ws.call_command(cmd_id, "Network.setUserAgentOverride", {"userAgent": default_ua})
            cmd_id += 1

            self._log(f"Chromium navigating to: {url}")
            ws.call_command(cmd_id, "Page.navigate", {"url": url})
            cmd_id += 1

            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                time.sleep(1.0)

                eval_res = ws.call_command(
                    cmd_id,
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement ? document.documentElement.outerHTML : ''",
                        "returnByValue": True,
                    },
                )
                cmd_id += 1
                html = eval_res.get("result", {}).get("result", {}).get("value", "")

                if self.is_rate_limited(200, html, url):
                    self._log("Chromium: detected 429 rate limit page.")
                    return {
                        "ok": False,
                        "rate_limited": True,
                        "impersonate": "chrome",
                        "cookies": {},
                        "user_agent": "",
                        "html": html,
                    }

                cookie_res = ws.call_command(
                    cmd_id,
                    "Network.getCookies",
                    {"urls": ["https://www.gocomics.com", url]},
                )
                cmd_id += 1
                raw_cookies = cookie_res.get("result", {}).get("cookies", [])
                cookies = {c["name"]: c["value"] for c in raw_cookies if "name" in c and "value" in c}

                has_clearance_cookie = any(
                    k == "bunny_shield" or k.startswith("bunny_shield_bd") for k in cookies
                )
                has_comic_html = (
                    "og:image" in html.lower() or "featureassets.gocomics.com" in html.lower()
                )

                if has_comic_html or has_clearance_cookie:
                    self._log(f"Chromium captured clearance! Cookies: {list(cookies.keys())}")
                    ua_res = ws.call_command(
                        cmd_id,
                        "Runtime.evaluate",
                        {"expression": "navigator.userAgent", "returnByValue": True},
                    )
                    raw_ua = ua_res.get("result", {}).get("result", {}).get("value", "")
                    user_agent = (
                        raw_ua.replace("HeadlessChrome/", "Chrome/") if raw_ua else default_ua
                    )

                    return {
                        "ok": True,
                        "rate_limited": False,
                        "impersonate": "chrome",
                        "cookies": cookies,
                        "user_agent": user_agent,
                        "html": html if has_comic_html else "",
                    }

            self._log("Chromium timed out waiting for clearance cookies.")
            return {
                "ok": False,
                "rate_limited": False,
                "impersonate": "chrome",
                "cookies": {},
                "user_agent": "",
                "html": "",
            }

        finally:
            if ws:
                ws.close()
            self._terminate_process(proc)
            if log_handle:
                try:
                    log_handle.close()
                except Exception:
                    pass
            if console_log_path.is_file():
                try:
                    out = console_log_path.read_text(encoding="utf-8", errors="replace").strip()
                    if out and (self.debug or (proc and proc.poll() not in (None, 0))):
                        self._log(f"Chromium process output (exit {proc.poll() if proc else 'N/A'}):\n{out}")
                except Exception:
                    pass
            shutil.rmtree(profile_dir, ignore_errors=True)

    def _solve_with_firefox(self, base_cmd: List[str], url: str, timeout_sec: float) -> Dict[str, Any]:
        try:
            res = self._solve_with_firefox_bidi(base_cmd, url, timeout_sec)
            if res.get("ok") or res.get("rate_limited"):
                return res
        except Exception as exc:
            self._log(f"Firefox BiDi stage did not complete ({exc}); falling back to direct SQLite harvest...")

        return self._solve_with_firefox_sqlite(base_cmd, url, timeout_sec)

    def _solve_with_firefox_bidi(self, base_cmd: List[str], url: str, timeout_sec: float) -> Dict[str, Any]:
        port = self._get_free_port()
        profile_dir = self._mk_profile_dir("csb_ff_bidi_")
        console_log_path = Path(profile_dir) / "browser_console.log"
        log_handle = open(console_log_path, "w", encoding="utf-8", errors="replace")
        proc: Optional[subprocess.Popen] = None
        ws: Optional[_LocalWebSocket] = None

        try:
            self._write_firefox_prefs(Path(profile_dir))
            cmd = base_cmd + [
                "--headless",
                "--no-remote",
                "--profile",
                profile_dir,
                f"--remote-debugging-port={port}",
                "about:blank",
            ]
            self._log(f"Spawning Firefox BiDi: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, **self._popen_kwargs(log_handle))
            self._log(f"Firefox PID: {proc.pid}")

            startup_deadline = time.monotonic() + 7.0
            self._log(f"Connecting to Firefox WebDriver BiDi socket ws://127.0.0.1:{port}/session...")
            while time.monotonic() < startup_deadline:
                if proc.poll() is not None:
                    self._log(f"Firefox process died during startup with exit code {proc.poll()}")
                    break
                try:
                    ws = _LocalWebSocket(f"ws://127.0.0.1:{port}/session", timeout=2.0)
                    self._log("Firefox WebDriver BiDi socket connected successfully.")
                    break
                except Exception:
                    time.sleep(0.2)

            if not ws:
                raise RuntimeError(f"Firefox WebDriver BiDi socket did not come up on port {port} (proc exit code: {proc.poll()}).")

            cmd_id = 1
            ws.call_command(cmd_id, "session.new", {"capabilities": {}})
            cmd_id += 1

            tree_res = ws.call_command(cmd_id, "browsingContext.getTree", {})
            cmd_id += 1
            contexts = tree_res.get("result", {}).get("contexts", [])
            if not contexts:
                raise RuntimeError("No Firefox browsingContext available.")
            ctx_id = contexts[0]["context"]

            ws.call_command(
                cmd_id,
                "script.addPreloadScript",
                {
                    "functionDeclaration": "() => { Object.defineProperty(Navigator.prototype, 'webdriver', {get: () => false}); }"
                },
            )
            cmd_id += 1

            self._log(f"Firefox BiDi navigating to: {url}")
            ws.call_command(
                cmd_id,
                "browsingContext.navigate",
                {"context": ctx_id, "url": url, "wait": "interactive"},
                timeout=10.0,
            )
            cmd_id += 1

            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                time.sleep(1.0)

                eval_res = ws.call_command(
                    cmd_id,
                    "script.evaluate",
                    {
                        "expression": "document.documentElement ? document.documentElement.outerHTML : ''",
                        "target": {"context": ctx_id},
                        "awaitPromise": False,
                    },
                )
                cmd_id += 1
                html = eval_res.get("result", {}).get("result", {}).get("value", "")

                if self.is_rate_limited(200, html, url):
                    self._log("Firefox BiDi: detected 429 rate limit page.")
                    return {
                        "ok": False,
                        "rate_limited": True,
                        "impersonate": "firefox",
                        "cookies": {},
                        "user_agent": "",
                        "html": html,
                    }

                cookie_res = ws.call_command(cmd_id, "storage.getCookies", {})
                cmd_id += 1
                raw_cookies = cookie_res.get("result", {}).get("cookies", [])
                cookies: Dict[str, str] = {}
                for c in raw_cookies:
                    domain = c.get("domain", "")
                    if "gocomics.com" in domain:
                        val_obj = c.get("value", {})
                        val = val_obj.get("value", "") if isinstance(val_obj, dict) else str(val_obj)
                        cookies[c.get("name", "")] = val

                has_clearance_cookie = any(
                    k == "bunny_shield" or k.startswith("bunny_shield_bd") for k in cookies
                )
                has_comic_html = (
                    "og:image" in html.lower() or "featureassets.gocomics.com" in html.lower()
                )

                if has_comic_html or has_clearance_cookie:
                    self._log(f"Firefox BiDi captured clearance! Cookies: {list(cookies.keys())}")
                    ua_res = ws.call_command(
                        cmd_id,
                        "script.evaluate",
                        {
                            "expression": "navigator.userAgent",
                            "target": {"context": ctx_id},
                            "awaitPromise": False,
                        },
                    )
                    user_agent = ua_res.get("result", {}).get("result", {}).get("value", "")
                    return {
                        "ok": True,
                        "rate_limited": False,
                        "impersonate": "firefox",
                        "cookies": cookies,
                        "user_agent": user_agent,
                        "html": html if has_comic_html else "",
                    }

            self._log("Firefox BiDi timed out waiting for clearance cookies.")
            return {
                "ok": False,
                "rate_limited": False,
                "impersonate": "firefox",
                "cookies": {},
                "user_agent": "",
                "html": "",
            }

        finally:
            if ws:
                ws.close()
            self._terminate_process(proc)
            if log_handle:
                try:
                    log_handle.close()
                except Exception:
                    pass
            if console_log_path.is_file():
                try:
                    out = console_log_path.read_text(encoding="utf-8", errors="replace").strip()
                    if out and (self.debug or (proc and proc.poll() not in (None, 0))):
                        self._log(f"Firefox process output (exit {proc.poll() if proc else 'N/A'}):\n{out}")
                except Exception:
                    pass
            shutil.rmtree(profile_dir, ignore_errors=True)

    def _solve_with_firefox_sqlite(self, base_cmd: List[str], url: str, timeout_sec: float) -> Dict[str, Any]:
        profile_dir = self._mk_profile_dir("csb_ff_sql_")
        console_log_path = Path(profile_dir) / "browser_console.log"
        log_handle = open(console_log_path, "w", encoding="utf-8", errors="replace")
        proc: Optional[subprocess.Popen] = None

        try:
            self._write_firefox_prefs(Path(profile_dir))
            cmd = base_cmd + [
                "--headless",
                "--no-remote",
                "--profile",
                profile_dir,
                url,
            ]
            self._log(f"Spawning Firefox SQLite harvest: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, **self._popen_kwargs(log_handle))
            self._log(f"Firefox PID: {proc.pid}")

            db_path = Path(profile_dir) / "cookies.sqlite"
            deadline = time.monotonic() + timeout_sec
            cookies: Dict[str, str] = {}
            default_ff_ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
                if sys.platform == "win32"
                else "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
            )

            # Poll for clearance cookies while Firefox is actively running (typically completes in 2-4s)
            while time.monotonic() < deadline:
                time.sleep(0.5)
                if not db_path.is_file():
                    continue

                try:
                    conn = sqlite3.connect(str(db_path), timeout=0.5)
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT name, value FROM moz_cookies WHERE host LIKE '%gocomics.com%'")
                        for name, value in cur.fetchall():
                            cookies[name] = value
                    finally:
                        conn.close()

                    if any(k.startswith("bunny_shield") for k in cookies):
                        self._log(f"Firefox SQLite harvested clearance cookies: {list(cookies.keys())}")
                        self._terminate_process(proc)
                        proc = None
                        return {
                            "ok": True,
                            "rate_limited": False,
                            "impersonate": "firefox",
                            "cookies": cookies,
                            "user_agent": default_ff_ua,
                            "html": "",
                        }
                except Exception as db_err:
                    self._log(f"SQLite poll notice: {db_err}")

                # If process died prematurely, break to final check
                if proc.poll() is not None:
                    self._log(f"Firefox process exited with code {proc.poll()}")
                    break

            # Terminate process if still running
            self._terminate_process(proc)
            proc = None

            # Final check in case cookies flushed on shutdown
            if db_path.is_file():
                try:
                    conn = sqlite3.connect(str(db_path), timeout=1.0)
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT name, value FROM moz_cookies WHERE host LIKE '%gocomics.com%'")
                        for name, value in cur.fetchall():
                            cookies[name] = value
                    finally:
                        conn.close()

                    if any(k.startswith("bunny_shield") for k in cookies):
                        self._log(f"Firefox SQLite harvested cookies on exit: {list(cookies.keys())}")
                        return {
                            "ok": True,
                            "rate_limited": False,
                            "impersonate": "firefox",
                            "cookies": cookies,
                            "user_agent": default_ff_ua,
                            "html": "",
                        }
                except Exception as final_err:
                    self._log(f"Final SQLite notice: {final_err}")

            self._log("Firefox SQLite harvest completed without finding clearance cookies.")
            return {
                "ok": False,
                "rate_limited": False,
                "impersonate": "firefox",
                "cookies": {},
                "user_agent": "",
                "html": "",
            }

        finally:
            self._terminate_process(proc)
            if log_handle:
                try:
                    log_handle.close()
                except Exception:
                    pass
            if console_log_path.is_file():
                try:
                    out = console_log_path.read_text(encoding="utf-8", errors="replace").strip()
                    if out and (self.debug or (proc and proc.poll() not in (None, 0))):
                        self._log(f"Firefox process output (exit {proc.poll() if proc else 'N/A'}):\n{out}")
                except Exception:
                    pass
            shutil.rmtree(profile_dir, ignore_errors=True)

    @staticmethod
    def _write_firefox_prefs(profile_path: Path) -> None:
        """
        Configures an isolated Firefox profile with automation and telemetry disabled,
        remote debugging/BiDi enabled, and extensions completely disabled across all scopes.
        """
        user_js = (
            'user_pref("dom.webdriver.enabled", false);\n'
            'user_pref("remote.active-protocols", 3);\n'
            'user_pref("remote.allow-origins", "*");\n'
            'user_pref("remote.allow-hosts", "*");\n'
            'user_pref("toolkit.startup.max_resumed_crashes", -1);\n'
            'user_pref("browser.shell.checkDefaultBrowser", false);\n'
            'user_pref("datareporting.policy.dataSubmissionEnabled", false);\n'
            'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);\n'
            'user_pref("media.volume_scale", "0.0");\n'
            'user_pref("extensions.autoDisableScopes", 15);\n'
            'user_pref("extensions.enabledScopes", 0);\n'
            'user_pref("app.normandy.enabled", false);\n'
            'user_pref("app.shield.optoutstudies.enabled", true);\n'
        )
        (profile_path / "user.js").write_text(user_js, encoding="utf-8")

    @staticmethod
    def _terminate_process(proc: Optional[subprocess.Popen]) -> None:
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=3.0)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=2.0)
            except Exception:
                pass

