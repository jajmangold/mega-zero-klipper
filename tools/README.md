# Test gcode generators

Plain Python, no slicer. Each writes a file into the printer's gcode directory
and prints a summary.

| script | what it makes |
|---|---|
| `gen_dd_test.py` | 20x20x10 hollow tower, ~5 min - shakedown after a change |
| `gen_pa_dd.py` | pressure-advance sweep tower (TUNING_TOWER) |
| `gen_tower.py` | configurable tower, optional PA sweep |
| `zladder.py` | ladder of extruded lines at known Z, for z_offset |

## Why these exist

They emit no `SET_VELOCITY_LIMIT` and nothing slicer-specific, so they run at
the machine's configured limits.

That makes them a **diagnostic**: if these print cleanly and sliced files do
not, the fault is in the slicer output, not the machine. That comparison is the
fastest way to split "printer problem" from "slicer problem" — see
`docs/troubleshooting.md`.

## Notes

- They call `PRINT_START` / `PRINT_END`, so homing, mesh load, purge and wipe
  all happen via the macros in `printer.cfg`
- Retraction is plain `G1 E` moves, **not** `G10`/`G11` - mixing the two hides
  which is actually acting
- `max_extrude_only_distance` defaults to 50 mm, so long purges must be split
- `zladder.py` draws real extruded lines rather than relying on paper feel,
  which has repeatedly given wrong answers on this machine
