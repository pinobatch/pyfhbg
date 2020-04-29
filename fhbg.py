#!/usr/bin/env python3
from __future__ import with_statement, division, print_function, unicode_literals
import pygame as G
import ascii, chipsfx, joycfg, loadlevel, mtplane
from events import VK_A, VK_B, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT
from events import translate_events, VK_SELECT, VK_START
from fhbgui import read_pads

action_names = [
    'Up', 'Down', 'Left', 'Right',
    'Jump', 'Fire', 'Select', 'Start'
]
keybindings_filename = "fhbg.kyb"
mixer_freq = 44100
with_double = True
with_fullscreen = False
with_music = True

# False (no video output), True (raw RGB24 frames to vtee.raw),
# or 'pipe' (through vidcap_pipe_cmd)
# use -c:v png for all intraframes
# or -c:v zmbv for intraframes and deltaframes
# but apparently avconv version 0.8.6-4:0.8.6-0ubuntu0.12.04.1 can't
# encode using any pixel format but "pal8" (that is, indexed color),
# and it can't convert RGB to indexed color either: "Incompatible
# pixel format 'rgb24' for codec 'zmbv', auto-selecting format 'pal8'"
# I tried Bisqwit's ZMBV encoder but it supports only BGR and Pygame
# supports only RGB.
with_vidcap = False
vidcap_pipe_cmd = r"""avconv -f rawvideo -r 30 -pix_fmt rgb24 -s "256x176" -y -an -i - -c:v png fhbg.avi"""
##vidcap_pipe_cmd = r"""zmbv/zmbv_encoder -o fhbg.avi --width 256 --height 176 --bpp 24 --swapredblue --fps 30"""

todoNotice = """
PyFHBG 0.02
Copr. 2011-2013 Joshua
Hoffman and Damian Yerrick

Concept by Joshua Hoffman
<http://novasquirrel.com/>
Program and graphics by
Damian Yerrick
<http://pineight.com/>

Before I port this back to
the NES, I'm looking for
* Anything broken
* Anything confusing
* Anything too hard too
  early
* Presets for more brands
  of controllers

Press Enter
"""

helpScreenText = """
They came back and found
the facility trashed and
crawling with vermin.
Not only that, but without
any staff to protect,
the sneakers were caring
for the vermin.
So they called an
exterminator.

Stun each enemy by tossing
a block at it, then touch
it while stunned to kill it.
Defeat all enemies in the
room or grab all chips
to continue.

Press Jump"""

sfxdata = [
    ('destroyed', 0, 2, bytes([
        0x88,37,0x81,37,0x88,44,0x81,44
    ])),
    ('hurt', 0, 1, bytes([
        0x88,55,0x88,48,0x88,41,0x88,34,
        0x88,55,0x88,48,0x88,41,0x88,34,0x88,27,0x84,20
    ])),
    ('knock', 12, 2, bytes([
        0x08,0x0c,0x08,0x08,0x05,0x0a,0x02,0x0b
    ])),
    ('sneakerdmg', 12, 3, bytes([
        0x08,0x89,0x08,0x8a,0x05,0x8b,0x05,0x8a,0x05,0x85
    ])),
    ('land', 12, 2, bytes([
        0x0c,0x0e,0x08,0x0f
    ])),
    ('makeblock', 0, 1, bytes([
        0x04,0,0x06,1,0x07,3,0x08,4,0x08,6,0x08,7,
        0x08,8,0x08,9,0x08,11,0x08,12,0x06,12,0x04,11,0x02,10
    ])),
    ('throwblock', 0, 1, bytes([
        0x84,48,0x86,50,0x87,52,0x88,53,
        0x88,52,0x87,51,0x86,50,0x85,49,0x84,48,0x83,47,0x82,46,0x81,45
    ])),
    ('jump', 0, 1, bytes([
        0x84,48,0x86,50,0x87,52,
        0x87,54,0x86,56,0x85,58,0x84,59,0x83,60,
    ])),
    ('getchip', 8, 2, bytes([
        0x88,51,0x88,58,0x88,51,0x88,58,0x88,51,0x88,58,
    ])),
    ('opendoor', 12, 1, bytes([
        0x0c,0x0f,0x08,0x0e,0x08,0x0d,0x08,0x0c,
        0x08,0x86,0x08,0x85,0x08,0x84,0x08,0x84,0x08,0x83,0x08,0x83,
        0x08,0x83,0x08,0x84,0x07,0x83,0x06,0x84,0x05,0x83,0x04,0x84,0x02,0x84
    ])),
]

