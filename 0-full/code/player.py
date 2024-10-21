import pygame
from debug import debug
from support import import_folder
from settings import weapon_data

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups: pygame.sprite.Group, obstacle_sprites: pygame.sprite.Group):
        super().__init__(groups)
        self.image = pygame.image.load('../graphics/test/player.png')
        self.rect = self.image.get_rect(topleft = pos)
        
        self.hitbox = self.rect.inflate(-20,-26)
        
        # graphics setup
        self.import_player_assets()
        self.animation_speed = 0.15
        self.frame_index = 0
        self.status = 'down'
        
        # movement
        self.direction = pygame.math.Vector2()
        self.speed = 5 # move speed
        self.attacking = False
        self.attack__cooldown = 400
        self.attack_time = pygame.time.get_ticks()
        self.obstacle_sprites = obstacle_sprites
        
        # weapon
        self.weapon_index = 0
        self.weapon = list(weapon_data.keys())[self.weapon_index]
        self.can_switch_weapon = True
        self.weapon_switch_time = None
        self.switch_duration_cooldown = 200

		# stats
        self.stats = {'health': 100,'energy':60,'attack': 10,'magic': 4,'speed': 5}
        self.health = self.stats['health'] * 0.5
        self.energy = self.stats['energy'] * 0.8
        self.exp = 123
        self.speed = self.stats['speed']


    def import_player_assets(self):
        character_path = '../graphics/player/'    
        self.animations = {'up': [],'down': [],'left': [],'right': [],
			'right_idle':[],'left_idle':[],'up_idle':[],'down_idle':[],
			'right_attack':[],'left_attack':[],'up_attack':[],'down_attack':[]}
        
        for animation in self.animations.keys():
            fullpath = character_path + animation
            self.animations[animation] = import_folder(fullpath)
    
    def input(self):
        keys = pygame.key.get_pressed()
        
        # movement
        if keys[pygame.K_RIGHT]:
            self.direction.x = 1
            self.status = 'right'
        elif keys[pygame.K_LEFT]:
            self.direction.x = -1
            self.status = 'left'
        else:
            self.direction.x = 0 
        
        if keys[pygame.K_DOWN]:
            self.direction.y = 1
            self.status = 'down' 
        elif keys[pygame.K_UP]:
            self.direction.y = -1
            self.status = 'up' 
        else:
            self.direction.y = 0
                
        
        # utility
        if keys[pygame.K_LMETA] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            print('magic')
        
        if keys[pygame.K_SPACE] and not self.attacking:
            self.attacking = True
            self.attack_time = pygame.time.get_ticks()
            print('attack')
        
        if keys[pygame.K_q] and self.can_switch_weapon:
            self.can_switch_weapon = False
            self.weapon_switch_time = pygame.time.get_ticks()
            
            if self.weapon_index < len(list(weapon_data.keys())) - 1:
                self.weapon_index += 1
            else:
                self.weapon_index = 0
            
            self.weapon = list(weapon_data.keys())[self.weapon_index]
        
        debug([self.status])

    def get_status(self):
        if self.direction.x == 0 and self.direction.y == 0:
            if '_idle' not in self.status and '_attack' not in self.status:
                self.status += '_idle'
        if self.attacking:
            if '_attack' not in self.status:
                if '_idle' not in self.status: 
                    self.status += '_attack'
                else:
                    self.status = self.status.replace('_idle', '_attack')
        else:
            if '_attack' in self.status:
                self.status = self.status.replace('_attack','')

    def move(self):
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        
        # detect collision before moving
        self.hitbox.x += self.direction.x * self.speed
        self.collision('horizontal')
        self.hitbox.y += self.direction.y * self.speed
        self.collision('vertical')
        
        self.rect.center = self.hitbox.center  
        
        # weapon move
        
                
    def hitbox_collide(self, sprite1: pygame.sprite.Sprite, sprite2: pygame.sprite.Sprite):
        return sprite1.hitbox.colliderect(sprite2.hitbox)
        
    def collision(self, direction):
        
        collided_sprites = pygame.sprite.spritecollide(self, self.obstacle_sprites, dokill=False, collided=self.hitbox_collide)
        for sprite in collided_sprites:
            if direction == 'horizontal':
                if self.direction.x > 0: # moving right
                    self.hitbox.right = sprite.hitbox.left - 1
                if self.direction.x < 0: # moving left
                    self.hitbox.left = sprite.hitbox.right + 1
            if direction == 'vertical':
                if self.direction.y > 0: # moving down
                    self.hitbox.bottom = sprite.hitbox.top - 1
                if self.direction.y < 0: # moving 33334
                    self.hitbox.top = sprite.hitbox.bottom + 1
            # self.direction.y = 0
        
    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.attack_time > self.attack__cooldown:
            self.attacking = False
            
        if not self.can_switch_weapon:
            if current_time - self.weapon_switch_time >= self.switch_duration_cooldown:
                self.can_switch_weapon = True
    
    def animate(self):
        animation = self.animations[self.status] # load animation sequence
        
        self.frame_index += self.animation_speed 
        if self.frame_index >= len(animation):
            self.frame_index = 0
            
        # set the image
        self.image = animation[int(self.frame_index)] # normalize the float
    
    def update(self):
        self.input()
        self.cooldowns()
        self.get_status()
        self.animate()
        self.move()