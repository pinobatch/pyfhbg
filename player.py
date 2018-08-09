#!/usr/bin/env python3
from itertools import chain

from enemy import BaseWalkingCritter, four_corner_collide
from enemy import VK_A, VK_B, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT
from chipsfx import fxq

class TossedBlock(object):
    def __init__(self, x, y, facing_left):
        self.pos = [x, y]
        self.xvel = -2 if facing_left else 2
        self.yvel = -5

    def move(self):
        self.pos[1] += self.yvel
        self.pos[0] += self.xvel
        self.yvel += 1
        if self.pos[1] > 176 or self.pos[0] < 4 or self.pos[0] > 252:
            self.pos = None

    def draw(self, screen):
        if not self.pos:
            return []
        dstpos = (self.pos[0] - 4, self.pos[1] - 4)
        srcarea = (0, 24, 8, 8)
        return [screen.blit(self.sheet, dstpos, srcarea)]

class Player(BaseWalkingCritter):
    ST_THROWING = 5
    ST_ENTERING_DOOR = 6
    can_hang = True
    x_spd = 2
    hitbox_width = 4
    hang_jump_power = 2
    jump_power = 3

    def __init__(self, *a, **k):
        BaseWalkingCritter.__init__(self, *a, **k)
        self.health = 5

    def new_level(self):
        self.yvel = 0
        self.state = self.ST_WALKING
        self.carrying_block = False

    def move(self, vkeys, new_vkeys):
        if (self.state == self.ST_WALKING and (new_vkeys & VK_UP)
            and self.getblkat(self.pos[0], self.pos[1] - 16) == 9):
            self.state = self.ST_ENTERING_DOOR
            self.walking_frame = 0
            return
        elif (self.state == self.ST_WALKING
              and self.getblkat(self.pos[0], self.pos[1] - 8) == 15):
            self.state = self.ST_ENTERING_DOOR
            self.walking_frame = 0
            return
        elif self.state == self.ST_ENTERING_DOOR:
            ecks = self.pos[0] // 1 % 16 - 8
            if ecks < 0:
                self.pos[0] += 1
            elif ecks > 0:
                self.pos[0] -= 1
            self.walking_frame += 1
            return

        pushed = BaseWalkingCritter.move(self, vkeys, new_vkeys)
        if new_vkeys & VK_B and self.state in (self.ST_WALKING, self.ST_JUMPING):
            if self.carrying_block:
                fxq('throwblock')
                self.state = self.ST_THROWING
                self.walking_frame = 0
                self.carrying_block = False
                blk = TossedBlock(self.pos[0], self.pos[1] - 28, self.facing_left)
                self.game.player_projectiles.append(blk)
            elif self.state == self.ST_WALKING:
                fxq('makeblock')
                self.carrying_block = True
        if self.state == self.ST_THROWING:
            self.walking_frame += 64

        self.pos[0] = min(248, max(8, self.pos[0]))
        if self.pos[1] >= 192:
            self.pos[1] -= 192

        collidables = chain(self.game.enemies, self.game.enemy_projectiles)
        for e in collidables:
            if not e or not e.pos:
                continue
            dx = e.pos[0] - self.pos[0]
            dy = e.pos[1] - e.hitbox_height - self.pos[1] + self.hitbox_height
            if (not e.hitbox_width or not e.hitbox_height
                or abs(dx) >= e.hitbox_width + self.hitbox_width
                or abs(dy) >= e.hitbox_height + self.hitbox_height):
                continue
            destroyed = False
            if e.stun_time > 0:
                destroyed = True
                fxq('destroyed')
            elif self.mercy_time == 0:
                self.health -= 1
                self.mercy_time = 60
                destroyed = True
                fxq('hurt')
            if destroyed:
                self.yvel = min(self.yvel, -2)
                from enemy import Poof
                bullet = Poof(self.game, self.view, e.pos[0], e.pos[1])
                self.game.enemy_projectiles.append(bullet)
                e.pos = None

        if self.mercy_time > 0:
            self.mercy_time -= 1

    def draw(self, screen):
        rects = []
        xflip = 1 if self.facing_left else 0
        if self.state == self.ST_WALKING:
            if self.walking_frame >= 1024:
                self.walking_frame -= 1024
            f = self.walking_frame // 256
            if self.carrying_block:
                f = (f & 1) + 4
        elif self.state == self.ST_THROWING:
            f = self.walking_frame // 256 + 6
            if f >= 8:
                f = 7
                self.state = self.ST_WALKING
        elif self.state == self.ST_JUMPING:
            f = (5 if self.carrying_block
                 else 6 if self.yvel < -1
                 else 7 if self.yvel < 1
                 else 3)
        elif self.state == self.ST_HANGING:
            f = 8
        elif self.state == self.ST_ON_LADDER:
            f = 9
            xflip = (int(self.pos[1] // 8) ^ int(self.pos[0] // 16)) & 1
        elif self.state == self.ST_ENTERING_DOOR:
            f = 10
        dstx = self.pos[0] - 8
        dsty = self.pos[1] - [24, 23, 24, 23, 24, 23, 23, 23, 23, 24, 24][f]
        if (self.mercy_time & 6) != 6:
            src = None
            srcx = [0, 16, 0, 32, 64, 80, 96, 112, 48, 80, 96][f]
            srcy = [0, 0, 0, 0, 0, 0, 0, 0, 0, 24, 24][f]
            if xflip & 1:
                srcx = 128 - 16 - srcx
            src = self.view.spritegfx[xflip]
            rects.append(screen.blit(src, (dstx, dsty), (srcx, srcy, 16, 24)))

        # draw block in hand
        src = self.view.spritegfx[0]
        if self.carrying_block:
            srcarea = (0, 24, 8, 8)
            rects.append(screen.blit(src, (dstx + 4, dsty - 8), srcarea))

        # draw hearts
        srcarea = (8, 24, 8, 8)
        for dsty in range(16, 16 + 10 * self.health, 10):
            rects.append(screen.blit(src, (16, dsty), srcarea))
        return rects
