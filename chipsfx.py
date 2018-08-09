#!/usr/bin/env python3
import pygame as G
from array import array
from math import sin, pi
from time import sleep

mixer_freq = 44100
# 44100/60 = 735

# Pygame sounds can be loaded with a string (the path to a sound file
# in RIFF WAVE PCM or Ogg Vorbis format) or, as of Pygame 1.8, an
# instance of array.array (must have same frequency, depth, and
# channels as pygame.mixer.pre_init call).  Ubuntu 12.04 LTS includes
# Pygame 1.9.1.
# Sounds cannot be resampled once loaded; this is a limitation of
# SDL_mixer that RSM was an attempt at fixing, but RSM never got
# worked on much after Pino started concentrating on NES.

# the period of one-eighth of a sample, equal tempered (12edo)
notePeriods = [mixer_freq / ((440 << (n // 12))
                             * (2 ** ((n % 12) / 12)))
               for n in range(80)]
noisePeriods = [p * mixer_freq * 11 / 19687500
                for p in [4, 8, 16, 32, 64, 96, 128, 160,
                          202, 254, 380, 508, 762, 1016, 2034, 4068]]
dmcPeriods = [p * mixer_freq * 11 / 19687500
                for p in [428, 380, 340, 320, 286, 254, 226, 214, 
                          190, 160, 142, 128, 106,  84,  72,  54]]

def synth_square_effect(snddata, samples_per_frame):
    phase = 0
    periodcd = 0
    out = array('h')
    snddata = iter(snddata)
    while True:
        try:
            dutyvol = next(snddata)
            period = notePeriods[next(snddata)]
        except StopIteration:
            break
        duty = [1,2,4,6][(dutyvol >> 6) & 0x03]
        vol = 1000 * (dutyvol & 0x0F)
        for s in range(samples_per_frame):
            level = vol if phase < duty else 0
            if periodcd < 1:
                # simulated box filtering
                phase = (phase + 1) % 8
                level2 = vol if phase < duty else 0
                level = level2 + int(max(0, periodcd) * (level - level2))
                periodcd += period
            periodcd -= 1
            out.append(level)
    return out

def synth_triangle_effect(snddata, samples_per_frame):
    phase = 0
    periodcd = 0
    out = array('h')
    snddata = iter(snddata)
    # triangle is balanced polarity
    samples = [1000*x for x in range(1, 17, 2)]
    samples.extend(reversed(samples))
    samples.extend([-i for i in samples])
    while True:
        try:
            dutyvol = next(snddata)
            period = notePeriods[next(snddata)] / 2
        except StopIteration:
            break
        for s in range(samples_per_frame):
            level = samples[phase]
            if periodcd < 1:
                # simulated box filtering
                phase = (phase + 1) % 32
                level2 = samples[phase]
                level = level2 + int(max(0, periodcd) * (level - level2))
                periodcd += period
            periodcd -= 1
            out.append(level)

    # anti-pop
    level = samples[phase]
    out.extend(i * level // samples_per_frame
               for i in range(samples_per_frame, 0, -1))
    return out

def synth_noise_effect(snddata, samples_per_frame):
    shiftreg = 0x4321
    periodcd = 0
    out = array('h')
    snddata = iter(snddata)
    lastlevel = 0
    while True:
        try:
            # because square sfx are positive polarity, make noise
            # sfx negative
            vol = -1000 * (next(snddata) & 0x0F)
            dutyperiod = next(snddata)
        except StopIteration:
            break
        period = noisePeriods[dutyperiod & 0x0F]
        othertap = 6 if dutyperiod & 0x80 else 1
        for s in range(samples_per_frame):
            if periodcd < 1:
                newbit = ((shiftreg >> othertap) ^ shiftreg) & 0x01
                shiftreg = (shiftreg >> 1) | (newbit << 14)
                level2 = vol if newbit else 0
                level = level2 + int(max(0, periodcd) * (lastlevel - level2))
                lastlevel = level2
                periodcd += period
            else:
                level = lastlevel
            periodcd -= 1
            out.append(level)
    return out

def synth_ding(f):
    f_trig = f * 2 * pi / mixer_freq
    length = mixer_freq // 2
    return array('h', (int(round((15000 * sin(t * f_trig)
                            + 5000 * sin(t * f_trig)
                            + 3000 * sin(t * f_trig))
                           * (length - t) / length))
                 for t in range(length)))

def make_sound_effects(sfxdata):
    baselen = mixer_freq // 60
    sfx = {}
    for (name, ch, framelen, data) in sfxdata:
        synth = (synth_noise_effect
                 if ch >= 12
                 else synth_triangle_effect
                 if ch >= 8
                 else synth_square_effect)
        sfx[name] = synth(data, framelen*baselen)
    return sfx

queued_fx = []
logged_fx = []

def fxq(sndname):
    queued_fx.append(sndname)

def fxq_play(sfx, logtime):
    if not queued_fx:
        return
    logged_fx.append((logtime, list(queued_fx)))
    for sndname in queued_fx:
        sfx[sndname].play()
    queued_fx[:] = []

def mixer_add2(dst, src, t):
    d = array(b'h', (min(32765, max(-32765, a + b))
                     for a, b in zip(src, dst[t:t + len(src)])))
    dst[t:t + len(d)] = d

def render_logged_fx(sfxdata, num_frames):
    import sys

    # Don't play identical FX on the same frame.
    next_t_per_fx = {}
    fxdeduped = []
    for t, fxlist in sorted(logged_fx):
        for fxname in fxlist:
            new_t = max(t, next_t_per_fx.get(fxname, 0))
            fxdeduped.append((new_t, fxname))
            next_t_per_fx[fxname] = new_t + 1
    new_t = fxlist = next_t_per_fx = None
    
    sys.stdout.write("Rendering %d sound effects" % len(fxdeduped))
    sfx = make_sound_effects(sfxdata)
    baselen = mixer_freq // 60
    a = array(b'h', [0]) * (num_frames * baselen)
    for t, fxname in fxdeduped:
        sys.stdout.write('.')
        mixer_add2(a, sfx.get(fxname, []), t * baselen)
    sfx = fxdeduped = None

    little = ord(array(b'h', [1]).tostring()[0])
    if not little:
        a.byteswap()

    import wave
    from contextlib import closing
    with closing(wave.open('atee.wav', 'w')) as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(mixer_freq)
        f.writeframes(a.tostring())
    sys.stdout.write(" done.\n")

splitsnd = array('B', [
    0x4f,36,0x44,36,0x4f,41,0x44,41,0x4f,46,0x44,46,0x44,36,0x42,36,
    0x44,41,0x42,41,0x44,46,0x42,46,0x42,36,0x41,36,0x42,41,0x41,41,
    0x42,46,0x41,46,
])
snaresnd = array('B', [
    0x0a,0x05,0x08,0x84,0x06,0x04,0x04,0x84,0x03,0x04,0x02,0x04,0x01,0x04,
])
kicksnd = array('B', [
    0x08,0x04,0x08,0x0e,0x04,0x0e,0x05,0x0e,0x04,0x0e,0x03,0x0e,0x02,0x0e,
    0x01,0x0e,
])
threat1snd = array('B', [
    0x46,31,0x4c,31,0x4c,31,0x4c,37,0x4c,37,0x4c,43,0x4c,43,0x4c,49,
    0x4c,49,0x4c,49,0x4c,49,0x4c,49,0x4c,49,0x4c,49,0x4c,49,0x4c,49,
    0x4b,49,0x4a,49,0x49,49,0x47,49,0x45,49,
])
threat2snd = array('B', [
    0x4c,28,0x4c,34,0x4c,40,0x4c,46,0x4c,46,0x4c,46,0x4c,46,0x4b,46,
    0x49,46,0x46,46,
])

launchsnd = array('B', [
    0x8c,61,0x4c,30,
    0x89,29,0x86,29,0x84,29,0x83,29,0x82,29,0x81,29
])
anchorsnd = array('B', [
    0x0c,0x0c,0x0c,0x09,0x09,0x0a,0x06,0x0b,0x02,0x0b
])
landsnd = array('B', [
    0x0c,0x0e,0x08,0x0f
])


def repr_sfx(s, noise=False):
    lines = ["array('B', ["]
    fmt = "0x%02x,0x%02x," if noise else "0x%02x,%2d,"
    width = 7 if noise else 8
    s = iter(s)
    row = []
    while True:
        try:
            b1 = next(s)
            b2 = next(s)
        except StopIteration:
            break
        row.append(fmt % (b1, b2))
        if len(row) >= width:
            lines.append("    "+"".join(row))
            row = []
    if row:
        lines.append("    "+"".join(row))
    lines.append("]")
    return "\n".join(lines)

def main():
##    cy = synth_ding(392)
    s1 = G.mixer.Sound(synth_triangle_effect(launchsnd, mixer_freq // 60))
    s2 = G.mixer.Sound(synth_noise_effect(anchorsnd, mixer_freq // 60))
##    s = G.mixer.Sound(synth_noise_effect(landsnd, mixer_freq // 60 * 2))
    s1.play()
    sleep(0.33)
    s2.play()
    sleep(0.33)

if __name__=='__main__':
    G.mixer.pre_init(mixer_freq, -16, 1, 2048)
    G.init()
    try:
        main()
    finally:
        G.quit()
