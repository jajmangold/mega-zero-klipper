#!/usr/bin/env python3
"""Generate a hollow square tower - a multi-layer speed/quality test.

Unlike the single-layer square this exercises layer adhesion, Z consistency,
corner quality and ringing. Short enough to print in a few minutes.

Usage: gen_tower.py [speed_mm_s] [hotend] [bed] [z_gcode_offset] [height] [pa_factor]
  PLA  : gen_tower.py 60 210 60 0
  PETG : gen_tower.py 60 235 75 0.03 40

PRESSURE ADVANCE: pass a non-zero 6th arg to turn the print into a PA test. It
emits a TUNING_TOWER that ramps pressure_advance with Z, so the whole tower is
one sweep:
    gen_tower.py 60 235 75 0.03 40 0.020      -> PA 0 at Z0 up to 0.80 at Z40
Then read the Z height where the corners look best and
    pressure_advance = height_mm * factor
A bowden extruder like this one usually lands in 0.4-1.0, i.e. 20-50 mm up.
Measure with calipers from the BED, not by counting layers.

There is NO `TUNING_TOWER RESET` command - checked against
klippy/extras/tuning_tower.py on this machine. The test mode is a move
transform that uninstalls itself when it next sees an extrusion move more than
2 mm BELOW the last one, i.e. at the start of the following print. So it cannot
leak into a real print, but it does stay installed until then; `RESTART` clears
it immediately if that matters. The ramp is emitted right AFTER the prime line
so the prime is not part of the sweep.

NOTE ON SPEED: with max_accel 500 the head cannot reach much over 110 mm/s on a
25 mm wall before it must decelerate, so nominal speeds above that are wasted.
Acceleration is the real limiter here, not velocity. Change it at runtime with
    SET_VELOCITY_LIMIT ACCEL=<n>
rather than editing the config. There is no input shaper configured, so
expect ringing (echoes after corners) to appear as accel goes up - that is the
trade-off this test is meant to show.
"""
import math, sys

SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0     # mm/s
HOT = int(sys.argv[2]) if len(sys.argv) > 2 else 235
BED = int(sys.argv[3]) if len(sys.argv) > 3 else 75
ZOFF = float(sys.argv[4]) if len(sys.argv) > 4 else 0.08
PA_FACTOR = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

LAYER_H, LINE_W, FIL_D = 0.2, 0.4, 1.75
SIZE = 25.0
HEIGHT = float(sys.argv[5]) if len(sys.argv) > 5 else 8.0
PERIMS = 2
CENTRE = (110.0, 110.0)
FIRST_LAYER_SPEED = 20.0
TRAVEL = 6000

E_PER_MM = (LAYER_H * LINE_W) / (math.pi * (FIL_D / 2) ** 2)
LAYERS = int(round(HEIGHT / LAYER_H))

L = []
def g(s): L.append(s)

g(f"; hollow tower {SIZE:.0f}x{SIZE:.0f}x{HEIGHT:.0f} mm, {LAYERS} layers")
g(f"; speed {SPEED:.0f} mm/s, hotend {HOT}, bed {BED}, z offset {ZOFF}")
if PA_FACTOR:
    g(f"; PRESSURE ADVANCE SWEEP: factor {PA_FACTOR}, "
      f"PA 0 -> {PA_FACTOR*HEIGHT:.3f} over {HEIGHT:.0f} mm")
    g(f"; best_height_mm * {PA_FACTOR} = pressure_advance")
g("M140 S%d" % BED)
g("M104 S%d" % HOT)
g("G28")
g("M190 S%d" % BED)
g("M109 S%d" % HOT)
g("G90")
g("M83")
g("SET_GCODE_OFFSET Z=%.3f" % ZOFF)
g("G1 Z5 F600")

