#!/usr/bin/env python3
"""Pressure-advance sweep tower for the DIRECT DRIVE conversion.

Ramps PA 0 -> 0.100 over 25 mm (FACTOR 0.004). That is the useful band for
direct drive; the 0 -> 0.8 sweep used for the bowden would put the entire
plausible range in the bottom 3 mm and tell you nothing.

    pressure_advance = height_mm * 0.004
      5 mm = 0.020   10 mm = 0.040   15 mm = 0.060
     20 mm = 0.080   25 mm = 0.100

Read it with CALIPERS from the bed, not by counting layers.

TUNING_TOWER is issued AFTER PRINT_START so the prime line is not part of the
sweep. There is no TUNING_TOWER RESET - the transform uninstalls itself when
it next sees an extrusion move more than 2 mm below the last, i.e. at the
start of the following print. RESTART clears it immediately if needed.
"""
import math

SIZE = 20.0
HEIGHT = 25.0
FACTOR = 0.004
LAYER_H, LINE_W, FIL_D = 0.2, 0.4, 1.75
PERIMS = 2
CENTRE = (90.0, 110.0)
SPEED = 40.0
FIRST_LAYER_SPEED = 18.0
RETRACT = 0.8
RETRACT_F = 35 * 60
TRAVEL = 4000
HOT, BED = 235, 75

E_PER_MM = (LAYER_H * LINE_W) / (math.pi * (FIL_D / 2) ** 2)
LAYERS = int(round(HEIGHT / LAYER_H))

L = []
def g(s): L.append(s)

g("; PA sweep (direct drive): 0 -> %.3f over %g mm, factor %g" % (FACTOR * HEIGHT, HEIGHT, FACTOR))
g("; pressure_advance = best_height_mm * %g" % FACTOR)
g("PRINT_START EXTRUDER=%d BED=%d" % (HOT, BED))
g("G90")
g("M83")
g("SET_PRESSURE_ADVANCE ADVANCE=0")
g("TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE START=0 FACTOR=%.5f" % FACTOR)

cx, cy = CENTRE
for layer in range(LAYERS):
    z = (layer + 1) * LAYER_H
    feed = (FIRST_LAYER_SPEED if layer == 0 else SPEED) * 60
    g("; --- layer %d  z=%.2f  PA=%.4f ---" % (layer + 1, z, z * FACTOR))
    if layer > 0:
        g("G1 E-%.3f F%d" % (RETRACT, RETRACT_F))
    g("G1 Z%.3f F600" % z)
    for i in range(PERIMS):
        half = SIZE / 2 - i * LINE_W
        x0, y0 = cx - half, cy - half
        x1, y1 = cx + half, cy + half
        e = (2 * half) * E_PER_MM
        if i == 0:
            g("G1 X%.3f Y%.3f F%d" % (x0, y0, TRAVEL))
            g("G1 E%.3f F%d" % (RETRACT, RETRACT_F))
        else:
            g("G1 X%.3f Y%.3f F%d" % (x0, y0, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x1, y0, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x1, y1, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x0, y1, e, feed))
        g("G1 X%.3f Y%.3f E%.4f F%d" % (x0, y0, e, feed))

g("; --- done ---")
g("G1 E-%.3f F%d" % (RETRACT, RETRACT_F))
g("PRINT_END")

path = '/home/josh/printer_data/gcodes/pa_sweep_dd.gcode'
open(path, 'w').write("\n".join(L) + "\n")
per_layer = PERIMS * 4 * (SIZE - LINE_W)
print("wrote %s (%d lines)" % (path, len(L)))
print("%d layers, ~%.1f min of extruding at %g mm/s" % (LAYERS, LAYERS * per_layer / SPEED / 60, SPEED))
for h in (5, 10, 15, 20, 25):
    print("   %2d mm up = PA %.3f" % (h, h * FACTOR))
