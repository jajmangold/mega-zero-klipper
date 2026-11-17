#!/usr/bin/env python3
# Draws a labelled coordinate map over the usable bed area so physical
# features (logo, plate edges, bucket, wipe pad) can be read off in BED
# COORDINATES from a photo.
X0,X1 = 15.0, 120.0        # mesh_min/max X
Y0,Y1 = 45.0, 195.0        # mesh_min/max Y
Z     = 0.2
EW,LH,FD = 0.42, 0.2, 1.75
EPM  = (EW*LH)/(3.14159265*(FD/2)**2)   # E per mm of travel
FP, FT = 1200, 6000
out=[]
def a(s): out.append(s)
def travel(x,y): a("G1 E-0.8 F2100"); a("G1 X%.3f Y%.3f F%d"%(x,y,FT)); a("G1 E0.8 F2100")
def line(x1,y1,x2,y2):
    d=((x2-x1)**2+(y2-y1)**2)**0.5
    a("G1 X%.3f Y%.3f E%.5f F%d"%(x2,y2,d*EPM,FP))
def poly(pts):
    travel(*pts[0])
    for p in pts[1:]: line(0,0,*p) if False else a("")
a("; bed coordinate map")
a("PRINT_START BED=75 EXTRUDER=235")
a("G90"); a("M83"); a("G92 E0"); a("G1 Z%.2f F300"%Z)

def stroke(pts):
    travel(pts[0][0],pts[0][1])
    cx,cy=pts[0]
    for (x,y) in pts[1:]:
        d=((x-cx)**2+(y-cy)**2)**0.5
        a("G1 X%.3f Y%.3f E%.5f F%d"%(x,y,d*EPM,FP)); cx,cy=x,y

# 1. boundary of the MESHED/usable area
stroke([(X0,Y0),(X1,Y0),(X1,Y1),(X0,Y1),(X0,Y0)])
# 2. corner marker at (15,45) - front-left, fixes orientation
stroke([(X0+3,Y0+3),(X0+18,Y0+3),(X0+3,Y0+18),(X0+3,Y0+3)])
# 3. vertical gridlines every 20mm; X=60 doubled as the reference
for x in (20,40,60,80,100):
    stroke([(x,Y0),(x,Y1)])
    if x==60: stroke([(x+1.2,Y0),(x+1.2,Y1)])
# 4. horizontal gridlines every 30mm; Y=120 doubled as the reference
for y in (60,90,120,150,180):
    stroke([(X0,y),(X1,y)])
    if y==120: stroke([(X0,y+1.2),(X1,y+1.2)])
# 5. proposed NEW prime-line L, drawn so we can see if it clears the logo
stroke([(18,150),(18,50),(60,50)])
a("G1 E-1.0 F2100")
a("G1 Z15 F600"); a("G1 X5 Y200 F6000")
a("TURN_OFF_HEATERS"); a("M107")
open('/home/josh/printer_data/gcodes/bedmap.gcode','w').write("\n".join(out)+"\n")
print("wrote bedmap.gcode, %d lines"%len(out))
