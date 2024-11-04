import pygame
from settings import UI_FONT, UI_FONT_SIZE, TEXT_COLOR, UI_BG_COLOR, UI_BORDER_COLOR


class TextBubble(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.font = pygame.font.Font(UI_FONT, UI_FONT_SIZE)
        self.padding = 10
        self.border_width = 2
        self.offset_y = -20  # Offset above the enemy
        self.bg_color = "#FFFFFF"  # Keep white background for readability
        self.text_color = "#000000"  # Keep black text for readability
        self.border_color = UI_BORDER_COLOR
        self.point_height = 10  # Height of the pointing triangle

        # Initialize with empty surface
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

    def update_text(self, text, target_rect):
        if not text:
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
            self.rect = self.image.get_rect()
            return

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
