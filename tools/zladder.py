#!/usr/bin/env python3
"""Draw a ladder of short extruded lines at descending Z heights.

Finding z_offset by paper feel misled this machine twice - ooze on the tip
drags the paper early by about the size of the thing being measured. An
actual extrusion is the honest instrument: the line that looks like a proper
first layer tells you the correction directly.

Each line is drawn at a commanded Z. If a line at Z = -0.30 looks right, then
the nozzle is 0.30 mm higher than Klipper thinks, so:

    new z_offset = current z_offset + 0.30

Usage: zladder.py [start_z] [step] [count]
Default: 0.00 down to -0.60 in 0.10 steps, 7 lines, 6 mm apart in Y.
"""
import os, select, sys, time, math

START = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.10
COUNT = int(sys.argv[3]) if len(sys.argv) > 3 else 7
Y_START = float(sys.argv[4]) if len(sys.argv) > 4 else 100.0
# Y_START moved 80 -> 100 so the ladder never lands on the prime,
# which runs along Y80.

# NOTE ON SIGN, because it has been got wrong both ways on this machine:
#   lines DIG IN / mark the plate  -> nozzle is CLOSER than Klipper thinks
#                                  -> z_offset is TOO LARGE, REDUCE it
#   lines sit as round beads       -> nozzle is HIGHER than Klipper thinks
#                                  -> z_offset is TOO SMALL, INCREASE it
# And wipe the nozzle first. Filament stuck to the tip makes extrusion curl,
# which looks exactly like "too high" and sent this diagnosis the wrong way.

LAYER_H, LINE_W, FIL_D = 0.2, 0.4, 1.75
E_PER_MM = (LAYER_H * LINE_W) / (math.pi * (FIL_D / 2) ** 2)

X0, X1 = 80.0, 130.0
Y0, Y_STEP = Y_START, 6.0
LEN = X1 - X0
E_LINE = LEN * E_PER_MM

fd = os.open('/tmp/printer', os.O_RDWR | os.O_NOCTTY)


def drain(sec):
    buf = b''
    end = time.time() + sec
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            buf += os.read(fd, 8192)
    return buf.decode('utf-8', 'replace')


def send(cmd, wait=0.8):
    os.write(fd, (cmd + '\n').encode())
    out = drain(wait)
    if '!!' in out:
        print('  ERROR:', out.strip()[:200], flush=True)
    return out


drain(0.4)
send('G90')
send('M83')
send('G1 Z10 F600', 1.5)

# PRIME, L-SHAPED. There was NO prime here before, so line 1 was drawn by a
# nozzle that was not yet flowing - which reads as "too high" and is exactly
# the kind of false signal this script exists to avoid.
# The second leg turns 90 degrees instead of running back 0.4 mm alongside
# the first: two parallel passes that close together merge and clump, badly
# so in PETG. Y80/X40->X180 is the known-good strip clear of the COMGROW
# logo; the L then runs UP X180, well clear of the ladder at X80-130.
PRIME_Y = 80.0
PRIME_X0, PRIME_X1 = 40.0, 180.0
PRIME_LEG2 = 90.0
send(f'G1 X{PRIME_X0:.1f} Y{PRIME_Y:.1f} F3000', 1.5)
send(f'G1 Z{LAYER_H:.3f} F300', 1.0)
send(f'G1 X{PRIME_X1:.1f} Y{PRIME_Y:.1f} '
     f'E{(PRIME_X1 - PRIME_X0) * E_PER_MM:.4f} F1200', 10.0)
send(f'G1 X{PRIME_X1:.1f} Y{PRIME_Y + PRIME_LEG2:.1f} '
     f'E{PRIME_LEG2 * E_PER_MM:.4f} F1200', 8.0)
send('G10', 1.0)          # retract before lifting off the prime
send('G1 Z5 F600', 1.0)

print(f'E per mm = {E_PER_MM:.5f}, {E_LINE:.3f} mm per {LEN:.0f} mm line\n', flush=True)
for i in range(COUNT):
    z = START - i * STEP
    y = Y0 + i * Y_STEP
    print(f'  line {i+1}: Y={y:.0f}  Z={z:+.3f}', flush=True)
    send(f'G1 X{X0:.1f} Y{y:.1f} F3000', 1.0)
    send(f'G1 Z{z:.3f} F300', 1.0)
    # UNRETRACT only once we are in position, and RETRACT before every lift.
    # Without this the bowden's 5 mm of standing pressure blobs at the end of
    # each line and strings across to the next one, which is exactly what it
    # did. G10/G11 must stay PAIRED - a G11 with nothing retracted is a
    # silent no-op, the same trap that cost 200 layers in gen_tower.py.
    send('G11', 1.0)
    send(f'G1 X{X1:.1f} Y{y:.1f} E{E_LINE:.4f} F300', 12.0)
    send('G10', 1.0)
    send('G1 Z5 F600', 1.0)

send('G1 Z20 F600', 1.5)
send('G1 X10 Y200 F3000', 2.0)
print('\nladder done - lowest Y is the highest Z', flush=True)
print('Line 1 is nearest you if Y increases away from you.', flush=True)