default_bindings = [
    G.K_UP, G.K_DOWN, G.K_LEFT, G.K_RIGHT,
    G.K_x, G.K_z, G.K_TAB, G.K_RETURN
]
joycfg_presets = [
    # Controller names under Linux include the make and model.
    # Windows omits the make, but Logitech has "Logitech" in both
    # the make and model
    ("logitech*precision,gamepad pro usb",  # clones of PS1 digital
     [('axis',0,1,-1),('axis',0,1,1),('axis',0,0,-1),('axis',0,0,1),
      ('button',0,1),('button',0,0),('button',0,8),('button',0,9)]),
    ("logitech dual action",  # clone of PS1 Dual Shock
     [('hat',0,0,1,1),('hat',0,0,1,-1),('hat',0,0,0,-1),('hat',0,0,0,1),
      ('button',0,1),('button',0,0),('button',0,8),('button',0,9)]),
    ("adaptoid",  # N64->USB adapter
     [('button',0,10),('button',0,11),('button',0,12),('button',0,13),
      ('button',0,0),('button',0,3),('button',0,9),('button',0,8)]),
    # X-Box 360 (Linux misspelling) and Xbox 360 (Windows correct
    # spelling) have different layouts for right stick, RT, L3, and
    # R3, but the rest are similar enough for one def to cover both
    ("x-box 360 pad,xbox 360",
     [('axis',0,1,-1),('axis',0,1,1),('axis',0,0,-1),('axis',0,0,1),
      ('button',0,0),('button',0,2),('button',0,6),('button',0,7)]),
    ('generic   usb  joystick',  # "Steel Series" PS2 clone bought at Walmart
     [('axis',0,1,-1),('axis',0,1,1),('axis',0,0,-1),('axis',0,0,1),
      ('button',0,2),('button',0,3),('button',0,8),('button',0,9)]),
    # For controllers with no make and model name, Linux returns HID
    # as the make and vendor:product as the model.  Windows returns
    # something less useful: "# axis # button controller".
    ("1267:2afb",  # white Chinese SNES clone by "X-BOY 2008"
     [('axis',0,1,-1),('axis',0,1,1),('axis',0,0,-1),('axis',0,0,1),
      ('button',0,2),('button',0,0),('button',0,6),('button',0,7)]),
    # The EMS USB2, a PS1->USB adapter, is popular among DDR players
    # precisely because it has so many buttons.  It treats the D-pad
    # as four separate buttons instead of a hat, allowing the
    # left+right and up+down presses that dance pads use for jumps.
    ("0b43:0003,4 axis 16 button",
     [('button',0,12),('button',0,14),('button',0,15),('button',0,13),
      ('button',0,2),('button',0,3),('button',0,8),('button',0,9)]),
]

def joycfg_get_preset():
    try:
        jname = joycfg.joysticks[0].get_name()
    except IndexError:
        print("Defaulting to keyboard!")
        return [('key', b) for b in default_bindings]
    return joycfg.match_name(joycfg_presets, jname)

def format_bindings(bindings):
    try:
        jname = joycfg.joysticks[0].get_name()
    except IndexError:
        buttonlabels = None
    else:
        buttonlabels = joycfg.get_buttonlabels(jname)
    return "\n".join("%-7s%s" % (n+":", joycfg.format_binding(b, buttonlabels))
                     for (n, b) in zip(action_names, bindings))

