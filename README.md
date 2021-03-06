PyFHBG
======

_Forehead Block Guy_ (_FHBG_) by Joshua Hoffman (@NovaSquirrel on
GitHub, @BushytailSkwirl on Twitter) is an arcade-style platform game
for NES where you throw blocks at enemies to stun them and then touch
them to defeat them.  It is the direct predecessor of two of
NovaSquirrel's later games:

* [_Double Action Blaster Guys_][1] (_DABG_), an elaboration
* [_FHBG_ for Game Boy Color][2], an enhanced remake

_PyFHBG_ is an attempt to take _FHBG_ in a slightly more serious
direction.

Premise
-------
They came back and found the facility trashed and crawling with
vermin.  Not only that, but without any staff to protect, the
sneakers were caring for the vermin.  So they called an exterminator.

Stun each enemy by tossing a block at it, then touch it while
stunned to kill it.  Defeat all enemies in the room or grab all
chips to continue.

Prerequisites
-------------
Install Python 3 and Pygame for Python 3.  Under Debian or Ubuntu,
try this:

    sudo apt install python3-pygame
    python3 fhbg.py

Why SDL 1.2?
------------
Pygame uses SDL 1.2.  When exporting a replay as a video, the game
uses `pygame.image.tostring()` to capture the video to an RGB byte
string and then feed it to FFmpeg.  (See `enlarger.py`.)  I know of
two SDL 2-based replacements for Pygame, neither of which has any
counterpart to `pygame.image.tostring()`

[PySDL2 docs][3] state:

> tostring(): No equivalent yet

The README for the Ren'Py project's [pygame_sdl2][4] states:

> Current omissions include:  
> APIs that expose pygame data as buffers or arrays.

License choice is pending.


[1]: https://github.com/NovaSquirrel/DABG
[2]: https://github.com/NovaSquirrel/GameBoyFHBG
[3]: https://pysdl2.readthedocs.io/en/rel_0_9_6/tutorial/pygamers.html#pygame-image
[4]: https://github.com/renpy/pygame_sdl2
