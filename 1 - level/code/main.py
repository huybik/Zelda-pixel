import pygame, sys
from settings import *
from level import Level
import debug

class Game:
	def __init__(self):
		  
		# general setup
		pygame.init()
		self.screen = pygame.display.set_mode((WIDTH,HEIGTH))
		pygame.display.set_caption('Zelda')
		self.clock = pygame.time.Clock()

		self.level = Level()
	
	def run(self):
		# running = True
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					# running = False
					pygame.quit()
					sys.exit()


			self.screen.fill('black')
			self.level.run()
			pygame.display.update()
			self.clock.tick(FPS)
			# debug.debug()


if __name__ == '__main__':
	game = Game()
	game.run()