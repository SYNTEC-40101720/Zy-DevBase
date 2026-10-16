"""一次性冒烟驱动：启动冻结 exe，探活后向 WebView2 窗口发 WM_CLOSE，
验证 exit 0、端口释放、无残留进程家族。

用法: python -I scripts/smoke_desktop_close.py --exe dist\\SYNTEC_DevBase\\SYNTEC_DevBase.exe --port 8791
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import socket
import subprocess
import sys
import time

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010


def find_window_by_pid(pid: int) -> int | None:
    result = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def enum_proc(hwnd, _lparam):
        pid_out = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_out))
        if pid_out.value == pid and user32.IsWindowVisible(hwnd):
            result.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return result[0] if result else None


def find_window_by_title(title: str) -> int | None:
    hwnd = user32.FindWindowW(None, title)
    return hwnd if hwnd else None


def probe_health(port: int, timeout: float = 0.5) -> bool:
    # TCP probe: /health requires a random per-process local token, so use
    # TCP accept as the readiness signal.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def descendants(pid: int) -> set[int]:
    """用 PowerShell CIM 查询进程树（含自身）。"""
    query = (
        f"Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.ProcessId -eq {pid} -or $_.ParentProcessId -eq {pid} }}"
    )
    out = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", query + " | Select-Object -ExpandProperty ProcessId"],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.split()
    return {int(x) for x in out}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()

    env = dict(os.environ, PLATFORM_PORT=str(args.port))
    start = time.monotonic()
    proc = subprocess.Popen([args.exe], env=env)
    print(f"[smoke] launcher pid={proc.pid}")

    # 探活健康端点（等引导进程拉起 uvicorn 子进程）
    ready = False
    while time.monotonic() - start < 30:
        if probe_health(args.port):
            ready = True
            break
        if proc.poll() is not None:
            print(f"[smoke] FAIL: launcher exited early rc={proc.returncode}")
            return 1
        time.sleep(0.3)
    if not ready:
        print("[smoke] FAIL: health not ready in 30s")
        kill_family(proc.pid)
        return 1
    print(f"[smoke] health OK after {time.monotonic() - start:.1f}s")

    # 找 WebView2 主窗口：优先按标题（launcher.py 默认 window_title="DevBase"），
    # 兜底按进程家族枚举可见窗口
    hwnd = None
    for _ in range(40):
        hwnd = find_window_by_title("DevBase") or find_window_by_pid(proc.pid)
        if hwnd:
            break
        time.sleep(0.25)
    if not hwnd:
        search_pids = descendants(proc.pid)
        for pid in sorted(search_pids):
            hwnd = hwnd or find_window_by_pid(pid)
    if not hwnd:
        print(f"[smoke] FAIL: no visible window found (pid={proc.pid})")
        kill_family(proc.pid)
        return 1
    # 校验窗口确属目标进程家族，防止误关无关同名窗口
    hwnd_pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(hwnd_pid))
    family = descendants(proc.pid) | {proc.pid}
    if hwnd_pid.value not in family:
        print(
            f"[smoke] FAIL: window pid {hwnd_pid.value} not in family {sorted(family)}"
        )
        kill_family(proc.pid)
        return 1
    print(f"[smoke] window hwnd=0x{hwnd:X}")

    user32.SendMessageW(hwnd, WM_CLOSE, 0, 0)

    try:
        rc = proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        print("[smoke] FAIL: launcher did not exit within 20s after WM_CLOSE")
        kill_family(proc.pid)
        return 1
    print(f"[smoke] exit code = {rc}")

    # 端口释放 + 无残留
    time.sleep(1.0)
    free = port_free(args.port)
    leftover = descendants(proc.pid)
    print(f"[smoke] port free: {free}; leftover family: {sorted(leftover)}")
    ok = rc == 0 and free and not leftover
    print(f"[smoke] RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def kill_family(pid: int) -> None:
    subprocess.run(
        ["pwsh", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -eq {pid} }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"],
        capture_output=True,
    )


if __name__ == "__main__":
    sys.exit(main())