#!/usr/bin/env python3
import pygame as G

class MetatilePlane(object):
    """

The order of operations:
1. Change tiles per game rules with setcell().
2. Get dirty runs, which at this point will consist of all tiles that
   were changed plus all tiles that were covered by a sprite.
3. Update all dirty tiles.
4. Draw sprites to the surface and use setdirtyrect() to mark where
   they were drawn.
5. Get dirty runs again, which will consist of all tiles currently
   covered by a sprite.
6. Union the two sets of dirty runs.
7. Convert this union to pixel coordinates.
8. pygame.display.update() these coordinates.

"""
    def __init__(self, height=12, tw=16, th=16):
        # Store cells as two 16x12 blocks because it's shared with NES
        self.cells = [[[0] * 16 for y in range(height)] for pg in (0, 1)]
        self.sheet = None
        self.cleardirty(True)
        self.win_x = 0
        self.tw = tw
        self.th = th
        

    def cleardirty(self, val):
        """Set dirty values of all tiles to True or False."""
        val = bool(val)
        # Store dirty as 32x12 because only Python needs it
        self.dirty = [[val] * 32 for i in range(len(self.cells[0]))]

    def getcell(self, x, y):
        x = x % 32
        tbl = self.cells[1 if x >= 16 else 0]
        return tbl[y][x % 16]

    def setcell(self, x, y, value):
        x = x % 32
        tbl = self.cells[1 if x >= 16 else 0]
        tbl[y][x % 16] = value
        self.dirty[y][x] = True

    def getrow(self, xmin, xmax, y):
        return [self.getcell(x, y) for x in range(xmin, xmax)]

    def setrow(self, x, y, it):
        for el in it:
            self.setcell(x, y, el)
            x += 1

    def setcol(self, x, y, it):
        for el in it:
            self.setcell(x, y, el)
            y += 1

    def setdirtyrect(self, x, y, w, h):
        """Set a rectangle of PIXELS dirty.

Useful for scheduling a sprite to be erased in a dirty-rect environment.

"""
        
                      
        w += x % self.tw      # include entire tile that X is in
        w = -(-w // self.tw)  # round width up
        x = (x // self.tw) % 32
        if w >= 32:
            x, w = 0, 32
        h += y % self.th      # include entire tile that Y is in
        h = -(-h // self.th)  # round height up
        y = y // self.th
        if y < 0:
            h -= y
            y = 0
        if h > len(self.dirty) - y:
            h = len(self.dirty) - y
        leftw = max(0, x + w - 32)
        w -= leftw
        for row in self.dirty[y:y + h]:
            if leftw:
                row[:leftw] = [True] * leftw
            row[x:x + w] = [True] * w

    def setdirtyrects(self, rects, xscroll=0, yscroll=0):
        sdr = self.setdirtyrect
        for (x, y, w, h) in rects:
            sdr(x + xscroll, y + yscroll, w, h)

    def redrawdirty(self, dst, xscroll=0, yscroll=0):
        tw, th = self.tw, self.th
        nperrow = self.sheet.get_width() // tw
        for (yt, row) in enumerate(self.dirty):
            row_dsty = yt * th - yscroll
            for (xt, d) in enumerate(row):
                if not d:
                    continue
                tileno = self.cells[1 if xt >= 16 else 0][yt][xt % 16]
                srcarea = G.rect.Rect(tileno % nperrow * tw,
                                      tileno // nperrow * th,
                                      tw, th)
                dstpos = (((xt + 1) * tw - xscroll) % (32 * tw) - tw, row_dsty)
                dst.blit(self.sheet, dstpos, srcarea)

        dirtied = self.getdirtyruns()
        self.cleardirty(False)
        return dirtied

    @staticmethod
    def boolstoruns(row):
        """Convert an iterable of booleans to an iterator of (start, length) tuples."""
        # TO DO: test
        runstart = None
        for (x, pred) in enumerate(row):
            if pred:
                if runstart is None:
                    runstart = x
            else:
                if runstart is not None:
                    yield (runstart, x - runstart)
                    runstart = None
        if runstart is not None:
            yield (runstart, x + 1 - runstart)

    def getdirtyruns(self):
        """Get runs of dirty tiles for each row.

Return a list of lists of (start, length) tuples.

"""
        # TO DO: test
        return [list(self.boolstoruns(row)) for row in self.dirty]

    @staticmethod
    def unionruns(*seqs):
        """Compute the union of a sequence of iterables of intervals.

The intervals are in (start, length) format.
Good for combining the last frame's sprite-covered dirty tiles
(things to erase) with this frame's changed and sprite-covered tiles
(things to draw).

"""
        allpairs = sorted(pair for seq in seqs for pair in seq)
        if len(allpairs) == 0:
            return
        lastPairStart = allpairs[0][0]
        lastPairLen = 0
        for (s, l) in allpairs:
            if l <= 0:
                continue
            if lastPairStart + lastPairLen >= s:
                # extend existing run
                if lastPairStart + lastPairLen < s + l:
                    lastPairLen = s + l - lastPairStart
            else:
                if lastPairLen > 0:
                    yield (lastPairStart, lastPairLen)
                lastPairStart, lastPairLen = s, l
        if lastPairLen > 0:
            yield (lastPairStart, lastPairLen)

    def dirtyrunstorects(self, runs):
        R = G.rect.Rect
        tw, th = self.tw, self.th
        return [R(x*tw, y*th, w*tw, th)
                for (y, row) in enumerate(runs)
                for (x, w) in row]

    @staticmethod
    def unionoldnewdirty(old, new):
        ur = MetatilePlane.unionruns
        return [list(ur(a, b)) for (a, b) in zip(old, new)]
    
