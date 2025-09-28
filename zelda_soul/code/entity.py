import pygame
from .particles import AnimationPlayer
from .support import get_distance_direction
from .resources import load_animation_folder, load_sound
from .event_bus import event_bus, GameEvent
from .settings import AUDIO_DIR


class Entity(pygame.sprite.Sprite):
    """Base entity with shared combat & animation behavior."""

    def __init__(self, groups):
        super().__init__(groups)
        self.groups = groups
        self.animation_player = AnimationPlayer()

        # animation state
        self.animation_speed = 0.15
        self.frame_index = 0
        self.animations: dict[str, list[pygame.Surface]] = {}
        self.animate_sequence = "idle"
        self.action: str | None = None # Player uses this for state
        self.sprite_type: str | None = None

        # movement
        self.direction = pygame.math.Vector2()
        self.facing = pygame.math.Vector2()
        self.hitbox: pygame.Rect | None = None
        self.obstacle_sprites: pygame.sprite.Group | None = None

        # combat & status
        self.vulnerable = True
        self.vulnerable_time = 0
        self.attack_type: str | None = None

        # identity
        self.name: str | None = None
        self.full_name: str | None = None
        self.target_location: pygame.math.Vector2 | None = None
        self.target_name: str | None = None

        # events / reasoning
        self.outside_event: str | None = None
        self.reason: str | None = None
        self.internal_event: str | None = None
        self.old_outside_event: str | None = None
        self.observed_event: str | None = None
        self.old_observed_event: str | None = None

        # stats
        self.health: float = 0
        self.max_health: float = 1
        self.energy: float = 0
        self.max_energy: float = 1
        self.lvl = 1
        self.attack_damage = 0
        self.speed = 0
        self.exp = 0

        # observation bookkeeping
        self.first_observation = False

        # sounds (cached)
        self.death_sound = load_sound(AUDIO_DIR / "death.wav")
        self.hit_sound = load_sound(AUDIO_DIR / "hit.wav")
        self.death_sound.set_volume(0.6)
        self.hit_sound.set_volume(0.6)

        # cosmetic placeholders
        self.text_bubble = None
        self.status_bars = None

    def import_graphics(self, main_path: str, name: str, animations: dict):
        load_animation_folder(main_path, name, animations)

    def animate(self):
        if not self.animations or self.animate_sequence not in self.animations: return
        animation = self.animations[self.animate_sequence]
        if not animation: return
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
        self.image = animation[int(self.frame_index)]

    def get_damage(self, attacker: "Entity"):
        if not self.vulnerable: return

        self.outside_event = f"attacked by {attacker.full_name}"
        event_bus.emit(GameEvent.ENTITY_TAKES_DAMAGE, {"target": self, "attacker": attacker})
        self.vulnerable = False
        self.hit_sound.play()
        self.vulnerable_time = pygame.time.get_ticks()

        attack_type = attacker.attack_type
        if attacker.sprite_type == "player":
            if attack_type == "weapon": self.health -= attacker.get_full_weapon_damage()
            elif attack_type == "magic": self.health -= attacker.get_full_magic_damage()
        else:
            self.health -= attacker.attack_damage

        if attack_type:
            self.animation_player.create_particles(attack_type, self.rect.center, [self.groups[0]])

        _, direction = get_distance_direction(self, attacker)
        knockback_distance, knockback_speed = 200, 5
        self.target_location = pygame.math.Vector2(self.hitbox.center) - (
            direction * knockback_distance if direction.magnitude() != 0 else pygame.math.Vector2()
        )
        self.move(self.target_location, knockback_speed)

        if self.health <= 0:
            self.outside_event = f"dead, killed by {attacker.full_name}"
            attacker.outside_event = f"killed {self.full_name}"
            self.animation_player.create_particles(self.name, self.rect.center, [self.groups[0]])
            self.death_sound.play()
            self.add_exp(attacker, self.exp)

    def get_heal(self, healer: "Entity"):
        self.health += healer.attack_damage
        if self.health >= self.max_health:
            self.outside_event = f"fully healed by {healer.full_name}"
            healer.outside_event = f"healed {self.full_name}"
            self.health = self.max_health
        self.animation_player.create_particles("heal", self.hitbox.center, [self.groups[0]])
        self.outside_event = f"healed by {healer.full_name}"

    def add_exp(self, entity: "Entity", amount):
        entity.exp += amount

    def collision(self, direction):
        if not hasattr(self, "obstacle_sprites") or self.obstacle_sprites is None: return
        if direction == "horizontal":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0: self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0: self.hitbox.left = sprite.hitbox.right
        if direction == "vertical":
            for sprite in self.obstacle_sprites:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0: self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0: self.hitbox.top = sprite.hitbox.bottom

    def move(self, target_location, speed):
        if self.direction.magnitude() != 0:
            if self.direction.magnitude() < 2:
                self.direction = self.direction.normalize()
            self.hitbox.x += self.direction.x * speed
            self.collision("horizontal")
            self.hitbox.y += self.direction.y * speed
            self.collision("vertical")
            self.rect.center = self.hitbox.center
