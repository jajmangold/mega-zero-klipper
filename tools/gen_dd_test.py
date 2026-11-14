#!/usr/bin/env python3
"""Small hollow square tower to shake down the DIRECT DRIVE conversion.

Deliberately short (~5 min) because several things are still unverified:
rotation_distance (never measured after the swap), pressure_advance (0.04 is a
placeholder, not a measurement) and the new retraction length.

Retraction is PLAIN G1 E moves at 0.8 mm - direct drive. Do NOT use G10/G11
here: [firmware_retraction] is a separate setting and mixing them hides which
one is actually acting.

PRINT_START does the homing, mesh load, bucket purge, pad wipe and prime line,
so this file only has to draw the object.
"""
import math

SIZE = 20.0
HEIGHT = 10.0
LAYER_H, LINE_W, FIL_D = 0.2, 0.4, 1.75
PERIMS = 2
CENTRE = (90.0, 110.0)      # inside the mesh (15,45 -> 120,195) and X travel (<185)
SPEED = 40.0                # mm/s - accel is 500, no input shaper
FIRST_LAYER_SPEED = 18.0
RETRACT = 0.8               # DIRECT DRIVE
RETRACT_F = 35 * 60
TRAVEL = 4000
HOT, BED = 235, 75

E_PER_MM = (LAYER_H * LINE_W) / (math.pi * (FIL_D / 2) ** 2)
LAYERS = int(round(HEIGHT / LAYER_H))

L = []
def g(s): L.append(s)

g("; direct-drive shakedown tower %gx%gx%g, %d layers" % (SIZE, SIZE, HEIGHT, LAYERS))
g("; retraction %.2f mm (plain E moves), speed %g mm/s" % (RETRACT, SPEED))
g("PRINT_START EXTRUDER=%d BED=%d" % (HOT, BED))
g("G90")
g("M83")

cx, cy = CENTRE
for layer in range(LAYERS):
    z = (layer + 1) * LAYER_H
    feed = (FIRST_LAYER_SPEED if layer == 0 else SPEED) * 60
    g("; --- layer %d  z=%.2f ---" % (layer + 1, z))
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

path = '/home/josh/printer_data/gcodes/dd_test.gcode'
open(path, 'w').write("\n".join(L) + "\n")
per_layer = PERIMS * 4 * (SIZE - LINE_W)
print("wrote %s (%d lines)" % (path, len(L)))
print("%d layers, ~%.0f mm per layer, ~%.1f min of extruding at %g mm/s"
      % (LAYERS, per_layer, LAYERS * per_layer / SPEED / 60, SPEED))
print("retract count: %d  unretract count: %d" % (
    sum(1 for x in L if x.startswith("G1 E-")), sum(1 for x in L if x.startswith("G1 E0.8"))))
