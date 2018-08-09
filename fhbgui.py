#!/usr/bin/env python3
from __future__ import with_statement, division, print_function, unicode_literals
import array
try:
    range
except NameError:
    range = range
import pygame as G
import ascii, chipsfx, loadlevel, mtplane
from enemy import enemies_gfxcoords
from events import translate_events, read_pads, VK_SELECT, VK_START
from events import VK_A, VK_B, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT

def press_a_key(view, vkeyfilter=VK_A|VK_START, addlkeys=[], waiting_time=30):
    """Wait for the player to press one of the keys in keys_set or the A button.

Return the vkey that caused closing.

"""
    done = False
    clk = G.time.Clock()
    while not done:
        event_vkeys, other_events = translate_events(addlkeys)
        (vkeys, new_vkeys) = read_pads(view)
        if waiting_time > 0:
            waiting_time -= 1
            new_vkeys = 0
        done = (new_vkeys | event_vkeys) & vkeyfilter
        clk.tick(60)
        view.display.flip()
    return done

def coprscreen(view, notice, with_tab=False):
    """Display a screen full of text, then wait for Enter, Esc.

Return the vkey that caused the form to close.
If with_tab, Tab also works; it's bound to VK_SELECT.

"""
    enl = view.display
    textout = view.font.textout
    screen = enl.get_surface()
    screen.fill((102, 102, 102))
    for y, txt in enumerate(notice.split('\n')):
        textout(screen, txt, 16, y * 8)
    keys = [(G.K_RETURN, 0, VK_START), (G.K_ESCAPE, 0, VK_B), (G.K_TAB, 0, VK_SELECT)]
    vkeyfilter = VK_A|VK_B|VK_START
    if with_tab:
        vkeyfilter |= VK_SELECT
    return press_a_key(view, vkeyfilter=vkeyfilter, addlkeys=keys)

def preroll(view, level):
    textout = view.font.textout
    enl = view.display
    lvname = level[0]
    enemyseq = level[3]
    screen = enl.get_surface()
    screen.fill((102, 102, 102))
    textout(screen, lvname, 64, 64)
    for i, enemy in enumerate(enemyseq):
        x, y = enemies_gfxcoords[enemy]
        dstpos = (64 + 8 * i, 80)
        srcarea = (120 - x, y, 8, 8)
        screen.blit(view.spritegfx[1], dstpos, srcarea)
    return press_a_key(view)

def gameover(view, num_levels):
    textout = view.font.textout
    enl = view.display
    screen = enl.get_surface()
    screen.fill((102, 102, 102))
    textout(screen, "Game Over", 64, 64)
    plural = "Cleared %d room" if num_levels == 1 else "Cleared %d rooms"
    textout(screen, plural % num_levels, 64, 80)
    return press_a_key(view)

class SmallLevelMap(mtplane.MetatilePlane):
    tilemapping = {0x08:0x10,0x0C:0xD3,0x0D:0xF3}
    def __init__(self, view, left, top):
        mtplane.MetatilePlane.__init__(self, height=11, tw=8, th=8)
        self.sheet = view.bggfx
        screen = view.display.get_surface()
        self.pfdst = screen.subsurface((left, top, 128, 88))

    def setcell(self, x, y, c):
        if y < 0:
            return
        c = 0x11 if 16 <= c < 32 else self.tilemapping.get(c, 0)
        mtplane.MetatilePlane.setcell(self, x, y, c)

    def load_map(self, levelmap):
        from itertools import chain, repeat
        sc = self.setcell
        data = chain(levelmap, repeat(0))
        for y in range(11):
            for x in range(16):
                sc(x, y, next(data))

    def slm_redrawdirty(self):
        return self.redrawdirty(self.pfdst, 0, 0)

