#!/usr/bin/env python3
from __future__ import with_statement, division, print_function, unicode_literals
import pygame as G

# virtual keys used by movement
VK_A = 0x80
VK_B = 0x40
VK_SELECT = 0x20
VK_START = 0x10
VK_UP = 0x08
VK_DOWN = 0x04
VK_LEFT = 0x02
VK_RIGHT = 0x01

def read_pads(view):
    import joycfg

    # Most of the engine handles vkeys in NES order
    # which is nibble swapped from how the player configures them
    newbindings = view.bindings[4:8] + view.bindings[0:4]
    vkeys = joycfg.read_pad(newbindings)
    new_vkeys = vkeys & ~view.last_vkeys
    view.last_vkeys = vkeys
    return (vkeys, new_vkeys)

def translate_events(addlkeys=[]):
    """Translate SDL events to vkeys.

"""
    event_vkeys = 0
    other_events = []
    for event in G.event.get():
        event_handled = False
        if event.type == G.QUIT:
            raise KeyboardInterrupt
        if event.type == G.KEYDOWN:
            if (event.key == G.K_p and (event.mod & G.KMOD_CTRL)):
                G.image.save(pfdst, "fhbg_snap.png")
                event_handled = True
                continue
            if ((event.key == G.K_F4 and (event.mod & G.KMOD_ALT))
                or (event.key == G.K_q and (event.mod & G.KMOD_CTRL))):
                raise KeyboardInterrupt
            for key, kmod, vkey in addlkeys:
                if key == event.key and (kmod & event.mod) == kmod:
                    event_handled = True
                    event_vkeys |= vkey
                    break
        if not event_handled:
            other_events = []
    return event_vkeys, other_events
