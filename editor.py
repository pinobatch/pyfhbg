#!/usr/bin/env python3
import pygame as G
import mtplane
from events import VK_A, VK_B, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT
from events import read_pads, translate_events, VK_SELECT, VK_START
from loadlevel import connect_level, randomize_level_bg, load_levels, save_levels
from enemy import enemies_gfxcoords, enemies_minitiles

user_levels_filename = 'editor_level.ini'

class EditorSession(object):
    DIRTY_BORDER = 0x01
    DIRTY_COLOR = 0x02
    DIRTY_ENEMIES = 0x04
    DIRTY_SETTINGS = 0x08
    DIRTY_ALL = DIRTY_ENEMIES | DIRTY_BORDER | DIRTY_COLOR | DIRTY_SETTINGS

    MODE_PLACE_BLOCKS = 0
    MODE_MOVE_DOOR = 1
    MODE_EDIT_ENEMIES = 2
    MODE_EDIT_SETTINGS = 3

    def __init__(self, view, game):
        from fhbgui import SmallLevelMap
        from mtplane import MetatilePlane

        try:
            maps, levels = load_levels(user_levels_filename)
            self.level = levels[0]
            self.map = maps[0]
            self.mapdata = self.map[-1]
        except Exception as e:
            print("Level loading failed: %s" % e)
            self.level = ['User level', 0, 1, ['plodder', 'toaster'], 0]
            self.mapdata = bytearray(160)
            self.mapdata.extend(bytes([16])*16)
            self.map = ['user_map', (2, 9), self.mapdata]
            
        self.view = view
        self.game = game
        self.slm = SmallLevelMap(view, 96, 24)
        self.cursor_x = 1
        self.cursor_y = 1
        self.cur_color = 0
        self.moved_since_b = True
        self.enemy_names = ['']
        self.enemy_names.extend(sorted(enemies_gfxcoords))
        self.enemy_name_to_idx = dict((b, a) for (a, b) in enumerate(self.enemy_names))
        self.dirty = self.DIRTY_ALL
        for x in range(16):
            self.updatecol(x)
        self.mode = 0

    def __enter__(self):
        self.old_maps_levels = self.game.levelmaps, self.game.levels
        self.game.levelmaps = [self.map]
        self.game.levels = [self.level]
        return None  # what I return from __enter__ goes into the 'as' variable

    def __exit__(self, et, ev, tb):
        self.game.levelmaps, self.game.levels = self.old_maps_levels
        self.old_maps_levels = None

    def updatecol(self, x):
        self.slm.setcol(x, 0, self.mapdata[x::16])
        doorx, doory = self.map[1]
        if x == doorx:
            self.slm.setcol(doorx, doory - 1, [12, 13])

    def add_enemy(self, x, offset):
        while len(self.level[3]) <= x:
            self.level[3].append('')
        eid = self.enemy_name_to_idx[self.level[3][x]] + offset
        self.level[3][x] = self.enemy_names[eid % len(self.enemy_names)]
        self.dirty |= self.DIRTY_ENEMIES

    def set_mode(self, mode):
        old_mode = self.mode
        if self.MODE_PLACE_BLOCKS in (mode, old_mode):
            self.dirty |= self.DIRTY_COLOR
        if self.MODE_EDIT_ENEMIES in (mode, old_mode):
            self.dirty |= self.DIRTY_ENEMIES
        if self.MODE_EDIT_SETTINGS in (mode, old_mode):
            self.dirty |= self.DIRTY_SETTINGS
        if mode < 2:
            self.cursor_x, self.cursor_y = self.map[1]
            self.moved_since_b = False
        else:
            self.cursor_x, self.cursor_y = 0, 0
        self.mode = mode

    def redrawdirty(self):
        screen = self.view.display.get_surface()
        blocktypesbgcolor = (255, 255, 255)
        screenbgcolor = (102, 102, 102)
        txo = self.view.font.textout
        solidblkarea = (0, 24, 8, 8)
        hollowblkarea = (16, 24, 8, 8)
        if self.dirty & self.DIRTY_BORDER:
            self.dirty = self.DIRTY_ALL & ~self.DIRTY_BORDER
            self.slm.cleardirty(True)
            screen.fill(screenbgcolor)

            # redraw block type swatches
            screen.fill(blocktypesbgcolor, (24, 24, 32, 56))
            screen.blit(self.view.bggfx, (40, 32), (0, 0, 8, 8))
            screen.blit(self.view.bggfx, (40, 48), (0, 8, 8, 8))
            screen.blit(self.view.bggfx, (40, 64), (8, 8, 8, 8))
            
            txo(screen, "limit:", 16, 88)
            txo(screen, "goal:", 16, 112)
