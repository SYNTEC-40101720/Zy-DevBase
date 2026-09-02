from threading import Event

import pytest

from devbase.api.app import create_app
from devbase.application.job_runtime import JobRuntime
from devbase.application.lifecycle import WindowCloseMode
from devbase.desktop import launcher
from devbase.desktop.launcher import (
    DesktopDependencyError,
    run_desktop,
)
from devbase.domain.job import JobStatus


class FakeServer:
    def __init__(self, config) -> None:
        self.config = config
        self.should_exit = False
        self.stopped = Event()

    def run(self) -> None:
        while not self.should_exit:
            self.stopped.wait(0.001)
        self.stopped.set()


class FakeClosedEvent:
    def __init__(self) -> None:
        self.handler = None

    def __iadd__(self, handler):
        self.handler = handler
        return self


class FakeWindow:
    def __init__(self) -> None:
        self.events = type("Events", (), {"closed": FakeClosedEvent()})()


class FakeWebview:
    def __init__(self) -> None:
        self.window = FakeWindow()
        self.window_config = None
        self.start_config = None

    def create_window(self, **config):
        self.window_config = config
        return self.window

    def start(self, **config) -> None:
        self.start_config = config
        self.window.events.closed.handler()


def test_missing_pywebview_has_installation_guidance(monkeypatch) -> None:
    real_import = __import__

    def fail_webview_import(name, *args, **kwargs):
        if name == "webview":
            raise ModuleNotFoundError("No module named 'webview'", name="webview")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fail_webview_import)

    with pytest.raises(DesktopDependencyError, match="pywebview") as error:
        launcher._load_webview()

    assert "[test,desktop]" in str(error.value)


def test_desktop_configures_window_and_stops_cancelled_job(tmp_path) -> None:
    runtime = JobRuntime(total_steps=100, step_delay=0.02)
    webview = FakeWebview()
    created = {}
    servers = []

    def app_factory(*, static_dir, lifecycle_policy):
        app = create_app(
            runtime=runtime,
            static_dir=static_dir,
            lifecycle_policy=lifecycle_policy,
        )
        created["app"] = app
        runtime.start_demo()
        return app

    def server_factory(config):
        server = FakeServer(config)
        servers.append(server)
        return server

    run_desktop(
        tmp_path,
        host="0.0.0.0",
        port=8765,
        window_title="测试工具",
        window_width=1100,
        window_height=700,
        app_factory=app_factory,
        server_factory=server_factory,
        webview_module=webview,
        readiness_waiter=lambda *_args: True,
    )

    assert created["app"].state.window_lifecycle.policy.close_mode is (
        WindowCloseMode.STOP_ON_CLOSE
    )
    assert runtime.current_job().status is JobStatus.CANCELLED
    assert webview.window_config == {
        "title": "测试工具",
        "url": "http://127.0.0.1:8765/",
        "width": 1100,
        "height": 700,
    }
    assert webview.start_config == {"gui": "edgechromium", "debug": False}
    assert servers[0].config.host == "0.0.0.0"
    assert servers[0].config.port == 8765
    assert servers[0].should_exit is True
    assert servers[0].stopped.is_set()