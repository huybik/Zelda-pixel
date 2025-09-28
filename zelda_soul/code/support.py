from csv import reader
from os import walk
import pygame
from math import sin
from typing import List
try:
    from resources import load_images_in_folder  # local import
except Exception:  # pragma: no cover - fallback if relative path issues
    load_images_in_folder = None  # type: ignore


def import_csv_layout(path):
    terrain_map = []
    with open(path) as level_map:
        layout = reader(level_map, delimiter=",")
        for row in layout:
            terrain_map.append(list(row))  # row is x, number of row is y
        return terrain_map


def import_folder(path):
    """Return list[Surface] for every image in folder (cached when possible)."""
    if load_images_in_folder:
        try:
            return load_images_in_folder(path)
        except Exception:
            pass  # fall back to legacy logic
    surface_list: List[pygame.Surface] = []
    for _, _, img_files in walk(path):
        for image in img_files:
            full_path = path + "/" + image
            image_surf = pygame.image.load(full_path).convert_alpha()
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


