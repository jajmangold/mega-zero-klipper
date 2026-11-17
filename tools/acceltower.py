#!/usr/bin/env python3
# Acceleration / ringing tower. Same square printed in bands at rising ACCEL.
# Ringing shows as ripples on the wall AFTER each sharp corner.
W = H = 50.0
X0, Y0 = 42.5, 95.0          # centred in the usable area (67.5,120)
LH, EW, FD = 0.2, 0.42, 1.75
EPM = (EW*LH)/(3.14159265*(FD/2)**2)
BANDS   = [500, 1000, 1500, 2000, 3000]
BAND_H  = 5.0                # mm per band
SPEED   = 80*60              # constant wall speed so bands are comparable
FIRST   = 25*60
o=[]; a=o.append
def seg(x,y,cx,cy,f):
    d=((x-cx)**2+(y-cy)**2)**0.5
    a("G1 X%.3f Y%.3f E%.5f F%d"%(x,y,d*EPM,f)); return x,y
def loop(x0,y0,w,h,f):
    pts=[(x0,y0),(x0+w,y0),(x0+w,y0+h),(x0,y0+h),(x0,y0)]
    cx,cy=pts[0]
    for (x,y) in pts[1:]: cx,cy=seg(x,y,cx,cy,f)

a("; acceleration / ringing tower")
a("PRINT_START BED=75 EXTRUDER=235")
a("G90"); a("M83"); a("G92 E0")
a("SET_VELOCITY_LIMIT ACCEL=500 ACCEL_TO_DECEL=250")

z=LH
a("G1 Z%.3f F300"%z)
# layer 1: 3 brim loops outward, then the wall
a("G1 E-0.8 F2100")
a("G1 X%.3f Y%.3f F6000"%(X0-1.35, Y0-1.35)); a("G1 E0.8 F2100")
for i in (1.35,0.90,0.45):
    loop(X0-i, Y0-i, W+2*i, H+2*i, FIRST)
    a("G1 X%.3f Y%.3f F3000"%(X0-i+0.45, Y0-i+0.45)) if i>0.45 else None
loop(X0, Y0, W, H, FIRST)

nlayer = int(len(BANDS)*BAND_H/LH)
cur=None
for n in range(1, nlayer):
    z = round(LH*(n+1), 3)
    b = BANDS[min(int((z-LH)/BAND_H), len(BANDS)-1)]
    if b != cur:
        a("; ---- band %d mm/s2 at Z%.1f ----"%(b,z))
        a("SET_VELOCITY_LIMIT ACCEL=%d ACCEL_TO_DECEL=%d"%(b, b//2)); cur=b
    a("G1 Z%.3f F%d"%(z, 900))
    loop(X0, Y0, W, H, SPEED)

a("G1 E-1.0 F2100")
a("SET_VELOCITY_LIMIT ACCEL=500 ACCEL_TO_DECEL=250")
a("G1 Z%.1f F600"%(z+15)); a("G1 X5 Y200 F6000")
a("TURN_OFF_HEATERS"); a("M107")
open('/home/josh/printer_data/gcodes/acceltower.gcode','w').write("\n".join(o)+"\n")
print("layers: %d   height: %.1f mm"%(nlayer, z))
print("bands : %s"%BANDS)
