# Hardware

The machine as built, and the electrical decisions that the config depends on.

## Two MCUs

| MCU | Board | Owns |
|---|---|---|
| `mcu` | ATmega1284P ("Trigorilla Zero", a Melzi) | X, Y, **both Z**, display, part fan |
| `pico` | RP2040-Zero | both heaters, extruder, probe, 24 V relay |

**Both Z steppers must be on the same MCU.** Splitting Z0 and Z1 across MCUs
makes the config refuse to load:

```
Config error: Multi-mcu homing not supported on multi-mcu shared axis
```

Probe-on-pico with both Z on the AVR is ordinary multi-MCU homing, which Klipper
does support — it's the standard CAN-toolhead arrangement.

### Flashing the AVR

It is an **ATmega1284P**, signature `1E 97 05` — *not* the ATmega2560 other
Anycubic Trigorilla boards use.

```
avrdude -c arduino -p m1284p -P <port> -b 115200 -D
```

`-D` is **mandatory**. Optiboot refuses to read out its own section, so the top
of flash dumps as `0xFF` and there is no bootloader backup — auto-erase would
brick it.

The board enumerates as a CH340 and **the COM number is not stable**. Enumerate
by VID/PID (`1a86:7523`) rather than hardcoding. Note it is USB-powered, so the
port appears even with the printer PSU off.

## 24 V relay

The 24 V supply is behind a mains relay driven by the pico. A bare `M104`/`M140`
from a slicer would set a target with the supply dead, and `verify_heater` would
shut the printer down a minute later.

`M140` / `M190` / `M104` / `M109` are **overridden as macros** to assert the
relay first. **Do not replace them with `SET_HEATER_TEMPERATURE`** — that
bypasses the relay logic. `PRINT_START` calls the overridden versions
deliberately.

The relay drops only when **both** heaters read zero.

## Hotend

E3D V6 clone, **40 W / 24 V**, so `max_power: 1.0` is correct.

> **Check cartridge wattage on any hotend swap.** A 12 V cartridge on the 24 V
> rail is 4× power — ~160 W into a 40 W part. **`verify_heater` cannot catch
> this**; it only ever watches for too *little* heating. `max_power: 0.25` is
> not a fix either, as peak current is still double rated.
>
> Expected resistance: **~14.4 Ω** for 24 V/40 W, **~3.6 Ω** for 12 V/40 W.

Working ceiling **240 °C**, `max_temp` 250. The PTFE liner depth on a clone is
unknown and >240 degrades it.

The thermistor is configured `Generic 3950` but is **inferred, not measured**. A
room-temperature reading cannot validate a curve — EPCOS, Generic 3950 and
Semitec are all 100 k at 25 °C and only diverge when hot. Confirming it needs a
thermocouple on the block at a 200 °C setpoint.

### Silicone sock

**A missing sock looks exactly like a failing heater.** Without it the block
stalled at ~233 °C with `pwm` pinned at 1.000. Refitted, it holds 240 at
0.66–1.0.

Steady-state plateau below target at full power is always a **heat-loss**
problem, never thermal mass — mass sets how fast you heat, not what you can
hold.

### Heatbreak fan — invisible to Klipper

It is on **FAN4, an unswitched 12 V passthrough with no MOSFET**. A Melzi has
exactly one fan MOSFET (PB4) and FAN4 isn't it, so there is no pin to put in a
`[heater_fan]` section.

**Klipper cannot report that this fan has stopped.** Its absence from the config
is a finding, not an oversight. Eyeball it before long prints — heat creep
presents as under-extrusion that worsens with time.

## Probe — capacitive

12 V, not on the relay-switched 24 V (which removes the old failure mode where
homing with the rail off crashed the nozzle).

`pin: ^!pico:gpio1` — inverted. At rest the pin reads HIGH; triggering pulls it
LOW.

> **Residual risk, known and accepted.** With `!`, a broken or unseated signal
> wire floats HIGH on the pullup and reads `open` — indistinguishable from "not
> triggered". Z would then home downwards and never trigger. Treat an
> unexplained failure to trigger as a **wiring** fault first — *after* ruling
> out a lost-step crash (see [troubleshooting](troubleshooting.md)).

Being capacitive, it senses the plate surface rather than ferrous material, and
its response falls off gradually near an edge — so "where it stops triggering"
is fuzzy by several millimetres and should not be used to derive offsets.

## Extruder — direct drive, ungeared

`rotation_distance: 22.2` (≈ 7.07 mm effective MK8 gear).

DRV8825 on the pico, **Vref 0.45 V = 0.9 A**. At the inherited 0.65 V it buzzed
and stalled on sustained 50 mm moves while short ones worked — the DRV8825
thermal-shutdown signature. An extruder needs far less current than an axis
motor.

DIP switches 1-0-0 = 1/16, silkscreened MS3/MS2/MS1 left to right.

## Bed

Heated bed added to the old aluminium plate, PEI sheet on top.

**PETG bonds to bare PEI hard enough to tear the sheet.** Let the plate cool
fully before removing parts.

**The COMGROW logo is screen-printed onto the PEI and takes no adhesion.**
Nothing sticks on that patch. A `bedmap.gcode` grid print on 2026-11-16 placed it
**entirely in front of Y45**, i.e. outside the meshed area altogether — so the old
"run the prime line at Y80 to clear the logo" rule was ~35 mm over-cautious. The
prime line now runs an L at X18 Y150 → X18 Y50 → X60 Y50.

## Purge bucket and wipe pad

A printed, foil-lined bucket hangs below the PEI on the old unheated aluminium
bed (X 0–135 at Y 17, Z 0), with a 3M pad on a tab at the plate edge
(X 160–185, surface Z 2.5; wipe at Z 2.2).

`PURGE_AND_WIPE` uses both — see the macro in `config/printer.cfg` for the
sequence and why each step is where it is.
