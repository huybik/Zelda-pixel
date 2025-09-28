from __future__ import annotations

from csv import reader
from pathlib import Path
import pygame
from math import sin

try:
    from .resources import load_images_in_folder  # Local import
except Exception:  # pragma: no cover - fallback if relative path issues
    load_images_in_folder = None  # type: ignore


def import_csv_layout(path: str | Path) -> list[list[str]]:
    layout_path = Path(path)
    terrain_map: list[list[str]] = []
    with layout_path.open() as level_map:
        csv_reader = reader(level_map, delimiter=",")
        for row in csv_reader:
            terrain_map.append(list(row))
    return terrain_map


def import_folder(path: str | Path) -> list[pygame.Surface]:
    """Return list[Surface] for every image in folder (cached when possible)."""
    if load_images_in_folder:
        try:
            return load_images_in_folder(path)
        except Exception:
            pass  # Fall back to legacy logic

    surface_list: list[pygame.Surface] = []
    directory = Path(path)
    for image_path in sorted(directory.iterdir()):
        if image_path.is_file():
            image_surf = pygame.image.load(str(image_path)).convert_alpha()
            surface_list.append(image_surf)
    return surface_list


def get_distance_direction(A: pygame.sprite.Sprite, B: pygame.sprite.Sprite):
    A_vec = pygame.math.Vector2(A.hitbox.center)
    B_vec = pygame.math.Vector2(B.hitbox.center)

    distance = (B_vec - A_vec).magnitude()
    if distance > 0:
        direction = (B_vec - A_vec).normalize()
    else:
        direction = pygame.math.Vector2()

    return distance, direction


def wave_value():
    value = sin(pygame.time.get_ticks())
    if value >= 0:
        return 255
    else:
        return 0


