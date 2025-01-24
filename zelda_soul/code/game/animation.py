import pygame
from utils.support import import_folder, import_graphics
from entities.actions import Action
import random
from typing import List, Dict


class AnimationPlayer:
    def __init__(self):
        self.attacks = {
            # magic
            "flame": import_folder("graphics/particles/flame/frames"),
            "aura": import_folder("graphics/particles/aura"),
            "heal": import_folder("graphics/particles/heal/frames"),
            # attacks
            "claw": import_folder("graphics/particles/claw"),
            "slash": import_folder("graphics/particles/slash"),
            "sparkle": import_folder("graphics/particles/sparkle"),
            "leaf_attack": import_folder("graphics/particles/leaf_attack"),
            "thunder": import_folder("graphics/particles/thunder"),
            "weapon": import_folder("graphics/particles/sparkle"),
        }
        self.deaths = {
            # monster deaths
            "squid": import_folder("graphics/particles/smoke_orange"),
            "raccoon": import_folder("graphics/particles/raccoon"),
            "spirit": import_folder("graphics/particles/nova"),
            "bamboo": import_folder("graphics/particles/bamboo"),
            "player": import_folder("graphics/particles/smoke2"),
        }
        self.leafs = {
            # leafs
            "leaf": (
                import_folder("graphics/particles/leaf1"),
                import_folder("graphics/particles/leaf2"),
                import_folder("graphics/particles/leaf3"),
                import_folder("graphics/particles/leaf4"),
                import_folder("graphics/particles/leaf5"),
                import_folder("graphics/particles/leaf6"),
                self.reflect_images(import_folder("graphics/particles/leaf1")),
                self.reflect_images(import_folder("graphics/particles/leaf2")),
                self.reflect_images(import_folder("graphics/particles/leaf3")),
                self.reflect_images(import_folder("graphics/particles/leaf4")),
                self.reflect_images(import_folder("graphics/particles/leaf5")),
                self.reflect_images(import_folder("graphics/particles/leaf6")),
            ),
        }
        actions = Action().get_actions().keys()
        self.animations = import_graphics("graphics/creatures/", actions)
        pass

    def reflect_images(self, frames):
        new_frames = []

        for frame in frames:
            flipped_frame = pygame.transform.flip(frame, True, False)
            new_frames.append(flipped_frame)

            return new_frames

    def create_grass_particles(self, pos, groups):
        animation_frames = random.choice(self.leafs["leaf"])
        Particle(pos, animation_frames, groups)

    def create_attack_particles(self, attack_type, pos, groups):
        animation_frames = self.attacks[attack_type]
        Particle(pos, animation_frames, groups)

    def create_death_particles(self, creature_type, pos, groups):
        animation_frames = self.deaths[creature_type]
        Particle(pos, animation_frames, groups)

    def create_animations(self, creature_type):
        return Animate(self.animations, creature_type)


class Particle(pygame.sprite.Sprite):
    def __init__(
        self,
        pos,
        animation_frames: list[pygame.surface.Surface],
        groups,
    ):
        super().__init__(groups)
        self.frame_index = 0
        self.animation_speed = 0.15
        self.frames = animation_frames
        self.type = type
        

        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=pos)

    def animate(self):
        self.frame_index += self.animation_speed

        if self.frame_index >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[int(self.frame_index)]

    def update(self):
        self.animate()


class Animate:
    def __init__(self, animations: dict, creature_type):
        # super().__init__(groups)
        self.frame_index = 0
        self.animation_speed = 0.15
        self.frames: Dict[str, List[pygame.Surface]] = animations[creature_type]

        # self.image = self.frames["chill"][self.frame_index]
        # self.rect = self.image.get_rect(center=pos)
        # self.hitbox = self.rect

    def animate(self, action):
        frames: List[pygame.Surface] = self.frames[action]
        self.frame_index += self.animation_speed

        if self.frame_index >= len(frames):
            self.frame_index = 0
        self.image = frames[int(self.frame_index)]

        return self.image