##            txo(screen, "set3:", 16, 136)
        if self.dirty & self.DIRTY_COLOR:
            self.dirty &= ~self.DIRTY_COLOR
            for i in range(3):
                dstpos = (32, 32 + 16 * i)
                screen.fill(blocktypesbgcolor, dstpos + (8, 8))
                if self.mode == self.MODE_PLACE_BLOCKS and i == self.cur_color:
                    screen.blit(self.view.spritegfx[0], dstpos, solidblkarea)
        if self.dirty & self.DIRTY_ENEMIES:
            self.dirty &= ~self.DIRTY_ENEMIES
            screen.fill(screenbgcolor, (92, 112, 136, 16))
            enemies = self.level[3]
            for i, enemy in enumerate(enemies[:16]):
                if not enemy:
                    continue
                if self.mode == self.MODE_EDIT_ENEMIES and i == self.cursor_x:
                    continue
                t = enemies_minitiles[enemy]
                srcarea = ((t % 16) * 8, (t // 16) * 8, 8, 8)
                dstpos = i * 8 + 96, 120
                screen.blit(self.view.bggfx, dstpos, srcarea)
            if self.mode == self.MODE_EDIT_ENEMIES:
                i = self.cursor_x
                enemy = (enemies[self.cursor_x]
                         if self.cursor_x < len(enemies)
                         else '')
                if enemy:
                    x, y = enemies_gfxcoords[enemy]
                    srcarea = (x - 8, y, 16, 16)
                    dstpos = i * 8 + 92, 112
                else:
                    srcarea = solidblkarea
                    dstpos = i * 8 + 96, 116
                screen.blit(self.view.spritegfx[0], dstpos, srcarea)
        if self.dirty & self.DIRTY_SETTINGS:
            self.dirty &= ~self.DIRTY_SETTINGS
            screen.fill(screenbgcolor, (16, 96, 32, 8))
            txo(screen, "%3d" % self.level[2], 24, 96)
            screen.fill(screenbgcolor, (16, 120, 80, 8))
            txo(screen, "get chips" if self.level[4] else "kill all", 24, 120)
            if self.mode == self.MODE_EDIT_SETTINGS:
                dstpos = (16, self.cursor_y * 24 + 96)
                screen.blit(self.view.spritegfx[0], dstpos, solidblkarea)

        # Draw the playfield, and draw the cursor on it if needed
        self.slm.slm_redrawdirty()
        if self.mode in (self.MODE_PLACE_BLOCKS, self.MODE_MOVE_DOOR):
            dstpos = (8 * self.cursor_x, 8 * self.cursor_y)
            cursorrect = self.slm.pfdst.blit(self.view.spritegfx[0],
                                             dstpos, hollowblkarea)
            self.slm.setdirtyrects([cursorrect])

    def handle_vkeys_enemies(self, new_vkeys):
        xmax = min(15, len(self.level[3]))
        if new_vkeys & VK_RIGHT:
            self.dirty |= self.DIRTY_ENEMIES
            self.cursor_x += 1
            if self.cursor_x > xmax:
                self.cursor_x = 0
        if new_vkeys & VK_LEFT:
            self.dirty |= self.DIRTY_ENEMIES
            self.cursor_x -= 1
            if self.cursor_x < 0:
                self.cursor_x = xmax
        if new_vkeys & VK_UP:
            self.add_enemy(self.cursor_x, 1)
        if new_vkeys & VK_DOWN:
            self.add_enemy(self.cursor_x, -1)

    def handle_vkeys_settings(self, new_vkeys):
        if new_vkeys & VK_UP:
            self.dirty |= self.DIRTY_SETTINGS
            self.cursor_y = (self.cursor_y - 1) % 2
        if new_vkeys & VK_DOWN:
            self.dirty |= self.DIRTY_SETTINGS
            self.cursor_y = (self.cursor_y + 1) % 2
        if self.cursor_y == 0:  # limit
            if new_vkeys & VK_LEFT:
                self.level[2] -= 1
                self.dirty |= self.DIRTY_SETTINGS
            if new_vkeys & VK_RIGHT:
                self.level[2] += 1
                self.dirty |= self.DIRTY_SETTINGS
            self.level[2] = min(7, max(1, self.level[2]))
        if self.cursor_y == 1:  # goal
            if new_vkeys & (VK_LEFT | VK_RIGHT):
                self.level[4] = 0 if self.level[4] else 9
                self.dirty |= self.DIRTY_SETTINGS

    def handle_vkeys(self, new_vkeys):
        if new_vkeys & VK_SELECT:
            self.set_mode((self.mode + 1) % 4)
            return
        if (new_vkeys & VK_B) and self.mode != 0:
            self.set_mode(0)
            return
        if self.mode == self.MODE_EDIT_ENEMIES:
            return self.handle_vkeys_enemies(new_vkeys)
        if self.mode == self.MODE_EDIT_SETTINGS:
            return self.handle_vkeys_settings(new_vkeys)

        if new_vkeys & VK_LEFT:
            self.moved_since_b = True
            self.cursor_x = (self.cursor_x - 1) % 16
        if new_vkeys & VK_RIGHT:
            self.moved_since_b = True
            self.cursor_x = (self.cursor_x + 1) % 16
        if new_vkeys & VK_UP:
            self.moved_since_b = True
            self.cursor_y = (self.cursor_y - 1) % 11
            if self.mode == self.MODE_MOVE_DOOR:
                self.cursor_y = max(1, self.cursor_y)
        if new_vkeys & VK_DOWN:
            self.moved_since_b = True
            self.cursor_y = (self.cursor_y + 1) % 11
            if self.mode == self.MODE_MOVE_DOOR:
                self.cursor_y = min(9, self.cursor_y)
        if (new_vkeys & VK_A) and self.mode == self.MODE_PLACE_BLOCKS:
            self.mapdata[16 * self.cursor_y + self.cursor_x] = self.cur_color << 3
            self.updatecol(self.cursor_x)
        if (new_vkeys & VK_B) and self.mode == self.MODE_PLACE_BLOCKS:
            if self.moved_since_b:
                c = self.mapdata[16 * self.cursor_y + self.cursor_x]
                self.cur_color = min(2, c >> 3)
                self.moved_since_b = False
            else:
                self.cur_color = (self.cur_color + 1) % 3
            self.dirty |= self.DIRTY_COLOR
        if self.mode == self.MODE_MOVE_DOOR and self.moved_since_b:
            oldx = self.map[1][0]
            self.map[1] = self.cursor_x, self.cursor_y
            if oldx != self.cursor_x:
                self.updatecol(oldx)
            self.updatecol(self.cursor_x)
            self.moved_since_b = False

def editor(view, game, play_level):
    es = EditorSession(view, game)
    done = False
    clk = G.time.Clock()
    VK_BACK = 0x2000
    addlkeys = [
        (G.K_RETURN, 0, VK_START), (G.K_ESCAPE, 0, VK_BACK),
        (G.K_TAB, 0, VK_SELECT), 
        (G.K_LEFT, 0, VK_LEFT), (G.K_RIGHT, 0, VK_RIGHT),
        (G.K_UP, 0, VK_UP), (G.K_RIGHT, 0, VK_DOWN)
    ]
    while not done:
        key_vkeys = 0
        event_vkeys, other_events = translate_events(addlkeys)
        (vkeys, new_vkeys) = read_pads(view)
        new_vkeys |= event_vkeys

        if es.moved_since_b and es.mode == es.MODE_PLACE_BLOCKS:
            new_vkeys |= vkeys & (VK_A | VK_B)
        es.handle_vkeys(new_vkeys)

        if new_vkeys & VK_BACK:
            done = True
        if new_vkeys & VK_START:
            if vkeys & VK_SELECT:
                done = True
            else:
                es.level[3][:] = [e for e in es.level[3] if e]
                connect_level(es.mapdata)
                randomize_level_bg(es.mapdata)
                game.new_game()
                game.pf.sheet = view.metatile_sheet
##                with es:
                play_level(view, game, es.level, es.map)
                es.dirty = es.DIRTY_ALL

        es.redrawdirty()
        clk.tick(60)
        view.display.flip()
    save_levels(user_levels_filename, [es.map], [es.level])
