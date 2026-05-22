from __future__ import annotations

import textwrap

import pytest

from dea.config_loader import ConfigLoadError, load_screen_map, load_screen_maps


def test_load_valid_screen1_yaml() -> None:
    screen_map = load_screen_map("configs/drake/2025/screen1.yaml")
    assert screen_map.screen_code == "SCRN1"
    assert screen_map.expected_markers
    assert len(screen_map.fields) >= 1


def test_load_valid_w2_yaml() -> None:
    screen_map = load_screen_map("configs/drake/2025/w2.yaml")
    assert screen_map.screen_code == "W2IN"
    assert any(field.field_path == "w2.employer.ein" for field in screen_map.fields)


def test_load_screen_maps_directory() -> None:
    maps = load_screen_maps("configs/drake/2025")
    assert "screen1" in maps
    assert "w2" in maps


def test_missing_file_raises() -> None:
    with pytest.raises(ConfigLoadError, match="not found"):
        load_screen_map("configs/drake/2025/not-a-file.yaml")


def test_invalid_support_status_raises(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent(
            """
            screen: screen1
            screen_code: SCRN1
            expected_markers: [Taxpayer]
            fields:
              taxpayer.first_name:
                support_status: MAYBE
                method: tab_order
                position: row:1,col:1
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="support_status"):
        load_screen_map(bad)


def test_missing_markers_raises(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent(
            """
            screen: screen1
            screen_code: SCRN1
            expected_markers: []
            fields:
              taxpayer.first_name:
                support_status: SUPPORTED
                method: tab_order
                position: row:1,col:1
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="expected_markers"):
        load_screen_map(bad)


def test_tab_order_without_position_raises(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent(
            """
            screen: screen1
            screen_code: SCRN1
            expected_markers: [Taxpayer]
            fields:
              taxpayer.first_name:
                support_status: SUPPORTED
                method: tab_order
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="requires position"):
        load_screen_map(bad)


def test_control_locator_without_locator_raises(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent(
            """
            screen: w2
            screen_code: W2IN
            expected_markers: [W-2]
            fields:
              w2.employer.ein:
                support_status: SUPPORTED
                method: control_locator
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="requires locator"):
        load_screen_map(bad)
