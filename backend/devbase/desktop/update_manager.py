"""Stage and apply verified GitHub Release updates."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from threading import RLock
from typing import Callable
from uuid import uuid4

from devbase.application.update_checker import (
    GitHubReleaseClient,
    ReleaseVersion,
    UpdateCheckResult,
)

from .update_helper import (
    ReadyUpdate,
    apply_staged_update,
    require_release_files,
    safe_extract_zip,
    write_ready_file,
)


@dataclass(frozen=True, slots=True)
class UpdateProgress:
    status: str = "idle"
    percent: int = 0
    message: str = ""
    error: str | None = None
    rollback: bool = False
    ready_file: str | None = None


class UpdateManager:
    """Own update state without embedding business-specific release names."""

    def __init__(
        self,
        current_version: str,
        *,
        client: GitHubReleaseClient | None = None,
        install_dir: str | Path,
        update_root: str | Path | None = None,
        executable_name: str = "SYNTEC_DevBase.exe",
        updater_name: str | None = "SYNTEC_DevBase-updater.exe",
    ) -> None:
        self.current_version = ReleaseVersion.parse(current_version)
        self.client = client or GitHubReleaseClient()
        self.install_dir = Path(install_dir).resolve()
        self.update_root = Path(update_root or tempfile.gettempdir()).resolve()
        self.executable_name = executable_name
        self.updater_name = updater_name
        self._lock = RLock()
        self._progress = UpdateProgress()
        self._ready: ReadyUpdate | None = None
        self._ready_file: Path | None = None
        self._staging = False
        self._cleanup_stale_runtime_dirs()

    def _cleanup_stale_runtime_dirs(self) -> None:
        if not self.update_root.is_dir():
            return
        for path in self.update_root.glob("updater-runtime-*"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    def progress(self) -> UpdateProgress:
        with self._lock:
            return self._progress

    def prepare_external_apply(self, process_id: int) -> tuple[Path, Path]:
        with self._lock:
            ready = self._ready
            ready_file = self._ready_file
            if ready is None or ready_file is None:
                raise RuntimeError("no staged update is ready")
            if ready.process_id is not None:
                raise RuntimeError("external update is already prepared")
            if self.updater_name is None:
                raise RuntimeError("updater executable is not configured")
            staged_updater = ready.staged_dir / self.updater_name
            if not staged_updater.is_file():
                raise RuntimeError(
                    f"staged updater executable not found: {staged_updater}"
                )
            runtime_dir = self.update_root / f"updater-runtime-{uuid4().hex}"
            try:
                runtime_dir.mkdir(parents=True, exist_ok=False)
                shutil.copy2(staged_updater, runtime_dir / self.updater_name)
                staged_internal = ready.staged_dir / "_internal"
                require_release_files(
                    ready.staged_dir,
                    executable_name=self.executable_name,
                    updater_name=self.updater_name,
                    require_runtime=True,
                )
                shutil.copytree(staged_internal, runtime_dir / "_internal")
                ready = replace(
                    ready,
                    process_id=process_id,
                    runtime_dir=runtime_dir,
                )
                write_ready_file(ready_file, ready)
            except Exception:
                shutil.rmtree(runtime_dir, ignore_errors=True)
                raise
            self._ready = ready
            return runtime_dir / self.updater_name, ready_file

    def discard_staged_update(self) -> None:
        with self._lock:
            ready_file = self._ready_file
            ready = self._ready
            self._ready = None
            self._ready_file = None
        if ready_file is not None:
            shutil.rmtree(ready_file.parent, ignore_errors=True)
        if ready is not None and ready.runtime_dir is not None:
            shutil.rmtree(ready.runtime_dir, ignore_errors=True)

    def check(self) -> UpdateCheckResult:
        self._set_progress("checking", 5, "checking for updates")
        result = self.client.check(self.current_version)
        if result.error:
            self._set_progress("failed", 0, result.error, error=result.error)
        elif result.available:
            self._set_progress("available", 10, f"version {result.latest} is available")
        else:
            self._set_progress("up_to_date", 100, "already up to date")
        return result

    def stage(self, result: UpdateCheckResult | None = None) -> ReadyUpdate:
        with self._lock:
            if self._ready is not None or self._staging:
                raise RuntimeError("an update is already staged or being prepared")
            self._staging = True
        session: Path | None = None
        try:
            if result is None:
                result = self.check()
            if not result.installable or result.release is None:
                raise RuntimeError(result.error or "no installable update is available")

            session = self.update_root / f"devbase-update-{uuid4().hex}"
            extracted = session / "extracted"
            download_dir = session / "download"
            self._set_progress("downloading", 20, "downloading release")
            archive = self.client.download_asset(result.release.asset, download_dir)
            self._set_progress("staging", 65, "verifying release files")
            release_dir = safe_extract_zip(
                archive,
                extracted,
                expected_top_level=self._expected_top_level(result.release.asset.name),
            )
            require_release_files(
                release_dir,
                executable_name=self.executable_name,
                updater_name=self.updater_name,
                require_runtime=self.updater_name is not None,
            )
            backup_dir = self.install_dir.with_name(
                f"{self.install_dir.name}.backup-{uuid4().hex[:8]}"
            )
            ready = ReadyUpdate(
                staged_dir=release_dir,
                install_dir=self.install_dir,
                backup_dir=backup_dir,
                executable_name=self.executable_name,
                updater_name=self.updater_name or "SYNTEC_DevBase-updater.exe",
            )
            ready_file = write_ready_file(session / "ready.json", ready)
            with self._lock:
                self._ready = ready
                self._ready_file = ready_file
                self._staging = False
                self._progress = UpdateProgress(
                    status="ready",
                    percent=80,
                    message="update is ready to apply",
                    ready_file=str(ready_file),
                )
            return ready
        except Exception as error:
            if session is not None:
                shutil.rmtree(session, ignore_errors=True)
            with self._lock:
                self._staging = False
            self._set_progress("failed", 0, str(error), error=str(error))
            raise

    def apply(
        self,
        *,
        process_id: int | None = None,
        wait_for_exit: Callable[[int], bool] | None = None,
        restart: Callable[[Path], None] | None = None,
    ) -> UpdateProgress:
        with self._lock:
            ready = self._ready
        if ready is None:
            raise RuntimeError("no staged update is ready")
        self._set_progress("applying", 85, "applying update")
        try:
            apply_staged_update(
                ready.staged_dir,
                ready.install_dir,
                ready.backup_dir,
                process_id=process_id,
                wait_for_exit=wait_for_exit,
                restart=restart,
            )
        except Exception as error:
            self._set_progress("failed", 0, str(error), error=str(error), rollback=True)
            raise
        with self._lock:
            self._ready = None
            ready_file = self._ready_file
            self._ready_file = None
            self._progress = UpdateProgress(
                status="succeeded",
                percent=100,
                message="update applied successfully",
            )
        if ready_file is not None:
            shutil.rmtree(ready_file.parent, ignore_errors=True)
            return self._progress

    def _expected_top_level(self, asset_name: str) -> str:
        prefix = self.client.config.asset_prefix.rstrip("-_")
        if prefix:
            return prefix
        stem = asset_name.removesuffix(".zip")
        if not stem:
            raise ValueError("release asset has no top-level directory name")
        return stem

    def _set_progress(
        self,
        status: str,
        percent: int,
        message: str,
        *,
        error: str | None = None,
        rollback: bool = False,
    ) -> None:
        with self._lock:
            self._progress = replace(
                self._progress,
                status=status,
                percent=percent,
                message=message,
                error=error,
                rollback=rollback,
            )


__all__ = ["UpdateManager", "UpdateProgress"]
