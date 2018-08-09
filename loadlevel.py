#!/usr/bin/env python3
import pygame as G
import innie

MT_LADDER = 8
MT_DOOR = 12
MT_DOOR_UNFINISHED_BOTTOM = 9
MT_OPEN_DOOR = 14
MT_ELEVATOR_SIGNAL = 43
MT_ELEVATOR_DOOR = 44

# 0-7: background patterns
# 8: ladder
# 12, 13: closed door
# 14, 15: open door
# 16: block (+1: top connect, +2: right connect,
#     +4: bottom connect, +8: left connect)
mttable = bytes([
  1, 1, 1, 1,  1, 2, 2, 1,  2, 2, 2, 2,  3, 3, 3, 3,  
  5, 5, 5, 5,  6, 6, 6, 6,  6, 7, 7, 6,  7, 7, 7, 7,
 0xD6,0xD7,0xD6,0xD7, 0xF3,0xE4,0xF8,0xF9,  0, 0, 0, 0,  0, 0, 0, 0,
 0xD3,0xD4,0xE3,0xE4, 0xF3,0xE4,0xE3,0xE4, 0x08,0xD5,0x08,0xE5, 0x08,0xF5,0x08,0xE5,

 0xD0,0xD2,0xF0,0xF2, 0xE0,0xE2,0xF0,0xF2, 0xD0,0xD1,0xF0,0xF1, 0xE0,0xE1,0xF0,0xF1,
 0xD0,0xD2,0xE0,0xE2, 0xE0,0xE2,0xE0,0xE2, 0xD0,0xD1,0xE0,0xE1, 0xE0,0xE1,0xE0,0xE1,
 0xD1,0xD2,0xF1,0xF2, 0xE1,0xE2,0xF1,0xF2, 0xD1,0xD1,0xF1,0xF1, 0xE1,0xE1,0xF1,0xF1,
 0xD1,0xD2,0xE1,0xE2, 0xE1,0xE2,0xE1,0xE2, 0xD1,0xD1,0xE1,0xE1, 0xE1,0xE1,0xE1,0xE1,

 0x03,0x02,0x02,0x01, 0xE6,0xE7,0x01,0x00, 0xE7,0xF6,0x00,0x01, 0x02,0x03,0x01,0x02,
 0x02,0x01,0x02,0x02, 0x01,0x02,0x02,0x02, 0x03,0x02,0x03,0x03, 0x02,0x03,0x03,0x03,
 0x03,0x03,0x04,0x04, 0x05,0x04,0x06,0x05, 0x07,0x06,0x07,0x07, 0x01,0x02,0x02,0xF7,
 0xF4,0x04,0xF4,0x04, 0x07,0x06,0x07,0x07, 0x05,0x04,0x06,0x05, 0x04,0x04,0x04,0x04
])

mtmap_fluoro = bytes([6, 4,
 0x03,0x20,0x21,0x22,0x23,0x03,
 0x03,0x24,0x00,0x00,0x25,0x03,
 0x03,0x26,0x02,0x02,0x27,0x03,
 0x28,0x28,0x03,0x03,0x28,0x28
])
mtmap_elevator = bytes([1, 4,
 0x10,0x10,0x2C,0x2C
])
mtmap_backshadow = bytearray()

def add_mtmap(level, area, x, y):
    w, h = area[:2]
    pitch = w
    i = 2
    skip = 0
    if x < 0:
        skip -= x
        i -= x
        w += x
    if w > 16 - x:
        skip += w + x - 16
        w = 16 - x
    if w <= 0:
        return
    di = y * 16 + x
    while h > 0:
        for lx in range(w):
            level[di] = level[di] or area[i]
            di += 1
            i += 1
        i += skip
        di += 16 - w
        h -= 1

