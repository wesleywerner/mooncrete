import pygame
from pygame.locals import *
import color

class PuzzleBlockSprite(object):
    """
    Presents a puzzle block image with a location and sliding movement.

    """

    def __init__(self):
        self.image = pygame.Surface(PUZZLE_BLOCK_SIZE)
        self.image.set_colorkey(color.magenta)
        self.image.fill(color.white)
        self.rect = pygame.Rect((0, 0), PUZZLE_BLOCK_SIZE)

    def draw(self, target):
        target.blit(self.image, self.rect)