class FHBGView(object):

    def __init__(self):
        from enlarger import Enlarger
        from ascii import PyGtxt
        from player import TossedBlock

        logisize = (256, 176)
        physsize = tuple(c * (2 if with_double else 1) for c in logisize)
        if with_fullscreen:
            modes = [(x, y) for (x, y) in G.display.list_modes()
                     if x > physsize[0] and y > physsize[1]]
        else:
            modes = []
        fullscreen = modes and G.display.set_mode(min(modes), G.FULLSCREEN)
        fullscreen = fullscreen or G.display.set_mode(physsize)
        screen_w, screen_h = fullscreen.get_size()
        if screen_w > physsize[0] or screen_h > physsize[1]:
            screen = fullscreen.subsurface(((screen_w - physsize[0]) // 2,
                                            (screen_h - physsize[1]) // 2,
                                            physsize[0], physsize[1]))
        else:
            screen = fullscreen
        self.display = Enlarger(screen, logisize if with_double else None, True)

        self.font = PyGtxt(G.image.load('tilesets/ascii.png'), 8, 8)
        sfx = chipsfx.make_sound_effects(sfxdata)
        self.sfx = dict((name, G.mixer.Sound(samples))
                        for (name, samples) in sfx.items())

        self.bggfx = G.image.load('tilesets/bggfx1.png').convert_alpha()
        spritegfx = G.image.load('tilesets/spritegfx.png')
        self.metatile_sheet = loadlevel.makemetatilesheet(self.bggfx, loadlevel.mttable)
        spritegfx.set_colorkey(0)
        spritegfx = spritegfx.convert_alpha()
        TossedBlock.sheet = spritegfx
        self.spritegfx = [spritegfx,
                          G.transform.flip(spritegfx, True, False),
                          G.transform.flip(spritegfx, False, True),
                          G.transform.flip(spritegfx, True, True)]
        self.ffpipe = self.video_outfp = None
        if with_vidcap:
            if with_vidcap == 'pipe':
                import shlex, subprocess
                args = shlex.split(vidcap_pipe_cmd)
                self.ffpipe = subprocess.Popen(args, bufsize=-1,
                                          stdin=subprocess.PIPE)
                self.video_outfp = self.ffpipe.stdin
            else:
                self.video_outfp = open('vtee.raw', 'wb')
                # convert this with
                # avconv -f rawvideo -r 30 -pix_fmt rgb24 -s 256x176 -y -an -i vtee.raw -c:v png vtee.avi
                # or see http://www.iabaldwin.com/2011/02/piping-raw-data-info-ffmpeg/
            self.display.set_videotee(self.video_outfp, 2)
        self.last_vkeys = 0xFF

    def draw(self, game):
        from itertools import chain
        pf = game.pf
        pfdst = self.display.get_surface()
        old_dirty = pf.redrawdirty(pfdst, 0, 0)
        spr_rects = []
        for t in chain(game.enemy_projectiles, game.enemies, game.player_projectiles):
            spr_rects.extend(t.draw(pfdst))
        if game.chip_factory:
            spr_rects.extend(game.chip_factory.draw(pfdst))
        spr_rects.extend(game.player.draw(pfdst))
        pf.setdirtyrects(spr_rects, 0)
##        new_dirty = pf.getdirtyruns()
##        all_dirty = pf.unionoldnewdirty(old_dirty, new_dirty)
##        to_update = pf.dirtyrunstorects(all_dirty)

    def close(self):
        if self.video_outfp:
            G.display.set_caption("Waiting for encode to finish")
            G.display.get_surface().fill((102, 102, 102))
            G.display.flip()
            self.video_outfp.close()
            self.video_outfp = None
            chipsfx.render_logged_fx(sfxdata, self.display.num_frames)
        elif self.display:
            self.display.get_surface().fill((102, 102, 102))
            self.display.flip()
        self.display = self.font = self.sfx = self.spritegfx = None
        if self.ffpipe:
            self.ffpipe.wait()
            self.ffpipe = None

    def __del__(self):
        self.close()

