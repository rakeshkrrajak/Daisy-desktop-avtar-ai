from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap


CELL_W, CELL_H, COLUMNS = 192, 208, 8
STATES: dict[str, tuple[int, int]] = {
    "idle": (0, 6),
    "running-right": (1, 8),
    "running-left": (2, 8),
    "waving": (3, 4),
    "jumping": (4, 5),
    "failed": (5, 8),
    "waiting": (6, 6),
    "running": (7, 6),
    "review": (8, 6),
}

# States loaded from standalone image files instead of the packed sprite
# sheet grid. Drop numbered PNGs (e.g. 01.png, 02.png, ...) with transparent
# backgrounds into `assets/<folder>/` and they'll be picked up automatically;
# with no files present, callers should fall back to a built-in STATES pose.
CUSTOM_STATE_DIRS: dict[str, str] = {
    "drinking": "drinking",
    "happy": "happy",
    "sleepy": "sleepy",
    "thinking": "thinking",
    "disappointed": "disappointed",
    "surprised": "surprised",
    "judging": "judging",
}
CUSTOM_IMAGE_SUFFIXES = (".png", ".webp")


class SpriteSheet:
    def __init__(self, path: str | Path, scale: float = 1.0) -> None:
        if scale <= 0:
            raise ValueError("scale must be positive")
        self.path = Path(path)
        self.scale = scale
        self._frames: dict[str, list[QPixmap]] = {}
        self._image = QImage(str(self.path))
        if self._image.isNull():
            raise FileNotFoundError(f"could not load sprite sheet: {self.path}")

    def rescale(self, scale: float) -> None:
        if scale <= 0:
            raise ValueError("scale must be positive")
        self.scale = scale
        self._frames.clear()

    @property
    def frame_size(self) -> tuple[int, int]:
        return round(CELL_W * self.scale), round(CELL_H * self.scale)

    def _custom_state_dir(self, state: str) -> Path | None:
        folder_name = CUSTOM_STATE_DIRS.get(state)
        if folder_name is None:
            return None
        return self.path.parent / folder_name

    def has_custom_state(self, state: str) -> bool:
        folder = self._custom_state_dir(state)
        return folder is not None and any(self._custom_image_files(folder))

    @staticmethod
    def _custom_image_files(folder: Path) -> list[Path]:
        if not folder.is_dir():
            return []
        return sorted(
            f for f in folder.iterdir() if f.suffix.lower() in CUSTOM_IMAGE_SUFFIXES
        )

    def _load_custom_frames(self, folder: Path) -> list[QPixmap]:
        width, height = self.frame_size
        result = []
        for file in self._custom_image_files(folder):
            image = QImage(str(file))
            if image.isNull():
                continue
            fitted = image.scaled(
                width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            canvas = QImage(width, height, QImage.Format_ARGB32)
            canvas.fill(Qt.transparent)
            painter = QPainter(canvas)
            x = (width - fitted.width()) // 2
            y = height - fitted.height()  # feet on the same baseline as other poses
            painter.drawImage(x, y, fitted)
            painter.end()
            result.append(QPixmap.fromImage(canvas))
        return result

    def frames(self, state: str) -> list[QPixmap]:
        if state not in self._frames:
            custom_dir = self._custom_state_dir(state)
            if custom_dir is not None and self.has_custom_state(state):
                self._frames[state] = self._load_custom_frames(custom_dir)
                return self._frames[state]
            if state not in STATES:
                valid = ", ".join((*STATES, *CUSTOM_STATE_DIRS))
                raise ValueError(f"unknown state {state!r}; valid names: {valid}")
            row, count = STATES[state]
            width, height = self.frame_size
            result = []
            for column in range(count):
                image = self._image.copy(
                    column * CELL_W,
                    row * CELL_H,
                    CELL_W,
                    CELL_H,
                )
                if self.scale != 1.0:
                    image = image.scaled(
                        width,
                        height,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                result.append(QPixmap.fromImage(image))
            self._frames[state] = result
        return self._frames[state]
