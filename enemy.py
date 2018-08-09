#!/usr/bin/env python3
from chipsfx import fxq
from events import VK_A, VK_B, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT
from loadlevel import MT_ELEVATOR_DOOR

enemies_gfxcoords = {
    'plodder': (24, 64),
    'sneaker': (56, 64),
    'spinner': (104, 64),
    'burger': (8, 80),
    'pecker': (120, 80),
    'toaster': (24, 80),
}

enemies_minitiles = {
    'sneaker': 0x12, 'spinner': 0x13, 'plodder': 0x14,
    'burger': 0x15, 'toaster': 0x16, 'pecker': 0x17,
    '': 0x08
}

def four_corner_collide(pf, x, y, rx, ry,
                        with_downsolid=True, diag_corner_push=False):
    tlx = int((x - 8) // 16)
    tly = int((y - 8) // 16)
    dx = x - (tlx + 1) * 16
    dy = y - (tly + 1) * 16
    if dy >= 0:  # already below centerline
        with_downsolid = False

    # 1 2
    # 4 8
    coords = enumerate((tlx + x1, tly + y1)
                       for y1 in (0, 1) for x1 in (0, 1))
    blks = [(i, pf.getcell(x1, min(y1, 11)) if 0 <= x1 and 0 <= y1 else 0)
            for (i, (x1, y1)) in coords]
    blks = sum(1 << i
               if (16 <= t < 32 or t == MT_ELEVATOR_DOOR
                   or (i >= 2 and with_downsolid and t == 8))
               else 0
               for (i, t) in blks)
    if not blks:
        return

    if blks == 0x0F:
        # F: all four blocks occupied; push all the way out
        # through the closest edge
        if dx < dy:
            return (-16, 0) if dx < -dy else (0, 16)
        else:
            return (0, -16) if dx < -dy else (16, 0)

    # If the object's center isn't already embedded in a cell, and
    # its bounding box doesn't straddle a cell boundary, copy the
    # cells in the row or column where it is to the row or column
    # where it isn't.  This way, blks represents only the contour
    # within the object's bounding box.  insideblk is as follows:
    # 0 1
    # 2 3
    insideblk = (1 if dx >= 0 else 0) | (2 if dy >= 0 else 0)
    embedded = (1 << insideblk) & blks
    if not embedded:
        if dx <= -rx:
            blks = (blks & 0x05)
            blks |= (blks << 1)
        elif dx >= rx:
            blks = (blks & 0x0A)
            blks |= (blks >> 1)
        if dy <= -ry:
            blks = (blks & 0x03)
            blks |= (blks << 2)
        elif dy >= ry:
            blks = (blks & 0x0C)
            blks |= (blks >> 2)
        if not blks:
            return

    # At this point we straddle a block.

    # But if there's only one block, in the opposite corner from the
    # object's center, push out of the corner.
    # Difference from WBB: support for rectangular objects
    if blks == (8 >> insideblk):
        if diag_corner_push:
            blks = 15 ^ (1 << insideblk)
        elif rx - abs(dx) <= ry - abs(dy):
            # Side of block is closer.
            blks |= 1 << (insideblk ^ 1)
        else:
            # Top or bottom of block is closer.
            blks |= 1 << (insideblk ^ 2)

    # Handle 1-corner and checkerboard configurations by
    # placing a block in the opposite corner.
    if blks in (1, 8, 9):
        blks |= 4 if dx > dy else 2
    elif blks in (2, 4, 6):
        # Find opposite corner across / from top right to bottom left
        blks |= 1 if dx > -dy else 8
    assert blks not in (0, 1, 2, 4, 6, 8, 9, 15)

    # remain:
    # 3, 7, B: push down
    # 5, 7, D: push right
    # A, B, E: push left
    # C, D, E: push up
    pushx, pushy = 0, 0
    if (blks & 0x05) == 0x05:
        pushx = rx - dx  # Right
    elif (blks & 0x0A) == 0x0A:
        pushx = -rx - dx  # Left
    if (blks & 0x03) == 0x03:
        pushy = ry - dy  # Down
    elif (blks & 0x0C) == 0x0C:
        pushy = -ry - dy  # Up
    assert pushx or pushy
    return pushx, pushy

def raycast(x1, y1, x2, y2):
    if x1 > x2:
        x1, y1, x2, y2 = x2, y2, x1, y1
    slope = (y2 - y1) / (x2 - x1)

    xt = int(x1 // 1)
    yt = int(y1 // 1)
    y2t = int(y2 // 1)

    while x1 <= x2:
        yield (xt, yt)
        # Find the top and bottom edges before the next left edge
##        print("raycast: Moving forward %.2f pixels" % ((xt + 1)  - x1))
        y1 += ((xt + 1) - x1) * slope
        lastyt, yt = yt, int(y1 // 1)
        x1 = (xt + 1)
##        print("x1, y1: %d,%.2f" % (x1, y1))
        while lastyt < yt:
            lastyt += 1
            yield (xt, lastyt)
            if lastyt == y2t and x1 > x2:
                return
        while lastyt > yt:
            lastyt -= 1
            yield (xt, lastyt)
            if lastyt == y2t and x1 > x2:
                return
        xt += 1

class Critter(object):
    hitbox_height = 8

    def __init__(self, game, view, x, y, facing_left=False):
        self.game = game
        self.view = view
        self.pos = [x * 16, y * 16 + 15]
        self.facing_left = facing_left
        self.yvel = 0
        self.walking_frame = 0
        self.mercy_time = 0

    def getblkat(self, x, y):
        x = int(x // 16) % 16
        y = int(y // 16)
        if y < 0:
            y += 12
        elif y >= 12:
            y -= 12
        return self.game.pf.getcell(x, y)

    def stun_test(self):
        for b in self.game.player_projectiles:
            if not b or not b.pos:
                continue
            dx = b.pos[0] - self.pos[0]
            dy = b.pos[1] - self.pos[1] + 8
            if (abs(dx) < 4 + self.hitbox_width
                and abs(dy) < 4 + self.hitbox_height):
                return True
        return False

    def draw16(self, screen, srcx, srcy, flip=0, dip=0):
        srcarea = (112 - srcx if flip & 1 else srcx,
                   112 - srcy if flip & 2 else srcy,
                   16, 16)
        dstpos = (int(self.pos[0]) - 8, int(self.pos[1]) + dip - 16)
        return screen.blit(self.view.spritegfx[flip], dstpos, srcarea)

class BaseWalkingCritter(Critter):
    ST_WALKING = 0
    ST_HANGING = 1
    ST_JUMPING = 2
    ST_ON_LADDER = 3
    can_hang = False
    jump_power = 1

    def __init__(self, game, view, x, y, facing_left=False):
        Critter.__init__(self, game, view, x, y, facing_left)
        self.state = self.ST_WALKING

    def onland(self):
        # use this to bounce (setting self.yvel negative)
        # or change direction, etc.
        pass

    def move(self, vkeys, new_vkeys):
        if not self.pos:
            return
        if vkeys & VK_RIGHT:
            self.pos[0] += self.x_spd
            if self.state == self.ST_WALKING:
                self.walking_frame += 32
            if self.facing_left and self.state == self.ST_HANGING:
                self.state = self.ST_JUMPING
            self.facing_left = False
        elif vkeys & VK_LEFT:
            self.pos[0] -= self.x_spd
            if self.state == self.ST_WALKING:
                self.walking_frame += 32
            if not self.facing_left and self.state == self.ST_HANGING:
                self.state = self.ST_JUMPING
            self.facing_left = True
        elif self.state == self.ST_WALKING:
            self.walking_frame = 128

        if self.state == self.ST_ON_LADDER:
            self.yvel = (-self.x_spd / 2
                         if vkeys & VK_UP
                         else self.x_spd / 2
                         if vkeys & VK_DOWN
                         else 0)
            if (self.getblkat(self.pos[0], self.pos[1] - 8) != 8
                and self.getblkat(self.pos[0], self.pos[1] + 1) != 8):
                self.state = self.ST_WALKING
        else:
            self.yvel = min(4, self.yvel + 0.125)
            if (new_vkeys & (VK_UP | VK_DOWN)) and not self.carrying_block:
                laddercheckoffset = 1 if new_vkeys & VK_DOWN else -1
                laddercheckblk = self.getblkat(self.pos[0], self.pos[1] + laddercheckoffset)
                if laddercheckblk == 8:
                    self.state = self.ST_ON_LADDER
        self.pos[1] = self.yvel + self.pos[1]

        # Treat ladders below player as solid if not already on a ladder
        ladders_below_are_solid = self.state not in (self.ST_ON_LADDER, self.ST_JUMPING)
        pushed = four_corner_collide(self.game.pf, self.pos[0], self.pos[1] - 8,
                                     self.hitbox_width, 8,
                                     ladders_below_are_solid,
                                     self.state == self.ST_ON_LADDER)
        on_floor = False
        can_jump = False
        if pushed:
            self.pos[0] += pushed[0]
            if pushed[1] > 0 or self.yvel > 0:
                self.pos[1] += pushed[1]
            if pushed[1] < 0:
                if self.yvel >= 0:
                    if self.yvel >= 0.25:
                        self.onland()
                    self.yvel = min(0, self.yvel)
                    on_floor = True
            elif pushed[1] > 0:
                self.yvel = max(0, self.yvel)

        if on_floor:
            can_jump = True
            if (self.state in (self.ST_JUMPING, self.ST_HANGING)
                or (self.state == self.ST_ON_LADDER and self.yvel > 0.25)):
                self.state = self.ST_WALKING
                self.walking_frame = 128
        elif (self.can_hang and self.yvel > 0 and not (vkeys & VK_DOWN)
              and not self.carrying_block):
            ledgetestx = self.pos[0] + (-5 if self.facing_left else 5)
            ledgesolidlo = 16 <= self.getblkat(ledgetestx, self.pos[1] - 14) < 32
            ledgesolidhi = 16 <= self.getblkat(ledgetestx, self.pos[1] - 18) < 32
            if ledgesolidlo and not ledgesolidhi:
                self.state = self.ST_HANGING
                self.yvel = 0
                self.pos[1] = (self.pos[1] + 8) // 16 * 16
                can_jump = True
        elif self.state == self.ST_ON_LADDER:
            can_jump = True

        if can_jump:
            jump_mask = ((VK_UP | VK_A)
                         if self.state != self.ST_ON_LADDER
                         else VK_A)
            if new_vkeys & jump_mask:
                self.yvel = (-self.hang_jump_power
                             if self.state == self.ST_HANGING
                             else -self.jump_power)
                self.state = self.ST_JUMPING
                if self.yvel < 0:
                    fxq('jump')

        return pushed

class BaseEnemyWalkingCritter(BaseWalkingCritter):
    ST_REPOSITION = 4

    def __init__(self, game, view, facing_left=False):
        BaseWalkingCritter.__init__(self, game, view, 8, 0)
        self.stun_time = 0
        self.reposition(facing_left)

    def reposition(self, facing_left=None):
        if facing_left is None:
            facing_left = not self.facing_left
        self.facing_left = facing_left

        # Move enemy toward the hole in the ceiling
        ceilcells = self.game.pf.getrow(0, 16, 0)
        openceilcells = [16 * i + 8 for i, c in enumerate(ceilcells) if c < 16]
        if openceilcells:
            x = max(min(self.pos[0], openceilcells[-1]), openceilcells[0])
            self.pos = [x, 0]
        else:
            print("no open ceiling cells:", repr(ceilcells))
        self.state = self.ST_JUMPING
        self.game.spawn_time += 30

    def move(self, advancing=True):
        if not self.pos:
            return
        if self.state == self.ST_REPOSITION:
            if self.game.spawn_time <= 0:
                self.reposition()
            return

        jumping = 0
        if self.stun_time > 0:
            self.stun_time -= 1
            if self.stun_time <= 0:
                jumping = VK_A
        vkeys = (0
                 if self.yvel > 0 or self.stun_time > 0 or not advancing
                 else VK_LEFT
                 if self.facing_left
                 else VK_RIGHT)
        pushed = BaseWalkingCritter.move(self, vkeys, jumping)
        if pushed:
            if pushed[0] > 0:
                # moved to the right, face right
                self.facing_left = False
            elif pushed[0] < 0:
                self.facing_left = True
        if self.pos[1] >= 192 or self.pos[0] < 8 or self.pos[0] > 248:
            self.state = self.ST_REPOSITION
        if self.mercy_time > 0:
            self.mercy_time -= 1
        elif self.stun_test():
            self.onhit()
        return pushed

    def onhit(self):
        fxq('knock')
        self.stun_time = 200
        self.mercy_time = 15

class PloddingCritter(BaseEnemyWalkingCritter):
    x_spd = 1
    hitbox_width = 7

    def draw(self, screen):
        if not self.pos or self.state == self.ST_REPOSITION:
            return []
        if self.walking_frame >= 1024:
            self.walking_frame -= 1024
        f = [0, 1, 2, 1][self.walking_frame // 256]
        xflip = 1 if self.facing_left else 0
        if self.stun_time > 0:
            xflip |= 2
        return [self.draw16(screen, 16 * f, 64, xflip)]

class BirdCritter(BaseEnemyWalkingCritter):
    x_spd = 2
    hitbox_width = 7

    def draw(self, screen):
        if not self.pos or self.state == self.ST_REPOSITION:
            return []
        if self.walking_frame >= 512:
            self.walking_frame -= 512
        f = self.walking_frame // 256
        xflip = 1 if self.facing_left else 0
        if self.stun_time > 0:
            xflip |= 2
        return [self.draw16(screen, 96 + 16 * f, 80, xflip, f)]

class ToasterCritter(BaseEnemyWalkingCritter):
    x_spd = 2
    hitbox_width = 7

    def __init__(self, *a, **kw):
        BaseEnemyWalkingCritter.__init__(self, *a, **kw)
        self.toast_time = 0

    def move(self):
        self.toast_time += 1
        pushed = BaseEnemyWalkingCritter.move(self, advancing=self.toast_time >= 0)
        on_floor = pushed and pushed[1] < 0
        if self.toast_time >= 180 and on_floor and self.stun_time <= 0:
            self.toast_time = -60
            bullet = Toast(self.game, self.view, self.pos[0], self.pos[1] - 8)
            self.game.enemy_projectiles.append(bullet)
            self.onland()  # turn randomly when firing

            # Turn randomly after firing
            from random import randint
            self.facing_left = bool(randint(0, 1))
            self.onland()  # Turn vaguely toward player

    def onland(self):
        """Turn the enemy if far from the player or if landing next to a cliff.

"""
        if self.pos[0] < 48:
            self.facing_left = False
            return
        if self.pos[0] >= 208:
            self.facing_left = True
            return
        playerdist = self.game.player.pos[0] - self.pos[0]
        if playerdist > 96:
            self.facing_left = False
            return
        elif playerdist < -96:
            self.facing_left = True
            return
        
        gc = self.game.pf.getcell
        xd = int(self.pos[0] // 16) + (-1 if self.facing_left else 1)
        yd = int((self.pos[1] + 8) // 16)
        c = gc(xd, yd) if 0 <= xd < 16 and 0 <= yd < 12 else 0
        if c < 16 and c != 8:
            print("not driving off cliff at %d,%d" % (xd, yd))
            self.facing_left = not self.facing_left

    def draw(self, screen):
        if not self.pos or self.state == self.ST_REPOSITION:
            return []
        self.walking_frame = 0
        xflip = 0  # toaster does not flip
        rects = [self.draw16(screen, 16, 80, xflip)]

        # draw lever
        srcx = 32
        srcy = 80
        if self.toast_time >= 0:
            dip = min(5, self.toast_time // 32)
        else:
            dip = max(0, -55 - self.toast_time)
        srcarea = (120 - srcx if xflip & 1 else srcx, srcy, 8, 8)
        dstpos = (int(self.pos[0]) - 8, int(self.pos[1]) + dip - 16)
        rects.append(screen.blit(self.view.spritegfx[0], dstpos, srcarea))
        return rects

class SneakerCritter(BaseEnemyWalkingCritter):
    x_spd = 3
    hitbox_width = 7
    hitbox_height = 7

    def __init__(self, *a, **k):
        BaseEnemyWalkingCritter.__init__(self, *a, **k)
        self.damaged = 0  # counts up to 16 after damaged; invulnerable 1-15
        self.crouchtestx = self.pos[0] // 16
        self.crouch_time = 0

    def block_is_threat(self, blk):
        if not blk.pos:
            return False
        dy = blk.pos[1] - self.pos[1]
        if dy > 32:  # below self
            return False
        dx = blk.pos[0] - self.pos[0]
        if self.facing_left:
            dx = -dx
        if dx < -12:  # can't see behind self
            return False
        blk_left = blk.xvel < 0
        facing_diff = not blk_left if self.facing_left else blk_left
        return facing_diff

    def block_in_the_way(self, other_pos):
        gc = self.game.pf.getcell
        x1, y1 = self.pos
        x2, y2 = other_pos

        p_x, p_y = self.game.player.pos
        traced = raycast(x1 / 16, (y1 - 8) / 16, x2 / 16, (y2 - 8) / 16)
        return any(16 <= gc(x, y) < 32 for (x, y) in traced)
        
    def player_is_threat(self, p):
        """Determine whether another critter is a "threat" to this critter.

Another not carrying a block is not a threat.
Another facing the same direction (that is, facing away) is not a threat.
Another behind self is not a threat.
Another more than 45 degrees above or below the horizontal line
through self is not a threat.
TO DO: Another with blocks preventing eye contact is not a threat.

"""
        if not p.carrying_block:
            return False
        facing_diff = not p.facing_left if self.facing_left else p.facing_left
        if not facing_diff:
            return False
        dy = p.pos[1] - self.pos[1]
        dx = p.pos[0] - self.pos[0]
        if abs(dy) > abs(dx):  # can't see more than 45 deg up or down
            return False
        if self.facing_left:   # assume w/o loss of generality that self faces R
            dx = -dx
        if dx < 0:  # can't see behind self
            return False
        if self.block_in_the_way(p.pos):
            return False
        return True

    def update_crouching(self):

        # If damaged or falling, stand.
        if self.damaged or self.yvel > 0:
            self.crouch_time = 0
            return False

        # If crouched, stay crouched for a while.
        if self.crouch_time > 0:
            self.crouch_time -= 1
            if self.crouch_time > 0:
                return True
        else:
            # If not crouched, stand until leaving this column.
            xt = self.pos[0] // 16
            if xt == self.crouchtestx:
                return False
            else:
                self.crouchtestx = xt

        # If threatened by a block or player, crouch.
        if (any(self.block_is_threat(blk)
                for blk in self.game.player_projectiles)
            or self.player_is_threat(self.game.player)):
            self.crouch_time = 30
            return True

        return False

    def onhit(self):
        if self.damaged == 0 and self.crouch_time > 0:
            self.stun_time = 0
            self.damaged = 1
            self.mercy_time = 15
            fxq('sneakerdmg')
            return
        BaseEnemyWalkingCritter.onhit(self)

    def move(self):
        crouched = self.update_crouching()
        BaseEnemyWalkingCritter.move(self, not crouched)

    def draw(self, screen):
        if not self.pos or self.state == self.ST_REPOSITION:
            return []
        xflip = 1 if self.facing_left else 0
        if self.crouch_time > 0 and self.stun_time == 0:
            srcx = 48
            srcy = 64
            srcarea = (112 - srcx if xflip & 1 else srcx, srcy,
                       16, 8)
            dstpos = (int(self.pos[0]) - 8, int(self.pos[1]) - 8)
            return [screen.blit(self.view.spritegfx[xflip], dstpos, srcarea)]
            
        if self.walking_frame >= 256:
            self.walking_frame -= 256
        f = self.walking_frame // 128
        if self.stun_time > 0:
            xflip |= 2
        return [self.draw16(screen, 48 + 16 * f, 64, xflip, 1)]

class BaseFlyingCritter(Critter):
    ST_WALKING = 0
    ST_HANGING = 1
    ST_JUMPING = 2
    can_hang = False
    jump_power = 0

    def __init__(self, game, view, facing_left=False):
        Critter.__init__(self, game, view, 0, 0)
        self.stun_time = 0
        self.reposition(facing_left)

    def reposition(self, facing_left=None):
        from random import randint
        if facing_left is None:
            facing_left = not self.facing_left
        self.facing_left = facing_left

        y = 5 * randint(0, 31) + 18
        self.pos = [252 if facing_left else 4, y]
        self.stun_time = 15  # allow player to get out of way

    def move(self):
        if not self.pos:
            return
        if self.stun_time > 0:
            self.stun_time -= 1
        elif self.facing_left:
            self.pos[0] -= self.x_spd
            if self.pos[0] < 0:
                self.reposition()
        else:
            self.pos[0] += self.x_spd
            if self.pos[0] >= 256:
                self.reposition()
        if self.mercy_time > 0:
            self.mercy_time -= 1
        elif self.stun_test():
            fxq('knock')
            self.stun_time = 200
            self.mercy_time = 15

class SpinningCritter(BaseFlyingCritter):
    x_spd = 1
    hitbox_width = 7

    def draw(self, screen):
        if not self.pos:
            return []
        f = self.walking_frame // 256
        xflip = 1 if self.facing_left else 0
        if f == 3:
            f = 1
            xflip ^= f
        self.walking_frame = (self.walking_frame + 64) % 1024
        return [self.draw16(screen, 80 + 16 * f, 64, xflip)]

class BurgerCritter(BaseFlyingCritter):
    x_spd = 3
    hitbox_width = 7

    def draw(self, screen):
        if not self.pos:
            return []
        xflip = 1 if self.facing_left else 0
        return [self.draw16(screen, 0, 80, xflip)]

class EnemyFactory(object):
    enemymap = {
        'plodder': PloddingCritter,
        'spinner': SpinningCritter,
        'burger': BurgerCritter,
        'pecker': BirdCritter,
        'sneaker': SneakerCritter,
        'toaster': ToasterCritter,
    }

    def __init__(self, leveldata, game, view):
        from itertools import cycle
        (levelname, mapid, limit, enemies, looped) = leveldata[:5]
        self.game = game
        self.view = view
        self.limit = limit
        self.iterenemies = cycle(enemies) if looped else iter(enemies)
        self.timer = 0
        self.facing_left = False

    def __iter__(self):
        return self

    def __next__(self):
        # remove dead enemies in list
        pfen = [e for e in self.game.enemies if e and e.pos]
        self.game.enemies[:] = pfen

        if self.game.spawn_time > 0:
            self.game.spawn_time -= 1
        if self.limit == 0 and len(pfen) == 0:
            raise StopIteration
        if self.game.spawn_time > 0 or len(pfen) >= self.limit:
            return None
        self.game.spawn_time = 30
        try:
            nx = next(self.iterenemies)
        except StopIteration:
            self.iterenemies = None
            self.limit = 0
            return None
        else:
            new_enemy = self.enemymap[nx](self.game, self.view, self.facing_left)
            self.facing_left = not self.facing_left
            return new_enemy

class Toast(Critter):
    hitbox_width = 3
    hitbox_height = 4

    def __init__(self, game, view, x, y):
        Critter.__init__(self, game, view, 0, 0)
        self.stun_time = 0
        self.pos = [x, y]
        self.yvel = -3

    def move(self):
        self.pos[1] += self.yvel
        self.yvel += .125
        if self.pos[1] >= 184:
            self.pos = None
            return

    def draw(self, screen):
        if not self.pos:
            return []
        srcarea = (32, 88, 8, 8)
        dstpos = (int(self.pos[0]) - 4, int(self.pos[1]) - 8)
        return [screen.blit(self.view.spritegfx[0], dstpos, srcarea)]

class Poof(Critter):
    hitbox_width = 0
    hitbox_height = 0

    def __init__(self, game, view, x, y):
        Critter.__init__(self, game, view, 0, 0)
        self.stun_time = 0
        self.pos = [x, y]
        self.yvel = -3

    def move(self):
        self.walking_frame += 1

    def draw(self, screen):
        progress = self.walking_frame
        f = progress // 8
        if f >= 3:
            self.pos = None
        if not self.pos:
            return []
        sep = max(0, progress - 8) // 4 + 4
        xbase, ybase = int(self.pos[0]) - 4, int(self.pos[1]) - 12
        srcx = 40 + 8 * f
        cmds = [(0, (xbase - sep, ybase - sep), (srcx, 80, 8, 8)),
                (3, (xbase + sep, ybase - sep), (120 - srcx, 120 - 88, 8, 8)),
                (0, (xbase - sep, ybase + sep), (srcx, 88, 8, 8)),
                (3, (xbase + sep, ybase + sep), (120 - srcx, 120 - 80, 8, 8))]
        return [screen.blit(self.view.spritegfx[flip], dstpos, srcarea)
                for (flip, dstpos, srcarea) in cmds]

TabCritter = SneakerCritter

class ChipCritter(BaseFlyingCritter):
    x_spd = 1
    hitbox_width = 4
    hitbox_height = 4

    def __init__(self, game, view, factory):
        self.factory = factory
        BaseFlyingCritter.__init__(self, game, view)

    def reposition(self, ignored1=None):
        row, self.facing_left = self.factory.get_next_row()
        y = 16 * row + 12
        self.pos = [252 if self.facing_left else 4, y]

    def draw(self, screen):
        if not self.pos:
            return []
        srcarea = (24, 24, 8, 8)
        dstpos = (int(self.pos[0]) - 4, int(self.pos[1]) - 8)
        return [screen.blit(self.view.spritegfx[0], dstpos, srcarea)]

class ChipFactory(object):
    def __init__(self, avoid_y, game, view):
        self.game = game
        self.view = view
        self.y_lru = [1, 9, 3, 7, 2, 8, 4, 6, 5]
        self.facing_left = False
        try:
            i = self.y_lru.index(avoid_y)
        except IndexError:
            pass
        else:
            self.y_lru[i], self.y_lru[-1] = self.y_lru[-1], self.y_lru[i]
        self.chips = []

    def get_next_row(self):
        from random import randint

        pull_idx = randint(0, 1) if len(self.y_lru) >= 4 else 0        
        pulled = self.y_lru.pop(pull_idx)
        self.y_lru.append(pulled)
        self.facing_left = not self.facing_left
        return pulled, self.facing_left

    def collect(self, pos):
        row = int(pos[1] // 16)
        try:
            self.y_lru.remove(row)
        except IndexError:
            pass
        else:
            fxq('getchip')
            num = 9 - len(self.y_lru)
            if 1 <= num <= 8:
                dig = FloatingDigit(self.game, self.view, pos[0], pos[1], num)
                self.game.enemy_projectiles.append(dig)

    def move(self):
        # remove dead enemies in list
        px, py = self.game.player.pos
        for e in self.chips:
            e.move()
            dy = e.pos[1] + 4 - py
            dx = e.pos[0] - px
            if abs(dx) < 8 and abs(dy) < 12:
                self.collect(e.pos)
                e.pos = None
        
        pfen = [e for e in self.chips if e and e.pos]
        self.chips[:] = pfen

        if len(self.y_lru) == 0:
            return True
        if len(pfen) < min(2, len(self.y_lru)):
            self.chips.append(ChipCritter(self.game, self.view, self))

    def draw(self, screen):
        rects = []
        for e in self.chips:
            if e and e.pos:
                rects.extend(e.draw(screen))
        return rects

class FloatingDigit(Critter):
    hitbox_width = 0
    hitbox_height = 0

    def __init__(self, game, view, x, y, num):
        Critter.__init__(self, game, view, 0, 0)
        self.walking_frame = 0
        self.pos = [x, y]
        self.num = num

    def move(self):
        self.walking_frame += 1

    def draw(self, screen):
        if self.walking_frame >= 32:
            self.pos = None
        if not self.pos:
            return []
        dstpos = (int(self.pos[0]) - 4,
                  int(self.pos[1]) - 8 - (self.walking_frame // 4))
        srcarea = (8 * (self.num - 1), 32, 8, 8)
        return [screen.blit(self.view.spritegfx[0], dstpos, srcarea)]