class FHBGGame(object):
    def __init__(self, view, levelmaps=None, levels=None):
        if not levelmaps or not levels:
            levelmaps, levels = loadlevel.load_levels()
        self.levelmaps, self.levels = levelmaps, levels
        self.view = view

    def new_game(self):
        from player import Player
        self.pf = mtplane.MetatilePlane()
        self.player = Player(self, self.view, 1, 9)
        self.cleared_levels = 0
        self.outer_y = 0
        self.outer_x = 0
        self.open_l = False
        self.open_r = False

    def clear_objs(self):
        self.player_projectiles = []
        self.enemies = []
        self.enemy_projectiles = []
        self.spawn_time = 0
        self.enemy_factory = self.chip_factory = self.exitpos = None
        self.player.new_level()

    def load_mapdata(self, mapdata):
        sr = self.pf.setrow
        for y in range(11):
            sr(0, y, mapdata[16 * y:16 * y + 16])

    def new_level(self, level, mapentry=None):
        from enemy import EnemyFactory, ChipFactory
        from itertools import chain, repeat

        self.clear_objs()
        if level:
            self.enemy_factory = EnemyFactory(level, self, self.view)
            self.player.mercy_time = 60
            mapentry = mapentry or self.levelmaps[level[1]]
        mapname, mapstart, mapdata = mapentry
        self.load_mapdata(mapdata)

        # And add the entry/exit door
        if mapstart:
            p_x, p_y = mapstart
            self.exitpos = p_x, p_y
            self.player.pos = [p_x * 16 + 8, p_y * 16 + 15]
            self.pf.setcol(p_x, p_y - 1, (12, 13))
        else:
            p_x, p_y = 8, 9

        # Start chips, but not immediately one headed for the player
        if level and level[4]:
            self.chip_factory = ChipFactory(p_y, self, self.view)

        return p_x, p_y

    def move(self, vkeys, new_vkeys):
        from itertools import chain
        self.player.move(vkeys, new_vkeys)
        want_to_open_door = False

        try:
            next_enemy = next(self.enemy_factory) if self.enemy_factory else None
        except StopIteration:
            self.enemy_factory = None
            want_to_open_door = True
        else:
            if next_enemy:
                self.enemies.append(next_enemy)
        self.player_projectiles = [t for t in self.player_projectiles if t and t.pos]
        self.enemy_projectiles = [t for t in self.enemy_projectiles if t and t.pos]
        for t in chain(self.player_projectiles, self.enemies, self.enemy_projectiles):
            t.move()
        if self.chip_factory and self.chip_factory.move():
            want_to_open_door = True
            self.chip_factory = None

        if want_to_open_door:
            chipsfx.fxq('opendoor')
            spawn_x, spawn_y = self.exitpos
            self.pf.setcol(spawn_x, spawn_y - 1, (14, 15))

def play_level(view, game, level=None, mapentry=None):
    game.new_level(level, mapentry)
    p = game.player
    done = False
    clk = G.time.Clock()
    addlkeys = [
        (G.K_ESCAPE, 0, VK_SELECT|VK_START)
    ]
    while not done:
        event_vkeys, other_events = translate_events(addlkeys)
        (vkeys, new_vkeys) = read_pads(view)
        new_vkeys |= event_vkeys
        vkeys |= event_vkeys
        game.move(vkeys, new_vkeys)
        view.draw(game)
        if p.health < 1:
            done = 'die'
        if (vkeys & VK_LEFT) and game.open_l and p.pos[0] <= 8:
            done = 'side'
        if (vkeys & VK_RIGHT) and game.open_r and p.pos[0] >= 248:
            done = 'side'
        if p.state == p.ST_ENTERING_DOOR and p.walking_frame > 20:
            done = 'door'
        if (vkeys & (VK_SELECT | VK_START) == (VK_SELECT | VK_START)):
            done = 'esc'
        chipsfx.fxq_play(view.sfx, view.display.num_frames)
        clk.tick(60)
        view.display.flip()
    return done

def ilog2(i):
    """Find the most significant 1 bit in an integer, or -1 if not positive."""
    if i <= 0:
        return -1
    out = 0
    while i >= 0x10000:
        i >>= 16
        out += 16
    if i >= 0x100:
        i >>= 8
        out += 8
    if i >= 0x10:
        i >>= 4
        out += 4
    if i >= 0x04:
        i >>= 2
        out += 2
    if i >= 0x02:
        i >>= 1
        out += 1
    return out

def clz(i):
    """Count least-significant zero bits in an integer."""
    return ilog2(i & -i)

def count_ones(i):
    num_ones = 0
    while i > 0:
        i = i & (i - 1)
        num_ones += 1
    return num_ones

assert ilog2(24) == 4
assert ilog2(0) < 0
assert ilog2(1) == 0
assert ilog2(2) == 1

num_floors = 3

