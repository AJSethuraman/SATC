"""Read-only Drake discovery harness.

This module inspects the local environment for visible Drake windows without
clicking, typing, screenshotting, clipboard usage, or data entry.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True)
class DrakeDiscoveryResult:
    timestamp: str
    platform: str
    supported_platform: bool
    dependency_available: bool
    drake_window_found: bool
    candidate_windows: list[str] = field(default_factory=list)
    selected_window_title: str | None = None
    child_control_count: int | None = None
    child_control_preview: list[dict[str, str]] | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _safe_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _is_windows(current_platform: str) -> bool:
    return current_platform.lower().startswith("win")


def _enumerate_visible_window_titles() -> list[tuple[int, str]]:
    """Return visible top-level window handles and non-empty titles on Windows."""
    from ctypes import WINFUNCTYPE, create_unicode_buffer, windll
    from ctypes.wintypes import BOOL, HWND, LPARAM

    user32 = windll.user32
    titles: list[tuple[int, str]] = []

    enum_proc = WINFUNCTYPE(BOOL, HWND, LPARAM)

    @enum_proc
    def _callback(hwnd: HWND, _lparam: LPARAM) -> BOOL:
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buffer = create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title:
                handle_value = hwnd.value if hasattr(hwnd, "value") else int(hwnd)
                titles.append((int(handle_value), title))
        except Exception:
            # Keep enumeration running even if one window fails to inspect.
            return True
        return True

    if not user32.EnumWindows(_callback, 0):
        raise RuntimeError("EnumWindows failed")
    return titles


def _preview_child_controls_with_optional_pywinauto(
    hwnd: int,
    *,
    max_preview: int = 25,
) -> tuple[bool, int | None, list[dict[str, str]] | None, list[str]]:
    """Try read-only child-control inspection using optional pywinauto.

    Returns: dependency_available, child_count, preview, warnings
    """
    warnings: list[str] = []
    try:
        from pywinauto import Desktop  # type: ignore[import-not-found]
    except Exception:
        warnings.append("Optional dependency 'pywinauto' is unavailable; child controls were not inspected.")
        return False, None, None, warnings

    try:
        window = Desktop(backend="uia").window(handle=hwnd)
        descendants = window.descendants()
    except Exception as exc:
        warnings.append(f"pywinauto was available but child control inspection failed: {exc}")
        return True, None, None, warnings

    preview: list[dict[str, str]] = []
    for element in descendants[:max_preview]:
        info = getattr(element, "element_info", None)
        name = ""
        control_type = ""
        automation_id = ""
        class_name = ""
        if info is not None:
            name = str(getattr(info, "name", "") or "")
            control_type = str(getattr(info, "control_type", "") or "")
            automation_id = str(getattr(info, "automation_id", "") or "")
            class_name = str(getattr(info, "class_name", "") or "")

        preview.append(
            {
                "name": name,
                "control_type": control_type,
                "automation_id": automation_id,
                "class_name": class_name,
            }
        )

    return True, len(descendants), preview, warnings


def _pywinauto_available() -> bool:
    try:
        import pywinauto  # type: ignore[import-not-found]

        del pywinauto
        return True
    except Exception:
        return False


def discover_drake_environment(
    *,
    window_title_contains: str = "Drake",
    platform_name: str | None = None,
) -> DrakeDiscoveryResult:
    """Run a read-only discovery pass for Drake window visibility and controls."""
    detected_platform = platform_name or platform.system()

    result = DrakeDiscoveryResult(
        timestamp=_safe_now_iso(),
        platform=detected_platform,
        supported_platform=_is_windows(detected_platform),
        dependency_available=False,
        drake_window_found=False,
        candidate_windows=[],
        selected_window_title=None,
        child_control_count=None,
        child_control_preview=None,
        warnings=[],
        errors=[],
    )

    if not result.supported_platform:
        result.warnings.append("Drake discovery is currently supported only on Windows.")
        return result

    result.dependency_available = _pywinauto_available()
    if not result.dependency_available:
        result.warnings.append("Optional dependency 'pywinauto' is unavailable; child controls cannot be inspected.")

    try:
        visible_windows = _enumerate_visible_window_titles()
    except Exception as exc:
        result.errors.append(f"Unable to enumerate visible windows: {exc}")
        return result

    needle = (window_title_contains or "Drake").strip().lower() or "drake"
    candidates = [(hwnd, title) for hwnd, title in visible_windows if needle in title.lower()]
    result.candidate_windows = [title for _, title in candidates]
    result.drake_window_found = len(candidates) > 0

    if not candidates:
        result.warnings.append(
            f"No visible windows matched title filter '{window_title_contains or 'Drake'}'."
        )
        return result

    selected_hwnd, selected_title = candidates[0]
    result.selected_window_title = selected_title

    if result.dependency_available:
        dep_available, child_count, child_preview, dep_warnings = _preview_child_controls_with_optional_pywinauto(
            selected_hwnd
        )
        result.dependency_available = dep_available
        result.child_control_count = child_count
        result.child_control_preview = child_preview
        result.warnings.extend(dep_warnings)

    return result


def write_discovery_report_json(result: DrakeDiscoveryResult, path: str | Path) -> Path:
    """Write discovery result JSON to disk."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return output


def run_and_write_discovery_report(
    *,
    output_dir: str | Path,
    window_title_contains: str = "Drake",
    platform_name: str | None = None,
) -> tuple[DrakeDiscoveryResult, Path]:
    """Convenience wrapper for CLI usage."""
    result = discover_drake_environment(
        window_title_contains=window_title_contains,
        platform_name=platform_name,
    )
    report_path = write_discovery_report_json(result, Path(output_dir) / "discovery_report.json")
    return result, report_path
