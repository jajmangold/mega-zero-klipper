# Anycubic Mega Zero → Klipper

An Anycubic Mega Zero V1 rebuilt as a two-MCU Klipper machine with a heated bed,
dual Z, a capacitive probe and a direct-drive extruder, running from an Incus
container with Moonraker and Mainsail.

This repo is the working configuration plus the notes needed to rebuild or debug
it. Most of the value is in [`docs/`](docs/) — in particular
[`docs/troubleshooting.md`](docs/troubleshooting.md), which records faults that
cost hours and would otherwise have to be rediscovered.

## The machine

| | |
|---|---|
| Base | Anycubic Mega Zero V1 (originally no heated bed, single Z, bowden) |
| Motion MCU | ATmega1284P ("Trigorilla Zero", a Melzi) — X, Y, dual Z, display |
| Second MCU | RP2040-Zero — both heaters, extruder, probe, 24 V relay |
| Hotend | E3D V6 clone, 40 W / 24 V, 0.4 nozzle |
| Extruder | **direct drive, ungeared** (`rotation_distance: 22.2`) |
| Probe | **capacitive**, 12 V, `x_offset -55 / y_offset -19` |
| Bed | added heated bed on the old aluminium plate, PEI sheet |
| Z | dual leadscrew, levelled with `z_tilt` |

## Calibrated values

These are measured, not guessed. See [`docs/calibration.md`](docs/calibration.md)
for how each was obtained.

| setting | value |
|---|---|
| `rotation_distance` (extruder) | **22.2** |
| `z_offset` | **1.355** |
| `pressure_advance` | 0.04 |
| retraction | 0.8 mm @ 35 mm/s |
| PETG | 235 °C nozzle / 75 °C bed |
| X travel | **−9 … 185** (not 220 — see below) |
| bed mesh | 5×5 over X 15–120, Y 45–195, range 0.30 mm |

## Three things that will bite you

**X travel is 185 mm, not the 220 the frame suggests.** Any move past 185 grinds
the carriage into the frame and *silently loses steps*. Every position reported
afterwards is fiction. The symptom is `No trigger on probe after full movement`,
which reads exactly like a dead probe — and a failed `PROBE` then drives Z down
into the bed and corrupts the Z reference too. Re-home before concluding
anything about the probe.

**The slicer can override `max_accel`.** Orca's Klipper flavour emits
`SET_VELOCITY_LIMIT ACCEL=` into the gcode, which overrides the config value at
runtime — `max_accel` is a default, not a ceiling. A stock process profile asked
for 5000–7000 mm/s² on this 500 mm/s² machine, 14,354 times in one file.

**`rotation_distance` is unknown after an extruder swap, not approximately
right.** This one was left at the old *geared bowden* value after fitting an
*ungeared direct drive* unit: 2.5× over-extrusion on every print.

## Layout

```
config/      printer.cfg and moonraker.conf as they actually run
container/   Incus container: systemd units, USB hotplug rule
slicer/      Orca presets (machine, filament, process)
tools/       gcode generators for calibration and shakedown prints
docs/        hardware, calibration method, troubleshooting
```

## Quick start

The printer runs in an Incus container on a separate host. Mainsail is on
port 80 of the container's LAN address.

```bash
incus exec klipper -- systemctl status klipper moonraker nginx
```

To rebuild the container from scratch, see
[`container/README.md`](container/README.md).

**After any WSL/host restart or `FIRMWARE_RESTART`**, the RP2040 may come back
holding a shutdown state. The udev rule in `container/` handles this
automatically; if you are doing it by hand the sequence is
`FIRMWARE_RESTART` → wait ~25 s → `systemctl restart klipper`. A plain service
restart is *not* enough.

## Licence

MIT — see [LICENSE](LICENSE).

Klipper and Moonraker are separate projects under their own licences; nothing
from them is vendored here. These are configuration files and helper scripts.