def play_game(view, game):
    from fhbgui import preroll, gameover
    game.new_game()
    game.pf.sheet = view.metatile_sheet
    game.player.pos = [2 * 16 + 8, 159]

    while True:
        game.player.pos[1] = (1 - game.outer_y % 2) * 80 + 79
        floors_done = clz(~game.cleared_levels) // 4
        open_elevator = (game.outer_y & 1
                         if game.outer_y + 1 == floors_done
                         else -1)
        if game.outer_x:
            game.open_l = True
        else:
            game.open_r = True
        if floors_done >= num_floors:
            game.open_l = True
        elif floors_done > game.outer_y:
            game.open_r = True
        m = loadlevel.build_outer_room(game.outer_x, game.outer_y // 2,
                                       game.cleared_levels, open_elevator)
        result = play_level(view, game, None, ('', None, m))
        if result == 'q':
            return 'q'
        if result == 'esc':
            gameover(view, count_ones(game.cleared_levels))
            return
        side = 1 if game.player.pos[0] >= 128 else 0
        if result == 'side':
            if game.outer_x == 1 and side == 1:
                game.outer_y = (game.outer_y + 1) % num_floors
                game.player.pos[0] = 232
                continue
            if game.outer_x == 0 and side == 0:
                return 'win'
            game.outer_x = side
            game.player.pos[0] = 8 if side else 248
            continue

        levelnum = game.outer_y * 4 + game.outer_x * 2 + side
        level = game.levels[levelnum]
        vkeys = preroll(view, level)
        game.open_l = game.open_r = False
        result = play_level(view, game, level)
        if result == 'q':
            return 'q'
        if result in ('esc', 'die'):
            gameover(view, count_ones(game.cleared_levels))
            return
        game.cleared_levels |= 1 << levelnum
        new_xpos = (levelnum & 1) * 7 - (game.outer_x & 1) + 5
        game.player.pos[0] = new_xpos * 16 + 8
            
def main():
    from fhbgui import coprscreen, titlescreen, level_select
    from editor import editor

    G.display.set_caption("Loading")
    joycfg.dump_joysticks(verbose=False)
    wndicon = G.image.load('tilesets/wndicon32.png')
    G.display.set_icon(wndicon)
    if with_music:
        G.mixer.music.load('audio/RescueMission.ogg')
    view = FHBGView()
    game = FHBGGame(view)
    view.bindings = joycfg.load_bindings(keybindings_filename)
    G.display.set_caption("Forehead Block Guy")
    quitting = False

    if view.bindings == 'reconfigure':
        got_preset = joycfg_get_preset()
        if got_preset:
            from textwrap import TextWrapper
            tw = TextWrapper(width=28)
            try:
                jname = joycfg.joysticks[0].get_name()
            except IndexError:
                jname = "Keyboard"
            bindingsNotice = '\n'.join([
                "\nRecommended settings for",
                tw.fill(jname),
                format_bindings(got_preset),
                "\nPress Tab to change"
            ])
            view.bindings = got_preset
            e = coprscreen(view, bindingsNotice, with_tab=True)
            if e & VK_SELECT:
                got_preset = None
        view.bindings = (got_preset
                    or joycfg.get_bindings(view.display.get_surface(), view.font,
                                           action_names, flipper=view.display))
        if not view.bindings:
            return
        joycfg.save_bindings(keybindings_filename, view.bindings, action_names)
    elif not isinstance(view.bindings, list):
        view.bindings = [('key', b) for b in default_bindings]

    if todoNotice:
        e = coprscreen(view, todoNotice)
    while not quitting:
        selected = titlescreen(view)
        if selected < 0:
            break
        if selected == 1:
            bindingsNotice = '\n'.join([
                "\nControls:",
                format_bindings(view.bindings),
                "\nTo change the controls,\npress Tab or Select"
            ])
            e = coprscreen(view, bindingsNotice, with_tab=True)
            if e & VK_SELECT:
                newbindings = joycfg.get_bindings(view.display.get_surface(), view.font,
                                                  action_names, flipper=view.display)
                view.bindings = newbindings or view.bindings
                joycfg.save_bindings(keybindings_filename, view.bindings, action_names)
            read_pads(view)  # clear out fire button
            continue
        elif selected == 2:  # practice
            ls_level = 0
            while True:
                e, ls_level = level_select(view, game, ls_level)
                if ls_level < 0:
                    break
                game.new_game()
                game.pf.sheet = view.metatile_sheet
                if with_music:
                    G.mixer.music.set_volume(.7)
                    G.mixer.music.play(-1)
                result = play_level(view, game, game.levels[ls_level])
                G.mixer.music.stop()
                if result == 'q':
                    quitting = True
            continue
        elif selected == 3:  # edit
            editor(view, game, play_level)
            continue
        elif selected == 4:  # help
            e = coprscreen(view, helpScreenText)
            continue
        if with_music:
            G.mixer.music.set_volume(.7)
            G.mixer.music.play(-1)
        result = play_game(view, game)
        G.mixer.music.stop()
        if result == 'q':
            quitting = True

    view.close()

if __name__=='__main__':
    G.mixer.pre_init(mixer_freq, -16, 1, 1024)
    G.init()
    try:
        main()
    finally:
        G.quit()
