#!/usr/bin/env python3
import pygame as G

class Enlarger(object):
    def __init__(self, dst, src_wh, flip_after=False):
        """

dst -- destination surface
src_wh -- size of new surface to create, usually half or a third
the size of dst, but None if no scaling is to be applied
flip_after -- if True, flip() chains to pygame.display.flip()

"""
        self.dst = dst
        self.src = G.Surface(src_wh, 0, dst) if src_wh else None
        self.flip_after = flip_after
        self.videotee_fp = None
        self.videotee_skip = 1
        self.videotee_left = 0
        self.num_frames = 0
        self.pixel_format = 'RGB'

    def set_videotee(self, outfp, divisor=1):
        self.videotee_fp = outfp
        self.videotee_skip = divisor

    def get_surface(self):
        return self.src or self.dst

    def flip(self):
        d = self.dst
        if self.src:
            G.transform.scale(self.src, (d.get_width(), d.get_height()), d)
        if self.flip_after:
            G.display.flip()
        if self.videotee_fp:
            if self.videotee_left <= 0:
                self.videotee_left += self.videotee_skip
                bottom_up = False
                s = G.image.tostring(self.get_surface(), self.pixel_format, bottom_up)
                self.videotee_fp.write(s)
            self.videotee_left -= 1
        self.num_frames += 1
