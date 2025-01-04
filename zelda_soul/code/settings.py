# game setup
WIDTH = 1280
HEIGTH = 720
FPS = 60
TILESIZE = 64

# model
MODEL_PATH = "../model/Llama-3.2-1B-Instruct.Q4_K_M.gguf"
INFERENCE_MODE = "local"
CONTEXT_LENGTH = 8192
CHAT_INTERVAL = 24000
SUMMARY_INTERVAL = 72000
GPU = -1  # 0 for CPU

# event
OBSERVATION_COOLDOWN = 2000
MEMORY_SIZE = 3
SUMMARY_SIZE = 3
OBSERVATION_TO_SUMMARY = 3
# ui
BAR_HEIGHT = 20
HEALTH_BAR_WIDTH = 150
ENERGY_BAR_WIDTH = 140
ITEM_BOX_SIZE = 80
UI_FONT = "../graphics/font/joystix.ttf"
UI_FONT_SIZE = 18

HITBOX_OFFSET = {"player": -26, "object": -40, "grass": -10, "boundary": 0}

# general colors
WATER_COLOR = "#71ddee"
UI_BG_COLOR = "#222222"
UI_BORDER_COLOR = "#111111"
TEXT_COLOR = "#EEEEEE"

# ui colors
HEALTH_COLOR = "red"
ENERGY_COLOR = "blue"
UI_BORDER_COLOR_ACTIVE = "gold"

# upgrade menu
TEXT_COLOR_SELECTED = "#111111"
BAR_COLOR = "#EEEEEE"
BAR_COLOR_SELECTED = "#111111"
UPGRADE_BG_COLOR_SELECTED = "#EEEEEE"

# weapons
weapon_data = {
    "sword": {
        "cooldown": 100,
        "damage": 15,
        "graphic": "../graphics/weapons/sword/full.png",
        # "knockback": 10,
    },
    "lance": {
        "cooldown": 400,
        "damage": 30,
        "graphic": "../graphics/weapons/lance/full.png",
    },
    "axe": {
        "cooldown": 300,
        "damage": 20,
        "graphic": "../graphics/weapons/axe/full.png",
    },
    "rapier": {
        "cooldown": 50,
        "damage": 8,
        "graphic": "../graphics/weapons/rapier/full.png",
    },
    "sai": {
        "cooldown": 80,
        "damage": 10,
        "graphic": "../graphics/weapons/sai/full.png",
    },
}

# magic
magic_data = {
    "flame": {
        "strength": 5,
        "cost": 20,
        "graphic": "../graphics/particles/flame/fire.png",
    },
    "heal": {
        "strength": 20,
        "cost": 10,
        "graphic": "../graphics/particles/heal/heal.png",
    },
}

# enemy
monster_data = {
    "squid": {
        "id": 393,
        "health": 100,
        "exp": 100,
        "damage": 20,
        "attack_type": "slash",
        "attack_sound": "../audio/attack/slash.wav",
        "speed": 2,
        "resistance": 3,
        "act_radius": 120,
        "notice_radius": 600,
        "characteristic": "player friend",
    },
    "raccoon": {
        "id": 392,
        "health": 300,
        "exp": 250,
        "damage": 40,
        "attack_type": "claw",
        "attack_sound": "../audio/attack/claw.wav",
        "speed": 3,
        "resistance": 3,
        "act_radius": 120,
        "notice_radius": 600,
        "characteristic": "aggressive",
    },
    "spirit": {
        "id": 391,
        "health": 100,
        "exp": 110,
        "damage": 8,
        "attack_type": "thunder",
        "attack_sound": "../audio/attack/fireball.wav",
        "speed": 2,
        "resistance": 3,
        "act_radius": 200,
        "notice_radius": 600,
        "characteristic": "help player",
    },
    "bamboo": {
        "id": 390,
        "health": 70,
        "exp": 120,
        "damage": 6,
        "attack_type": "leaf_attack",
        "attack_sound": "../audio/attack/slash.wav",
        "speed": 2,
        "resistance": 3,
        "act_radius": 120,
        "notice_radius": 600,
        "characteristic": "enemy of player",
    },
}
