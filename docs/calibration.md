# Calibration

How each measured value was obtained, and in what order. The order matters —
several of these invalidate the ones after them.

## Order of operations

1. **Axis travel limits** — everything downstream is meaningless if positions
   are fiction
2. **Probe offsets** — measure with a ruler
3. **`rotation_distance`** (flow)
4. **`z_tilt`** (gantry level)
5. **Bed mesh**
6. **`z_offset`** — must come *after* flow and levelling
7. **Pressure advance**

---

## 1. Axis travel

**X travel is 185 mm**, despite a 220 mm bed. `position_max` was 220, and every
move beyond 185 drove the carriage into the frame and lost steps silently.

Measure by jogging in small steps and watching/listening, then set
`position_max` so Klipper *refuses* the move rather than attempting it.

> **Y is still unverified** at `position_max: 220`. Same condition that caused
> the X crashes. Worth measuring before anything uses the back of the bed.

## 2. Probe offsets

**Measure with a ruler: nozzle tip to the centre of the probe face.**

Attempts to infer these from where the probe stops triggering produced numbers
that were simply wrong — bed tilt and a loaded mesh both move the apparent
"edge" by millimetres. The ruler took ten seconds and landed within 5 mm of the
config's existing values.

```
x_offset: -55.0
y_offset: -19.0
```

**Bed-slinger sign trap:** the probe sits physically *behind* the nozzle but is
at a *lower* bed Y — it leaves the plate's front edge before the nozzle does, so
`y_offset` is **negative**. Physical "behind" and bed-coordinate "+Y" are
opposite on a moving-bed machine.

**Consequence:** with `x_offset -55` and 185 mm of X travel, the probe can only
reach **bed X 0–130**. The right ~55 mm of the plate is permanently
unmeasurable. Keep parts within X 15–130 for properly-meshed first layers.

## 3. `rotation_distance` — measure it

**A swapped extruder means this is unknown, not approximately right.**

1. Mark the filament a known distance from the extruder inlet
2. Heat to printing temperature, `M83`, command a known extrusion
3. Measure what remains

```
new = old × (actual fed ÷ commanded)
```

Command *less* than the mark distance so the mark stays visible — if it
disappears into the extruder all you learn is "at least that much".

Worked example from this machine:

| step | commanded | fed | result |
|---|---|---|---|
| start | — | — | 8.312 (old geared bowden extruder) |
| 1 | 50 | 125 | → 20.78 |
| 2 | 50 | 55 | → 22.86 |
| final | — | — | **22.2** (trimmed ~3% by eye) |

**Sanity check the result against the hardware:** `22.2 / π ≈ 7.07 mm`, a
standard MK8 hobbed gear. If the number doesn't divide by π into a believable
drive-gear diameter, it's wrong.

**Symptoms of getting this wrong:** extruder skipping (being asked for more than
the nozzle can melt), and a 20 mm cube measuring tall in **Z only** — X and Y
stay near 20.3 because surplus material has nowhere to go but up.

## 4. `z_tilt` — dual Z

Took the bed from **1.42 mm to 0.30 mm** range in one pass.

```
z_positions:          # screw positions, ~438 mm apart
    -109, 85          # 396 mm frame + one NEMA 17 body
    329, 85
points:               # probe points - both left of centre because
    20, 120           # x_offset -55 caps the probe at bed X~130
    115, 120
```

Leverage ratio is 438 ÷ 95 ≈ **4.6**, so every 0.1 mm measured at the probe
becomes ~0.46 mm of screw movement. Approximate screw positions are fine (it
iterates) but not arbitrary.

## 5. Bed mesh

5×5 over X 15–120, Y 45–195. Residual range **0.30 mm** — a gentle dish, back-left
corner lowest.

`fade_start 1.0` / `fade_end 10.0` is important: without it the bed-shape
correction applies at *every* layer, so a tall part is still being Z-shifted by
the plate's shape at its top, and any out-of-mesh extrapolation compounds all
the way up instead of dying out.

## 6. `z_offset`

**Must be done after flow is correct.** A `z_offset` measured while
over-extruding is worthless: the fat bead fills a gap that is really too large.

Paper feel has misled this machine repeatedly — ooze on the tip drags the paper
early by roughly the amount being measured. Retract first and wipe the nozzle.
[`tools/zladder.py`](../tools/zladder.py) draws real extruded lines at known Z
instead, which is the honest instrument.

Sign: lines **dig in** → nozzle closer than Klipper thinks → `z_offset` too
large, reduce. Lines sit as **round beads** → increase. Too small is the safe
direction to be wrong (prints in the air); too large drives the nozzle into the
plate.

Current: **1.355**

## 7. Pressure advance

`0.04`, and **it barely matters on this machine**. A full 0 → 0.100 sweep showed
no visible difference anywhere, because at `max_accel: 500` there is almost no
pressure lag for PA to correct. Don't spend time here unless acceleration is
raised — and raising it without an input shaper brings ringing.

[`tools/gen_pa_dd.py`](../tools/gen_pa_dd.py) generates the sweep tower.
Read it with **calipers from the bed**, not by counting layers.
