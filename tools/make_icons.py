"""Generate PWA PNG icons (no external deps)."""
import os
from PIL import Image, ImageDraw

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")
os.makedirs(HERE, exist_ok=True)

def rounded(draw, box, r, **kw):
    draw.rounded_rectangle(box, radius=r, **kw)

def make(size):
    S = size
    im = Image.new("RGBA", (S, S), (0,0,0,0))
    d = ImageDraw.Draw(im)
    u = S/512.0
    # background
    d.rounded_rectangle([0,0,S-1,S-1], radius=int(96*u), fill=(27,20,12,255))
    for y in range(S):
        t = y/max(1,S-1)
        c = (int(59+(23-59)*t), int(42+(16-42)*t), int(28+(9-28)*t), 255)
        d.line([(0,y),(S,y)], fill=c)
    d.rounded_rectangle([0,0,S-1,S-1], radius=int(96*u), outline=(0,0,0,0))
    # page
    px, py, pw, ph = 96*u, 72*u, 320*u, 368*u
    rounded(d, [px,py,px+pw,py+ph], int(14*u), fill=(253,248,238,255))
    rounded(d, [px,py,px+pw,py+ph], int(14*u), outline=(216,162,74,255), width=max(1,int(7*u)))
    d.line([(256*u,py),(256*u,py+ph)], fill=(200,168,120,150), width=max(1,int(3*u)))
    rows = [(122,96,96),(122,96,96),(164,80,104),(164,104,80),(206,104,88),(206,88,104),
            (248,72,104),(248,104,72),(290,96,80),(290,80,96),(332,88,96),(332,96,88),
            (374,96,72),(374,72,96)]
    fill = (58,42,22,255)
    for y, lw, rw in rows:
        yy = y*u
        rounded(d, [132*u, yy, 132*u+lw*u, yy+9*u], int(4.5*u), fill=fill)
        rounded(d, [284*u, yy, 284*u+rw*u, yy+9*u], int(4.5*u), fill=fill)
    r = 16*u
    d.ellipse([256*u-r, 128*u-r, 256*u+r, 128*u+r], outline=(184,132,47,255), width=max(1,int(5*u)))
    im.save(os.path.join(HERE, f"icon-{size}.png"))

for s in (192, 512, 180):
    make(s)
print("icons written to", os.path.abspath(HERE))