def makemetatilesheet(chrrom_bmp, mttable):
    tilestall = -(-len(mttable) // 64)
    out = G.Surface((256, tilestall * 16))
    mttable = iter(mttable)
    outy = 0
    try:
        for outy in range(0, tilestall * 16, 16):
            for outx in range(0, 256, 16):
                for dsty in (outy, outy + 8):
                    for dstx in (outx, outx + 8):
                        tileno = next(mttable)
                        srcarea = (8 * (tileno % 16), 8 * (tileno // 16), 8, 8)
                        out.blit(chrrom_bmp, (dstx, dsty), srcarea)
    except StopIteration:
        pass
    return out

def connect_level(level):
    from random import choice, shuffle

    # Break existing connections
    for y in range(0, len(level), 16):
        for x in range(y, y + 15):
            b = level[x]
            if 16 <= b < 32:
                b = 16
            level[x] = b

    # Connect blocks across
    for y in range(0, len(level), 16):
        for x in range(y, y + 15):
            if 16 <= level[x] < 32 and 16 <= level[x + 1] < 32:
                level[x] |= 2
                level[x + 1] |= 8

    # Connect blocks down
    for x in range(len(level) - 16):
        if 16 <= level[x] < 32 and 16 <= level[x + 16] < 32:
            level[x] |= 4
            level[x + 16] |= 1

def randomize_level_bg(level):
    from random import choice

    for y in range(0, len(level), 16):
        for x in range(y, y + 15):
            if level[x] < 8:
                level[x] = 0

    # Break up background monotony
    rowwts = iter([0, 0, 1, 2, 3, 3])
    for y1 in range(0, len(level), 32):
        rowwt = next(rowwts)
        colchoice = [(rowwt + choice((0, 2)), choice((0, 1)), choice((0, 1)))
                     for x in range(8)]
        row0 = [[basewt + (ysub ^ yflip) + (xsub ^ xflip)
                 for (basewt, xflip, yflip) in colchoice
                 for xsub in (0, 1)]
                for ysub in (0, 1)]
        whichcol = [choice((0, 1)) for x in range(8)]
        for x in range(16):
            xy = x + y1
            level[xy] = level[xy] or row0[0][x]
        if y1 + 32 <= len(level):
            for x in range(16):
                xy = x + y1 + 16
                if level[xy] < 8:
                    level[xy] = row0[1][x]

class LevelsParser(innie.InnieParser):
    mtnums = {ord('#'): MT_LADDER, ord(' '): 0}

    def __init__(self, data=None, filenames=None):
        innie.InnieParser.__init__(self)
        self.maps = []
        self.maps_by_name = {}
        self.levels = []
        self.addfilter(self.do_map)
        if data:
            self.readstring(data)
        if filenames:
            ok = self.read(filenames)

    def do_map(self, k, v):
        from array import array

        if k == 'map':
            v = v.strip()
            self.maps_by_name[v.lower()] = len(self.maps)
            self.maps.append([v, None, None])
            # name, starting position, block map
            # (default position: lowest unfilled row on column 1)
        elif k == 'start':
            self.maps[-1][1] = tuple(int(i.strip()) for i in v.split(','))
        elif k == 'bg':
            level = [b'%-16s' % line.rstrip().encode("ascii")[:16]
                     for line in v.split('\n')][:11]
            g = self.mtnums.get
            level = bytearray(g(c, 16) for c in b''.join(level))
            connect_level(level)
            randomize_level_bg(level)
            self.maps[-1][2] = level
        elif k == 'level':
            self.levels.append([v, None, 1, [], 0])
            # name, map id, limit, enemies, floating_items
        elif k == 'usemap':
            self.levels[-1][1] = self.maps_by_name[v.strip().lower()]
        elif k == 'limit':
            self.levels[-1][2] = max(int(v), 1)
        elif k == 'tokens':
            self.levels[-1][4] = max(int(v), 1)
        elif k == 'enemy':
            for v in v.split(','):
                v = v.rsplit('*', 1)
                n = int(v[1]) if len(v) > 1 else 1
                self.levels[-1][3].extend([v[0]] * n)
        else:
            return (k, v)

def load_levels(filenames=None):
    parser = LevelsParser(filenames=filenames or ['levels.ini'])
    return (parser.maps, parser.levels)

def save_levels(filename, maps, levels):
    rows = []
    
    for (name, starting_position, mapdata) in maps:
        rows.extend(('map=%s' % name,
                     'start=%d,%d' % starting_position,
                     'bg:'))
        mapdata = ''.join((
            '%' if c >= 16 else '#' if c == MT_LADDER else ' '
            for c in mapdata
        ))
        rows.extend(mapdata[i:i + 16] for i in range(0, len(mapdata), 16))
        rows.extend(('.', ''))
    for (name, mapid, limit, enemies, floating_items) in levels:
        rows.extend(('level=%s' % name,
                     'usemap=%s' % maps[mapid][0],
                     'limit=%d' % limit,
                     'enemy=%s' % ','.join(enemies)))
        if floating_items:
            rows.append('tokens=%d' % floating_items)
        rows.append('')
    with open(filename, 'wt') as outfp:
        outfp.write('\n'.join(rows))

def build_outer_room(x, y, cleared_bits, open_elevator=-1):
    if y > 0:
        cleared_bits >>= 8
    if x > 0:
        cleared_bits >>= 2
    
    lv = bytearray(176)
    for i in range(16):
        lv[i] = lv[i + 80] = lv[i + 160] = 16
    if x > 0:
        add_mtmap(lv, mtmap_elevator, 15, 1)
        lv[46] = MT_ELEVATOR_SIGNAL
    else:
        for base in range(16, 80, 16):
            lv[base] = lv[base + 1] = 16
    for tx in range(0 if x > 0 else 1, 15, 5):
        add_mtmap(lv, mtmap_fluoro, tx, 1)
    doorbase = 4 if x > 0 else 5
    for tx in range(doorbase, 15, 7):
        lv[48 + tx] = MT_DOOR
        lv[64 + tx] = MT_DOOR + 1

    # replicate floors
    lv[96:160] = lv[16:80]

    # shadow only bottomleft
    if x == 0 and y == 0:
        lv[144] = 45
        lv[145] = lv[128] = 46
        lv[129] = 47
    # doors
    if not (cleared_bits & 0x10):
        lv[64 + doorbase] = MT_DOOR_UNFINISHED_BOTTOM
    if not (cleared_bits & 0x20):
        lv[71 + doorbase] = MT_DOOR_UNFINISHED_BOTTOM
    if not (cleared_bits & 0x01):
        lv[144 + doorbase] = MT_DOOR_UNFINISHED_BOTTOM
    if not (cleared_bits & 0x02):
        lv[151 + doorbase] = MT_DOOR_UNFINISHED_BOTTOM
    if open_elevator == 0:
        lv[159] = lv[143] = 4
    elif open_elevator == 1:
        lv[79] = lv[63] = 4

    connect_level(lv)
    return lv

if __name__=='__main__':
##    load_levels()
    for y in (0, 1):
        for x in (0, 1):
            build_outer_room(x, y, 0x0000)
