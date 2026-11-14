# Incus container

Klipper, Moonraker and Mainsail run in an Incus container on a separate host,
rather than on a Pi or on the workstation. This replaced a WSL setup that kept
losing USB attachments and dying mid-print.

## Create

Built to match the host's existing conventions — Ubuntu noble, `nvme-cow` pool,
`boot.autostart`, CPU/memory limits, `default` profile:

```bash
incus launch images:ubuntu/noble klipper \
  --storage nvme-cow \
  -c boot.autostart=true \
  -c limits.cpu=2 \
  -c limits.memory=4GiB \
  -c security.privileged=true

# second NIC so the web UI gets a real LAN address
incus config device add klipper eth1 nic nictype=macvlan parent=eno1
```

`eth1` needs its own netplan inside the container — the image only configures
`eth0`:

```yaml
# /etc/netplan/11-eth1.yaml   (chmod 600)
network:
  version: 2
  ethernets:
    eth1:
      dhcp4: true
      dhcp4-overrides:
        use-dns: false
        route-metric: 50
```

`netplan apply` fails inside a container (`udevadm control --reload`); restart
the container instead.

> **macvlan means the host itself cannot reach the container.** Every other
> machine on the LAN can; the host running it cannot. That is inherent, not a
> misconfiguration.

## Install

Inside the container: Klipper + Moonraker in separate venvs under `/home/josh`,
Mainsail served by nginx on port 80 proxying Moonraker on 7125.

Gotchas worth knowing:

- Ubuntu 24.04 needs **`python3.12-venv`**; plain `python3 -m venv` fails with
  *ensurepip is not available*
- Recent Moonraker uses sqlite, **not lmdb** — a missing `lmdb` import is not a
  failed install
- nginx needs **`chmod o+x /home/josh`** or it 403s on the Mainsail files
- `printer_data/gcodes` is a **symlink** to `/home/josh/gcode_files`, because
  `virtual_sdcard` points there and the generators write there by hardcoded path

## USB passthrough

Map each character device **directly to its by-id path**, so `printer.cfg` works
unmodified:

```bash
incus config device add klipper mcu-pico unix-char \
  source=/dev/serial/by-id/usb-Klipper_rp2040_<serial>-if00 \
  path=/dev/serial/by-id/usb-Klipper_rp2040_<serial>-if00 \
  uid=1001 gid=1001 mode=0660 required=false
```

**Use the by-id symlink as the source.** Hardcoding `/dev/ttyUSB0` broke when
the CH340 re-enumerated as `ttyUSB1`.

`uid=1001` — the image already has `ubuntu` at 1000, so a `josh` useradd lands
on 1001. Getting this wrong gives permission-denied on the serial device.

`required=false` lets the container start with the printer unplugged.

## The hotplug problem

**Incus resolves a device's source at *attach* time.** When the RP2040
re-enumerates — which it does on every `FIRMWARE_RESTART`, being native USB —
the mapping goes stale and the device vanishes from the container.

Setting the same source again is a **no-op**. The device must be *removed and
re-added*, which works on a running container.

`99-klipper-incus.rules` + `incus-klipper-usb.sh` do this automatically and then
restart klipper. Install to `/etc/udev/rules.d/` and `/usr/local/bin/` on the
**host**, not in the container, then `udevadm control --reload-rules`.

Log: `/var/log/incus-klipper-usb.log`

## systemd units

`klipper.service` and `moonraker.service` go in `/etc/systemd/system/` inside
the container.

Two details that matter:

**`-a <socket>`** — klippy needs the API socket or Moonraker cannot connect at
all. Easy to omit and the failure is obscure.

**`ExecStartPre=/bin/rm -f /tmp/printer`** — a stale pty symlink **silently
blocks startup**. No error, no log entry, no process. Foreground start works
fine, which makes it look like a backgrounding problem.

`Restart=on-failure` with `RestartSec=20` and a burst limit, **not
`Restart=always`** with a short delay: klippy *exits* on a config error, so an
aggressive restart policy becomes a storm — 76 start/stop cycles in 20 minutes
in one case, each hitting a still-shutdown MCU and fighting the recovery script.
