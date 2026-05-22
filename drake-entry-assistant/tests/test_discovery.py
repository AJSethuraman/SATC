from __future__ import annotations

import json
from pathlib import Path

from dea.adapters.discovery import (
    DrakeDiscoveryResult,
    discover_drake_environment,
    run_and_write_discovery_report,
    write_discovery_report_json,
)
from dea.cli import main


def test_non_windows_path_returns_supported_platform_false() -> None:
    result = discover_drake_environment(platform_name="Linux", window_title_contains="Drake")
    assert result.supported_platform is False
    assert result.drake_window_found is False


def test_report_writer_creates_discovery_report_json(tmp_path) -> None:
    result = DrakeDiscoveryResult(
        timestamp="2026-01-01T00:00:00+00:00",
        platform="Linux",
        supported_platform=False,
        dependency_available=False,
        drake_window_found=False,
        candidate_windows=[],
        selected_window_title=None,
        child_control_count=None,
        child_control_preview=None,
        warnings=["example"],
        errors=[],
    )
    out = tmp_path / "discovery_report.json"
    written = write_discovery_report_json(result, out)

    assert written == out
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["supported_platform"] is False


def test_discovery_result_does_not_contain_screenshots_or_client_data(tmp_path) -> None:
    result, report = run_and_write_discovery_report(
        output_dir=tmp_path,
        window_title_contains="Drake",
        platform_name="Linux",
    )
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert "screenshot" not in payload
    joined = json.dumps(payload)
    assert "taxpayer" not in joined.lower()
    assert "client_id" not in joined.lower()
    assert result.supported_platform is False


def test_cli_discover_drake_exits_gracefully(tmp_path) -> None:
    code = main([
        "discover-drake",
        "--output-dir",
        str(tmp_path),
        "--window-title-contains",
        "Drake",
    ])

    assert code == 0
    assert (tmp_path / "discovery_report.json").exists()


def test_no_pyautogui_import_exists_in_discovery_paths() -> None:
    for relative in ["src/dea/adapters/discovery.py", "src/dea/adapters/real.py", "src/dea/cli.py"]:
        source = Path(relative).read_text(encoding="utf-8").lower()
        assert "pyautogui" not in source


def test_no_clipboard_usage_exists_in_discovery_paths() -> None:
    disallowed_tokens = ["win32clipboard", "pyperclip", ".clipboard", "tkinter.clipboard"]
    for relative in ["src/dea/adapters/discovery.py", "src/dea/adapters/real.py", "src/dea/cli.py"]:
        source = Path(relative).read_text(encoding="utf-8").lower()
        for token in disallowed_tokens:
            assert token not in source


def test_no_keyboard_or_mouse_entry_behavior_exists_in_discovery_paths() -> None:
    disallowed_tokens = ["click_input", "type_keys", "send_keys", "mouse", "keyboard", "set_focus"]
    for relative in ["src/dea/adapters/discovery.py", "src/dea/adapters/real.py"]:
        source = Path(relative).read_text(encoding="utf-8").lower()
        for token in disallowed_tokens:
            assert token not in source
