from csv import reader
from os import walk
import pygame
from math import sin
from typing import List


def import_csv_layout(path):
    terrain_map = []
    with open(path) as level_map:
        layout = reader(level_map, delimiter=",")
        for row in layout:
            terrain_map.append(list(row))  # row is x, number of row is y
        return terrain_map


def import_folder(path):
    # add list of surfaces that is all the images in folder
    surface_list = []

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


def import_graphics(main_path, actions):
    animations = {}
    for _, folder_names, _ in walk(main_path):
        for creature_name in folder_names:
            animations[creature_name] = {}
            creature_path = f"{main_path}{creature_name}/"
            # get all frames into animation index
            for action in actions:
                surface_list = []
                path = creature_path + action
                for _, _, img_files in walk(path):
                    for image in img_files:
                        full_path = path + "/" + image
                        image_surf = pygame.image.load(full_path).convert_alpha()
                        surface_list.append(image_surf)

                animations[creature_name][action] = surface_list

    return animations


def wave_value():
    value = sin(pygame.time.get_ticks())
    if value >= 0:
        return 255
    else:
        return 0


def to_grid(pos, tile_size=64):
    return (int(pos.x // tile_size), int(pos.y // tile_size))


def to_world(grid, tile_size=64):
    return pygame.math.Vector2(
        grid[0] * tile_size + tile_size / 2,
        grid[1] * tile_size + tile_size / 2,
    )

def grid_to_discrete(x, y, num_col=64):
    # x and y starting from 0
    return x * num_col + y

def discrete_to_grid(x, num_col=64):
    # x and y starting from 0
    return (x // num_col, x % num_col)
    