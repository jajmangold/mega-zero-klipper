#!/bin/bash
# Re-attach a printer MCU to the klipper container after it re-enumerates.
#
# Incus resolves a unix-char device's source at ATTACH time, so when the
# RP2040 re-enumerates (which it does on every FIRMWARE_RESTART, being native
# USB) the mapping inside the container goes stale and the device vanishes.
# Setting the same source again is a no-op; the device must be REMOVED and
# RE-ADDED. That works on a running container - no restart needed.
#
# This is the incus equivalent of the usbipd attach-watchdog on the laptop.
CT=klipper
LOG=/var/log/incus-klipper-usb.log
case "${1:-}" in
  pico) DEV=mcu-pico;  BYID=/dev/serial/by-id/usb-Klipper_rp2040_E6614C3093449930-if00 ;;
  avr)  DEV=mcu-avr;   BYID=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 ;;
  *) exit 0 ;;
esac

exec >>"$LOG" 2>&1
echo "$(date '+%F %T') $1 event"

# let udev finish creating the by-id symlink
for i in $(seq 1 15); do [ -e "$BYID" ] && break; sleep 1; done
[ -e "$BYID" ] || { echo "  $BYID never appeared, giving up"; exit 0; }

incus info "$CT" >/dev/null 2>&1 || { echo "  container not present"; exit 0; }

incus config device remove "$CT" "$DEV" >/dev/null 2>&1
incus config device add "$CT" "$DEV" unix-char \
    source="$BYID" path="$BYID" uid=1001 gid=1001 mode=0660 required=false >/dev/null 2>&1 \
  && echo "  re-attached $DEV" || { echo "  re-attach FAILED"; exit 0; }

# klippy cannot recover a vanished MCU on its own
incus exec "$CT" -- systemctl restart klipper >/dev/null 2>&1
sleep 18
S=$(incus exec "$CT" -- curl -s --max-time 8 http://127.0.0.1:7125/printer/info 2>/dev/null \
    | grep -o '"state":"[a-z]*"' | head -1)
echo "  klippy after restart: ${S:-unknown}"
