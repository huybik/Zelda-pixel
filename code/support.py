from csv import reader
from os import walk
import pygame
from math import sin


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
    enemy_vec = pygame.math.Vector2(A.rect.center)
    player_vec = pygame.math.Vector2(B.rect.center)

    distance = (player_vec - enemy_vec).magnitude()
    if distance > 0:
        direction = (player_vec - enemy_vec).normalize()
    else:
        direction = pygame.math.Vector2()

    return distance, direction


def wave_value():
    value = sin(pygame.time.get_ticks())
    if value >= 0:
        return 255
    else:
        return 0