def level_select(view, game, selected=0):
    textout = view.font.textout
    enl = view.display
    screen = enl.get_surface()
    screen.fill((102, 102, 102))
    level_dirty = True

    slm = SmallLevelMap(view, 64, 80)
    
    done = False
    clk = G.time.Clock()
    addlkeys = [
        (G.K_RETURN, 0, VK_START), (G.K_ESCAPE, 0, VK_B),
        (G.K_TAB, 0, VK_SELECT),
        (G.K_LEFT, 0, VK_LEFT), (G.K_RIGHT, 0, VK_RIGHT)
    ]
    while not done:
        key_vkeys = 0
        event_vkeys, other_events = translate_events(addlkeys)
        (vkeys, new_vkeys) = read_pads(view)
        new_vkeys |= event_vkeys
        if new_vkeys & VK_LEFT:
            selected -= 1
            if selected < 0:
                selected = len(game.levels) - 1
            level_dirty = True
        if new_vkeys & VK_RIGHT:
            selected += 1
            if selected >= len(game.levels):
                selected = 0
            level_dirty = True
        if new_vkeys & (VK_A | VK_START):
            done = VK_A
        if new_vkeys & VK_B:
            selected = -1
            done = VK_B
        if level_dirty and 0 <= selected < len(game.levels):
            screen.fill((102, 102, 102), (0, 8, 256, 8))
            textout(screen, "Level %d" % (selected + 1), 16, 8)
            screen.fill((102, 102, 102), (0, 24, 256, 24))
            level = game.levels[selected]
            textout(screen, level[0], 16, 24)
            enemyseq = level[3]
            for i, enemy in enumerate(enemyseq):
                x, y = enemies_gfxcoords[enemy]
                dstpos = (16 + 8 * i, 40)
                srcarea = (120 - x, y, 8, 8)
                screen.blit(view.spritegfx[1], dstpos, srcarea)
            levelmap = game.levelmaps[level[1]][2]
            slm.load_map(levelmap)
            slm.slm_redrawdirty()
            level_dirty = False
        clk.tick(60)
        enl.flip()
    return done, selected

def titlescreen(view):
    textout = view.font.textout
    enl = view.display
    title = G.image.load('tilesets/title.png').convert_alpha()
    options = ['play', 'controls', 'practice', 'edit', 'help', 'quit']
    screen = enl.get_surface()
    screen.blit(title, (0, 0))
    done = False
    clk = G.time.Clock()
    textout(screen, "forehead block guy", 24, 80, (102, 102, 102))
    for i, txt in enumerate(options):
        y = 120 + 8 * (i % 4)
        x = 72 + 80 * (i // 4)
        textout(screen, txt, x + 8, y, (0, 0, 0))
    selected = 0
    last_selected = -1
    last_col_top = (-(-len(options) // 4) - 1) * 4
    addlkeys = [
        (G.K_RETURN, 0, VK_START), (G.K_ESCAPE, 0, VK_B|VK_START), (G.K_TAB, 0, VK_SELECT),
        (G.K_LEFT, 0, VK_LEFT), (G.K_RIGHT, 0, VK_RIGHT),
        (G.K_DOWN, 0, VK_DOWN), (G.K_UP, 0, VK_UP),
    ]
    while not done:
        event_vkeys, other_events = translate_events(addlkeys)
        (vkeys, new_vkeys) = read_pads(view)
        new_vkeys |= event_vkeys
        if new_vkeys & VK_UP:
            selected -= 1
            if selected < 0:
                selected = len(options) - 1
        if new_vkeys & (VK_DOWN|VK_SELECT):
            selected += 1
            if selected >= len(options):
                selected = 0
        if new_vkeys & VK_LEFT:
            if selected < 4:
                selected = min(selected + last_col_top, len(options) - 1)
            else:
                selected -= 4
        if new_vkeys & VK_RIGHT:
            if selected >= last_col_top:
                selected = selected % 4
            else:
                selected = min(selected + 4, len(options) - 1)
        if new_vkeys & VK_B:
            selected = len(options) - 1
        if new_vkeys & (VK_A|VK_START):
            done = True
        if selected != last_selected:
            if last_selected >= 0:
                y = 120 + 8 * (last_selected % 4)
                x = 72 + 80 * (last_selected // 4)
                screen.blit(title, (x, y), (x, y, 8, 8))
            if selected >= 0:
                y = 120 + 8 * (selected % 4)
                x = 72 + 80 * (selected // 4)
                screen.blit(view.spritegfx[0], (x, y), (0, 24, 8, 8))
            last_selected = selected
        clk.tick(60)
        enl.flip()
    if selected == len(options) - 1:
        selected = -1
    return selected

