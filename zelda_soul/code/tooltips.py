import pygame
from settings import UI_FONT, UI_FONT_SIZE, TEXT_COLOR, UI_BG_COLOR, UI_BORDER_COLOR


class TextBubble(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.font = pygame.font.Font(UI_FONT, 15)
        self.padding = 10
        self.border_width = 2
        self.offset_y = -10  # Offset above the enemy
        self.bg_color = "#FFFFFF"  # Keep white background for readability
        self.text_color = "#000000"  # Keep black text for readability
        self.border_color = UI_BORDER_COLOR
        self.point_height = 10  # Height of the pointing triangle

        # Initialize with empty surface
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

    def update_text(self, text, target_rect):
        # Render text
        text_surface = self.font.render(text, True, self.text_color)
        text_rect = text_surface.get_rect()

        # Create bubble surface with padding and point
        bubble_width = text_rect.width + (self.padding * 2)
        bubble_height = text_rect.height + (self.padding * 2) + self.point_height
        self.image = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)

        # Draw bubble background
        pygame.draw.rect(
            self.image,
            self.bg_color,
            (0, 0, bubble_width, bubble_height - self.point_height),
            border_radius=10,
        )

        # Draw border
        pygame.draw.rect(
            self.image,
            self.border_color,
            (0, 0, bubble_width, bubble_height - self.point_height),
            width=self.border_width,
            border_radius=10,
        )

        # Draw pointing triangle
        point_points = [
            (bubble_width // 2 - 10, bubble_height - self.point_height),  # Left point
            (bubble_width // 2 + 10, bubble_height - self.point_height),  # Right point
            (bubble_width // 2, bubble_height),  # Bottom point
        ]
        pygame.draw.polygon(self.image, self.bg_color, point_points)
        pygame.draw.polygon(
            self.image, self.border_color, point_points, self.border_width
        )

        # Draw text
        self.image.blit(text_surface, (self.padding, self.padding))

        # Position bubble above target
        self.rect = self.image.get_rect()
        self.rect.midbottom = (target_rect.centerx, target_rect.top + self.offset_y)


class StatusBars(pygame.sprite.Sprite):
    def __init__(self, groups, size=(70, 5), border_color=(60, 60, 60), border_width=2):
        super().__init__(groups)
        self.size = size
        self.border_color = border_color
        self.border_width = border_width

        # Create surface and rect
        total_height = size[1] * 2 + 20  # Height for both bars plus gap
        self.image = pygame.Surface((200, total_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

        # Create rects for health and energy bars relative to surface
        self.health_rect = pygame.Rect(0, 0, size[0], size[1])
        self.energy_rect = pygame.Rect(0, size[1] + 1, size[0], size[1])

        # Colors
        self.health_color = (0, 255, 0)  # green for health
        self.energy_color = (0, 0, 255)  # blue for energy

    def draw_bar(self, rect, current, maximum, color):
        # Draw background
        pygame.draw.rect(self.image, (60, 60, 60), rect)

        # Calculate fill width based on current/max ratio
        if maximum > 0:
            ratio = current / maximum
            fill_width = self.size[0] * ratio
            fill_rect = pygame.Rect(rect.x, rect.y, fill_width, self.size[1])
            pygame.draw.rect(self.image, color, fill_rect)

        # Draw border
        pygame.draw.rect(self.image, self.border_color, rect, self.border_width)

    def update_rect(self, entity):
        # Clear surface
        self.image.fill((0, 0, 0, 0))

        # Update position
        self.rect = self.image.get_rect(
            topleft=(entity.rect.topleft[0], entity.rect.topleft[1] - 20)
        )
        # entity.rect

        # Draw health bar
        self.draw_bar(
            self.health_rect, entity.health, entity.max_health, self.health_color
        )

        # Draw energy bar
        self.draw_bar(
            self.energy_rect, entity.energy, entity.max_energy, self.energy_color
        )

        # Draw exp text
        font = pygame.font.Font(None, 12)  # Default font, size 20
        exp_text = font.render(
            f"EXP:{entity.exp}, LVL:{entity.lvl}, HP:{entity.max_health}, ATT:{entity.attack_damage}, SPD:{entity.speed}",
            True,
            (255, 255, 255),
        )  # White text
        exp_text_rect = exp_text.get_rect(topleft=(0, 10))
        self.image.blit(exp_text, exp_text_rect)

        # Draw to screen
        # surface.blit(self.image, self.rect)
