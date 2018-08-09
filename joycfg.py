#!/usr/bin/env python3
import pygame as G
from ascii import PyGtxt

# For http://slashdot.org/comments.pl?sid=3205473&cid=41752211

def dump_joysticks(verbose=True):
    global joysticks

##    print("Available fonts:")
##    print("\n".join(G.font.get_fonts()))
    joysticks = [G.joystick.Joystick(i) for i in range(G.joystick.get_count())]
    for (i, j) in enumerate(joysticks):
        j.init()
    if verbose:
        for j in joysticks:
            name = j.get_name().strip()
            n_axes = j.get_numaxes()
            n_buttons = j.get_numbuttons()
            n_hats = j.get_numhats()
            # Don't call them by the racist term "coolie hat".
            # Instead call them D-pads because that's what they are.
            print("%s\n  stick axes: %d; buttons: %d; auxiliary directional pads: %d"
                  % (name, n_axes, n_buttons, n_hats))
    return joysticks

def draw_joystick_state(screen, font, j, y):

    # axis values are from -1.0 to +1.0
    axes = [j.get_axis(i) for i in range(j.get_numaxes())]
    axes = ['-' if a < -.5 else '+' if a > .5 else '.' for a in axes]

    # button values are false or true
    buttons = [j.get_button(i) for i in range(j.get_numbuttons())]
    buttons = ['o' if a else '.' for a in buttons]

    # hats are (x, y) where -1 is left or down and 1 is up or right
    hats = [a for i in range(j.get_numhats()) for a in j.get_hat(i)]
    hats = ['-' if a < 0 else '+' if a > 0 else '.' for a in hats]

    txt = "[%s|%s|%s]" % ("".join(axes), "".join(buttons), "".join(hats))
    font.textout(screen, txt, 8, y)

def get_wrapped_names():
    from textwrap import TextWrapper
    tw = TextWrapper(width=32)
    return [tw.wrap("%d: %s" % (i + 1, j.get_name().strip()))
            for (i, j) in enumerate(joysticks)]

def enum_screen(screen, font, flipper=None):
    names = get_wrapped_names()
    done = False
    flipper = flipper or G.display
    while not done:
        for event in G.event.get():
            if event.type == G.KEYDOWN:
                if event.key == G.K_ESCAPE:  # escape
                    done = True
            if event.type == G.QUIT:
                done = True

        screen.fill((0, 0, 0))
        y = 8
        for j, name in zip(joysticks, names):
            for line in name:
                font.textout(screen, line, 0, y)
                y += 8
            draw_joystick_state(screen, font, j, y)
            y += 8
        if not joysticks:
            font.textout(screen, "No joysticks.", 0, y)
            y += 8
        font.textout(screen, "Press Escape to quit", 0, y + 8)
        flipper.flip()

axis_labels = {
    (0, -1): 'left',
    (0, 1): 'right',
    (1, -1): 'up',
    (1, 1): 'down',
}
hat_labels = {
    (0, -1): 'left',
    (0, 1): 'right',
    (1, 1): 'up',
    (1, -1): 'down',
}
buttonlabels_presets = [
    ('x-box 360 pad',  # Xbox 360 controller under Linux
     ['A', 'B', 'X', 'Y', 'LB', 'RB', 'Back', 'Start', 'Guide', 'L3', 'R3']),
    ('xbox 360',  # Xbox 360 controller under Windows
     ['A', 'B', 'X', 'Y', 'LB', 'RB', 'Back', 'Start', 'L3', 'R3']),
    ('gamepad pro usb',  # Gravis
     ['Red', 'Yellow', 'Green', 'Blue', 'L1', 'R1', 'L2', 'R2', 'Select', 'Start']),
    ('1267:2afb',  # No-name SNES style pad with "X-BOY 2008" on inspection sticker on rear
     ['Y', 'X', 'B', 'A', 'L', 'R', 'Select', 'Start']),
    ('0b43:0003,4 axis 16 button',  # EMS USB2 (ps1 to PC adapter)
     ['Triangle', 'Circle', 'X', 'Square', 'L2', 'R2', 'L1', 'R1',
      'Select', 'Start', 'L3', 'R3', 'D-pad up', 'D-pad right', 'D-pad down', 'D-pad left']),
    ('adaptoid',  # N64 to USB adapter
     ['A', 'C down', 'C right', 'B', 'C left', 'C up', 'L', 'R', 'Start', 'Z',
      'Control Pad up', 'Control Pad down', 'Control Pad left', 'Control Pad right'])
]

