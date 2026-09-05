"""devbase backend entry point."""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import threading
import webbrowser
from pathlib import Path
from time import monotonic
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIST_DIR = ROOT_DIR / "web" / "dist"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _default_port() -> int:
    try:
        return int(os.getenv("PLATFORM_PORT", "8000"))
    except ValueError:
        return 8000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the devbase local web application."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("PLATFORM_HOST", "127.0.0.1"),
        help="API bind host (default: PLATFORM_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_default_port(),
        help="API bind port (default: PLATFORM_PORT or 8000)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--browser",
        action="store_true",
        help="Use the default browser for web debugging.",
    )
    mode.add_argument(
        "--desktop",
        action="store_true",
        help="Use a local pywebview desktop window (the default).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn reload; only valid with --browser.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser in --browser mode.",
    )
    return parser


def _require_frontend_build() -> Path:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.is_file():
        raise FileNotFoundError(
            "未找到前端构建入口："
            f"{index_path}\n"
            "请先在 web 目录执行 npm ci 和 npm run build。"
        )
    return FRONTEND_DIST_DIR


def _local_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _format_url_host(host: str) -> str:
    local_host = _local_host(host)
    if ":" in local_host and not local_host.startswith("["):
        return f"[{local_host}]"
    return local_host


def _browser_url(host: str, port: int, token: str | None = None) -> str:
    url = f"http://{_format_url_host(host)}:{port}/"
    if token:
        url += "?" + urlencode({"token": token})
    return url


def _wait_for_server_ready(
    host: str,
    port: int,
    stop_event: threading.Event,
    timeout: float = 10.0,
) -> bool:
    health_url = (
        f"http://{_format_url_host(host)}:{port}/api/v1/health"
    )
    deadline = monotonic() + timeout

    while not stop_event.is_set():
        remaining = deadline - monotonic()
        if remaining <= 0:
            return False
        try:
            with urlopen(health_url, timeout=min(0.5, remaining)) as response:
                if response.status == 200:
                    return True
        except (OSError, URLError):
            pass
        stop_event.wait(min(0.1, remaining))
    return False


def _open_browser_when_ready(
    host: str,
    port: int,
    stop_event: threading.Event,
    token: str | None = None,
) -> None:
    if _wait_for_server_ready(host, port, stop_event):
        webbrowser.open(_browser_url(host, port, token))
    elif not stop_event.is_set():
        print("服务未及时就绪，未自动打开浏览器。", file=sys.stderr)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.browser and args.reload:
        parser.error("--reload 仅用于浏览器调试模式，请同时使用 --browser。")

    try:
        static_dir = _require_frontend_build()
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    if not args.browser:
        from importlib import import_module

        desktop_launcher = import_module("devbase.desktop.launcher")

        try:
            desktop_launcher.run_desktop(
                static_dir=static_dir,
                host=args.host,
                port=args.port,
            )
        except desktop_launcher.DesktopLaunchError as error:
            print(error, file=sys.stderr)
            raise SystemExit(1) from error
        return

    import uvicorn

    previous_static_dir = os.environ.get("PLATFORM_STATIC_DIR")
    previous_local_token = os.environ.get("PLATFORM_LOCAL_TOKEN")
    local_token = previous_local_token or secrets.token_urlsafe(32)
    os.environ["PLATFORM_STATIC_DIR"] = str(static_dir)
    os.environ["PLATFORM_LOCAL_TOKEN"] = local_token
    stop_event = threading.Event()
    browser_thread: threading.Thread | None = None
    if not args.no_browser:
        browser_thread = threading.Thread(
            target=_open_browser_when_ready,
            args=(args.host, args.port, stop_event, local_token),
            name="devbase-browser-opener",
        )
        browser_thread.start()

    try:
        uvicorn.run(
            "devbase.api.app:create_app_from_environment",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
            app_dir=str(BACKEND_DIR),
        )
    finally:
        stop_event.set()
        if browser_thread is not None:
            browser_thread.join()
        if previous_static_dir is None:
            os.environ.pop("PLATFORM_STATIC_DIR", None)
        else:
            os.environ["PLATFORM_STATIC_DIR"] = previous_static_dir
        if previous_local_token is None:
            os.environ.pop("PLATFORM_LOCAL_TOKEN", None)
        else:
            os.environ["PLATFORM_LOCAL_TOKEN"] = previous_local_token


if __name__ == "__main__":
    main()
