"""Step 3: Fix visual quality — brighten background, circle, and fix composite"""
bg = op('/project1/SRP_BreathGuide/Breath_Guide')

# 1. Brighten background (was 0.05 — nearly black)
rect = bg.op('bg_rect')
try:
    rect.par.fillcolorr = 0.08
    rect.par.fillcolorg = 0.08
    rect.par.fillcolorb = 0.15
    print("bg_rect brightened")
except Exception as e:
    print("bg_rect error: " + str(e))

# 2. Circle — brighter and more visible
circle = bg.op('guide_circle')
try:
    circle.par.fillcolorr = 0.2
    circle.par.fillcolorg = 0.8
    circle.par.fillcolorb = 0.4
    print("circle colors set")
except Exception as e:
    print("circle error: " + str(e))

# 3. Phase tint — reduce alpha so it doesn't wash out
tint = bg.op('phase_tint')
try:
    tint.par.fillcolorr = 0.1
    tint.par.fillcolorg = 0.8
    tint.par.fillcolorb = 0.2
    print("phase_tint set to green (inhale)")
except Exception as e:
    print("tint error: " + str(e))

# 4. Glow — set small amount
glow = bg.op('glow_blur')
try:
    glow.par.sizex = 4
    glow.par.sizey = 4
    print("glow size set")
except Exception as e:
    print("glow error: " + str(e))

# 5. guide_comp — check it renders properly
gcomp = bg.op('guide_comp')
print("guide_comp width:", gcomp.width)
print("guide_comp height:", gcomp.height)

# 6. Check final_comp connections & render
fcomp = op('/project1/SRP_BreathGuide/Output/final_comp')
print("final_comp width:", fcomp.width)

# 7. Display out
dot = op('/project1/SRP_BreathGuide/Output/display_out')
print("display_out active:", dot.par.active.eval())

print("Visual fix applied")