def match_name(preset_list, jname):
    jname = jname.strip().lower()
    for (name, bindings) in preset_list:
        for name in name.split(','):
            if all(needle.strip() in jname for needle in name.split('*')):
                return bindings

def get_buttonlabels(jname):
    return match_name(buttonlabels_presets, jname)

def format_binding(binding, buttonlabels=None):
    if binding[0] == 'key':
        return 'key ' + G.key.name(binding[1])
    if binding[0] == 'mousebutton':
        return "mouse button %d" % binding[1]

    buttonlabels = buttonlabels or []
    if binding[0] == 'button':
        jn = joysticks[binding[1]].get_name()
        try:
            button_name = buttonlabels[binding[2]]
        except IndexError:
            button_name = "button %d" % (binding[2] + 1)
        return "#%d %s" % (binding[1] + 1, button_name)
    if binding[0] == 'axis':
        try:
            axis_name = axis_labels[binding[2], binding[3]]
        except KeyError:
            axis_name = "axis %d %s" % (binding[2], '+' if binding[3] > 0 else '-')
        return "#%d %s" % (binding[1] + 1, axis_name)
    if binding[0] == 'hat':
        axis_name = hat_labels[binding[3], binding[4]]
        return "#%d D-pad %d %s" % (binding[1] + 1, binding[2] + 1, axis_name)
    return " ".join(str(s) for s in binding)

