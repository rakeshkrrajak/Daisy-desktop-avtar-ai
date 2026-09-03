from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage

import daisy_pet.sprites as sprites_module
from daisy_pet.sprites import STATES, SpriteSheet


@pytest.fixture
def sheet(qapp):
    return SpriteSheet(
        Path(__file__).parents[1] / "daisy_pet" / "assets" / "spritesheet.webp"
    )


def test_each_state_has_expected_nontransparent_frames(sheet):
    for name, (_, count) in STATES.items():
        frames = sheet.frames(name)
        assert len(frames) == count
        for frame in frames:
            image = frame.toImage().convertToFormat(QImage.Format_ARGB32)
            assert any(
                image.pixelColor(x, y).alpha() > 0
                for y in range(image.height())
                for x in range(image.width())
            )


def test_unknown_state_raises_value_error(sheet):
    with pytest.raises(ValueError, match="valid names"):
        sheet.frames("not-a-state")


def test_new_custom_states_load_from_disk(sheet):
    for state in ("happy", "sleepy", "thinking", "disappointed", "surprised", "judging"):
        assert sheet.has_custom_state(state)
        assert len(sheet.frames(state)) == 1


def test_drinking_custom_state_asset_is_loaded_with_transparency(sheet):
    assert sheet.has_custom_state("drinking")
    frames = sheet.frames("drinking")
    assert len(frames) >= 1
    assert frames[0].size().toTuple() == sheet.frame_size
    image = frames[0].toImage().convertToFormat(QImage.Format_ARGB32)
    assert any(
        image.pixelColor(x, y).alpha() > 0
        for y in range(image.height())
        for x in range(image.width())
    )


def test_has_custom_state_false_when_folder_missing(sheet):
    assert not sheet.has_custom_state("idle")
    assert not sheet.has_custom_state("some-unregistered-state")


def test_generic_custom_state_loads_from_arbitrary_folder(tmp_path, qapp, monkeypatch):
    sheet_path = tmp_path / "sheet.webp"
    sheet_path.write_bytes(
        (
            Path(__file__).parents[1] / "daisy_pet" / "assets" / "spritesheet.webp"
        ).read_bytes()
    )
    custom_dir = tmp_path / "celebrating"
    custom_dir.mkdir()
    swatch = QImage(50, 50, QImage.Format_ARGB32)
    swatch.fill(QColor(255, 0, 0, 255))
    swatch.save(str(custom_dir / "01.png"))

    monkeypatch.setitem(
        sprites_module.CUSTOM_STATE_DIRS, "celebrating", "celebrating"
    )
    sheet = SpriteSheet(sheet_path)
    assert sheet.has_custom_state("celebrating")
    frames = sheet.frames("celebrating")
    assert len(frames) == 1
    assert frames[0].size().toTuple() == sheet.frame_size
    # feet-aligned to the bottom, centered horizontally, padded transparent
    image = frames[0].toImage().convertToFormat(QImage.Format_ARGB32)
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(image.width() // 2, image.height() - 1).alpha() > 0