# PRIME LINE
# Y80, not Y50: the COMGROW logo is SCREEN-PRINTED onto the PEI and that patch
# does not take adhesion - the prime line simply would not stick there. Keep
# everything clear of it.
# Also made long (140 mm + 90 mm L = 230 mm) because the first run had rough
# bottom layers: the nozzle was not fully flowing by the time the object
# started. Purge length is the cure for that.
PRIME_Y = 80.0
PRIME_X0, PRIME_X1 = 40.0, 180.0
PRIME_LEN = PRIME_X1 - PRIME_X0
g("; --- prime (long, clear of the COMGROW logo) ---")
g("G1 X%.1f Y%.1f F%d" % (PRIME_X0, PRIME_Y, TRAVEL))
g("G1 Z%.3f F300" % LAYER_H)
g("G1 X%.1f Y%.1f E%.4f F%d" % (PRIME_X1, PRIME_Y, PRIME_LEN * E_PER_MM, FIRST_LAYER_SPEED * 60))
# SECOND LEG TURNS 90 DEGREES rather than running back alongside the first.
# Two parallel passes 0.4 mm apart merge into each other and clump - clearly
# so in PETG, which is what spoiled the last prime. The L puts the second leg
# on clean plate. X180 is well clear of the tower at X97.5-122.5.
PRIME_LEG2 = 90.0
g("G1 X%.1f Y%.1f E%.4f F%d" % (PRIME_X1, PRIME_Y + PRIME_LEG2, PRIME_LEG2 * E_PER_MM, FIRST_LAYER_SPEED * 60))
# RETRACT before the long travel to the tower, and lift so the nozzle cannot
# drag the end of the prime line across the plate.
g("G10")
g("G1 Z2 F300")

# PRESSURE ADVANCE SWEEP, if asked for. Issued after the prime so the prime line
# is not part of the ramp.
if PA_FACTOR:
    g("; --- pressure advance sweep: PA = Z * %.4f ---" % PA_FACTOR)
    g("SET_PRESSURE_ADVANCE ADVANCE=0")
    g("TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE "
      "START=0 FACTOR=%.5f" % PA_FACTOR)

cx, cy = CENTRE
for layer in range(LAYERS):
    z = (layer + 1) * LAYER_H
    feed = (FIRST_LAYER_SPEED if layer == 0 else SPEED) * 60
    g(f"; --- layer {layer+1}  z={z:.2f} ---")
    # RETRACT before the layer change. This was the bug in the first attempt:
    # a G11 was emitted at each layer start with no matching G10 at the layer
    # END, and G11 with nothing retracted is a NO-OP - so there was effectively
    # no retraction at all across 200 layers, and it strung exactly as if none
    # had been added. Retract/unretract must be PAIRED.
    if layer > 0:
        g("G10")
    g("G1 Z%.3f F%d" % (z, 600))
    for i in range(PERIMS):
        half = SIZE / 2 - i * LINE_W
        x0, y0 = cx - half, cy - half
        x1, y1 = cx + half, cy + half
        side = 2 * half
        e = side * E_PER_MM
        if i == 0:
            # travel to the start of this layer - unretract once we are there.
            # G11 is a no-op if nothing is retracted, so this is safe every layer.
            g("G1 X%.3f Y%.3f F%d" % (x0, y0, TRAVEL))
            g("G11")
        else:
            g("G1 X%.3f Y%.3f F%d" % (x0, y0, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x1, y0, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x1, y1, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x0, y1, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x0, y0, e, feed))

g("; --- done ---")
# RETRACT before the long travel to park, or it strings right across the part.
g("G10")
g("G1 Z%.3f F600" % (HEIGHT + 15))
g("G1 X10 Y200 F%d" % TRAVEL)
g("M104 S0")
g("M140 S0")
g("SET_GCODE_OFFSET Z=0")
g("M84")

path = '/home/josh/gcode_files/tower.gcode'
open(path, 'w').write("\n".join(L) + "\n")
per_layer = PERIMS * 4 * (SIZE - LINE_W)
print(f"wrote {path}  ({len(L)} lines)")
print(f"{LAYERS} layers, ~{per_layer:.0f} mm extrusion per layer, "
      f"~{LAYERS*per_layer/SPEED/60:.1f} min of extruding at {SPEED:.0f} mm/s")
if PA_FACTOR:
    print(f"PRESSURE ADVANCE SWEEP: 0 -> {PA_FACTOR*HEIGHT:.3f} over "
          f"{HEIGHT:.0f} mm.  pressure_advance = best_height_mm * {PA_FACTOR}")
    for h in (10, 20, 30, 40):
        if h <= HEIGHT:
            print(f"   {h:3d} mm up = PA {h*PA_FACTOR:.3f}")