def get_bindings(screen, font, descs, confirm_button=-1, flipper=G.display):
    names = get_wrapped_names()
    flipper = flipper or G.display
    out = []
    last_axis_values = {}
    uninteresting_events = frozenset([
        G.MOUSEMOTION, G.KEYUP, G.JOYBUTTONUP, G.MOUSEBUTTONUP,
        G.ACTIVEEVENT
    ])
    bound_names = ['' for row in descs]
    confirmed = False
    clk = G.time.Clock()
    timeout = 1
    while out is not None and not confirmed:
        assigned = None
        for event in G.event.get():
            if event.type == G.KEYDOWN:
                if event.key == G.K_ESCAPE:  # escape
                    out = None
                else:
                    assigned = ('key', event.key)
            elif event.type == G.JOYAXISMOTION:
                joy = event.joy
                axis = event.axis

                # Round axes to left, center, or right during config
                value = int((event.value + 0.5) // 1)
                ja = (joy, axis)
                if value != last_axis_values.get(ja, 0):
                    last_axis_values[ja] = value
                    if value:
                        assigned = ('axis', joy, axis, value)
            elif event.type == G.JOYHATMOTION:
                joy = event.joy
                hat = event.hat
                for i, value in enumerate(event.value):
                    ja = (joy, hat, i)
                    if value != last_axis_values.get(ja, 0):
                        last_axis_values[ja] = value
                        if value:
                            assigned = ('hat', joy, hat, i, value)
            elif event.type == G.JOYBUTTONDOWN:
                assigned = ('button', event.joy, event.button)
            elif event.type == G.MOUSEBUTTONDOWN:
                assigned = ('mousebutton', event.button)
            elif event.type == G.QUIT:
                raise KeyboardInterrupt
            elif event.type not in uninteresting_events:
                print("event type", event.type)

        if timeout > 0:
            pass
        elif assigned:
            if len(out) < len(descs):
                if assigned not in out:
                    bl = (get_buttonlabels(joysticks[assigned[1]].get_name())
                          if assigned[0] not in ('key', 'mousebutton')
                          else None)
                    bound_names[len(out)] = format_binding(assigned, bl)
                    out.append(assigned)
                    timeout = 15
            elif assigned != out[confirm_button]:
                out = None
            else:
                confirmed = True
        elif out is not None and len(out) < len(descs):
            bound_names[len(out)] = 'Press a button'

        screen.fill((0, 0, 0))
        y = 8
        for j, name in zip(joysticks, names):
            for line in name:
                font.textout(screen, line, 0, y)
                y += 8
            draw_joystick_state(screen, font, j, y)
            y += 8
        if not joysticks:
            font.textout(screen, "No joysticks.", 0, y)
            y += 8

        y += 8
        for (action, button) in zip(descs, bound_names):
            font.textout(screen, "%s: %s" % (action, button), 0, y)
            y += 8
        y += 8
        if out is None:
            lines = ['Canceled.']
        elif len(out) >= len(descs):
            lines = ["To confirm, press %s" % descs[confirm_button],
                     "(%s)" % bound_names[confirm_button],
                     "or anything else to cancel"]
        else:
            lines = ['Press Esc to cancel']
        for line in lines:
            font.textout(screen, line, 0, y)
            y += 8

        clk.tick(60)
        if timeout > 0:
            timeout -= 1
        flipper.flip()
    return out

def read_pad(bindings, key=None):
    """Read a single pad (list of bindings).

bindings -- a list of bindings returned from
key -- output of pygame.key.get_pressed()

"""
    vkeys = 0
    mouse_b = None
    for binding in bindings:
        if not binding:
            pressed = 0
        elif binding[0] == 'key':
            key = key or G.key.get_pressed()
            pressed = key[binding[1]]
        elif binding[0] == 'button':
            pressed = joysticks[binding[1]].get_button(binding[2])
        elif binding[0] == 'axis':
            pos = joysticks[binding[1]].get_axis(binding[2])
            pressed = pos < -.5 if binding[3] < 0 else pos > .5
        elif binding[0] == 'hat':
            pos = joysticks[binding[1]].get_hat(binding[2])[binding[3]]
            pressed = pos < -.5 if binding[4] < 0 else pos > .5
        elif binding[0] == 'mousebutton':
            mouse_b = mouse_b or G.mouse.get_pressed()
            pressed = binding[1] < len(mouse_b) and mouse_b[binding[1]]
        else:
            pressed = 0
        vkeys = (vkeys << 1) | (1 if pressed else 0)
    return vkeys

def bindings_to_text(bindings, comments=None):
    from itertools import chain, repeat

    return  [''.join((' '.join(str(el) for el in binding),
                      '  #%s' % comment if comment else ''))
             for binding, comment
             in zip(bindings, chain(comments or [], repeat('')))]

def text_to_bindings(bindings):
    lencheck = {
        'axis': 4, 'key': 2, 'mousebutton': 2, 'button': 3, 'hat': 5
    }
    out = []
    try:
        basestring
    except NameError:
        basestring = str  # 2to3: lol self assignment
    if isinstance(bindings, basestring):
        bindings = bindings.split('\n')
    for line in bindings:
        line = line.split('#', 1)[0].split()
        try:
            expected_len = lencheck[line[0]]
        except KeyError:
            raise KeyError('unexpected binding type %s' % line[0])
        if len(line) != expected_len:
            raise ValueError('expected %d values for %s binding; got %d'
                             % (expected_len - 1, line[0], len(line) - 1))
        out.append((line[0],) + tuple(int(b) for b in line[1:]))
    return out

def load_bindings(filename):
    try:
        with open(filename, 'rU') as infp:
            lines = [line.strip() for line in infp]
    except IOError:
        lines = []
    try:
        splitpoint = lines.index('')
        old_pads = lines[:splitpoint]
    except ValueError:
        splitpoint = -1
        old_pads = []
    cur_pads = [j.get_name().strip() for j in joysticks]
    if old_pads != cur_pads:
        return "reconfigure"
    try:
        bindings = text_to_bindings(_f for _f in lines[splitpoint + 1:] if _f)
    except Exception as e:
        print(e)
        return "corrupt"
    if len(bindings) < 5:
        return "corrupt"
    return bindings

def save_bindings(filename, bindings, comments=None):
    out = [
        "\n".join(j.get_name().strip() for j in joysticks),
        '\n\n',
        "\n".join(bindings_to_text(bindings, comments)),
        '\n'
    ]
    with open(filename, "wt") as outfp:
        outfp.writelines(out)

def main():
    dump_joysticks()
    screen = G.display.set_mode((256, 192))
    font = PyGtxt(G.image.load('tilesets/ascii.png'), 8, 8)
    action_list = ['Up', 'Down', 'Left', 'Right', 'Fire']
    bindings = get_bindings(screen, font, action_list)
    if bindings:
        print("\n".join(bindings_to_text(bindings)))
        newbindings = (bindings[4:] + [None, None, None][:8 - len(bindings)]
                       + bindings[:4])
        print("\n".join(repr(row) for row in newbindings))
    enum_screen(screen, font)

if __name__=='__main__':
    G.init()
    try:
        main()
    finally:
        G.quit()
