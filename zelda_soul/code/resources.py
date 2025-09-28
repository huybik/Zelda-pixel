"""Resource caching utilities for images, animations, and sounds.

This reduces repeated filesystem I/O across the main loop and entity
initialization. Functions are intentionally small & composable so we
can gradually adopt them across modules.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import pygame
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent


def _abs(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    return p


@lru_cache(maxsize=1024)
def load_image(path: str | Path) -> pygame.Surface:
    return pygame.image.load(str(_abs(path))).convert_alpha()


@lru_cache(maxsize=256)
def _folder_listing(path: str | Path) -> tuple[str, ...]:
    folder = _abs(path)
    if not folder.exists():
        return tuple()
    files = [str(f) for f in folder.iterdir() if f.is_file()]
    files.sort()
    return tuple(files)


def load_images_in_folder(path: str | Path) -> list[pygame.Surface]:
    return [load_image(f) for f in _folder_listing(path)]


_ANIMATION_CACHE: Dict[tuple[str, str, str], List[pygame.Surface]] = {}


def load_animation_folder(root: str | Path, name: str, animations: Dict[str, list]):
    root_path = _abs(root)
    for status in animations.keys():
        key = (str(root_path), name, status)
        if key not in _ANIMATION_CACHE:
            frames: List[pygame.Surface] = []
            folder = root_path / name / status
            if folder.exists():
                for f in sorted(folder.iterdir()):
                    if f.is_file():
                        frames.append(load_image(f))
            _ANIMATION_CACHE[key] = frames
        animations[status] = _ANIMATION_CACHE[key]


@lru_cache(maxsize=256)
def load_sound(path: str | Path) -> pygame.mixer.Sound:
    return pygame.mixer.Sound(str(_abs(path)))
