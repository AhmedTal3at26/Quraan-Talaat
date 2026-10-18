"""
segment_surahs.py — يحدّد صفحة بداية كل سورة بدقة.

الصفحات تتناوب وجهًا/ظهرًا، وخانة اسم السورة تتحرك معها، لذا نقارن كل صفحة
بالبعد عنها صفحتين (نفس الزوجية). انخفاض التشابه يعني بداية سورة جديدة.

ثم ندمج الشواذ: القطعة التي صفحة واحدة فقط ويشبه ما قبلها ما بعدها فهي
عيب رسم لا سورة جديدة.

    python tools/segment_surahs.py --thr 0.95
"""
import argparse, json, os, pickle
import numpy as np
from PIL import Image, ImageDraw
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"


def cos(a, b):
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr", type=float, default=0.95)
    args = ap.parse_args()

    rows = {(r["v"], r["p"]): r for r in
            pickle.load(open(os.path.join(WORK, "header_sigs.pkl"), "rb"))["rows"]}
    jobs = [(v, p) for v in range(1, 20) for p in range(1, 33) if not (v == 1 and p < 6)]
    n = len(jobs)
    S = [rows[j]["sig"] for j in jobs]
    print("text pages:", n)

    def sim(i, j):
        if S[i] is None or S[j] is None:
            return 1.0
        return cos(S[i], S[j])

    starts = [0]
    for i in range(2, n - 1):
        # تغيّر بين i-2 و i  وحده لا يكفي: لو تغيّرت البدايتان i-2→i و i-1→i+1
        # معًا فالصفحة i هي أول صفحة سورة جديدة.
        if sim(i, i - 2) < args.thr and sim(i - 1, i + 1) >= args.thr:
            starts.append(i)
    print("raw boundaries:", len(starts))

    # merge single-page segments whose neighbours match (rendering glitch)
    changed = True
    while changed:
        changed = False
        bounds = starts[:]
        for k in range(1, len(bounds) - 1):
            a, b, c = bounds[k - 1], bounds[k], bounds[k + 1]
            if b - a == 1 and sim(a, c) >= args.thr:
                starts.remove(b); changed = True; break
    print("after merge:", len(starts))

    segs = []
    for k, a in enumerate(starts):
        b = (starts[k + 1] - 1) if k + 1 < len(starts) else n - 1
        segs.append(dict(k=k, v=jobs[a][0], p=jobs[a][1], n=b - a + 1))

    def printed(s):
        return (s["p"] - 5) if s["v"] == 1 else 27 + (s["v"] - 2) * 32 + s["p"]

    for s in segs:
        print("   S%-3d v%-2d p%-3d n=%-3d printed=%d" % (s["k"], s["v"], s["p"], s["n"], printed(s)))
    for s in segs:
        s["printed"] = printed(s)
    json.dump(segs, open(os.path.join(WORK, "segments.json"), "w"), indent=0)

    cell = 300; cols = 8
    rn = (len(segs) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rn * (cell // 2 + 16)), (245, 245, 245))
    dr = ImageDraw.Draw(img)
    cache = {}
    for k, s in enumerate(segs):
        key = (s["v"], s["p"])
        if key not in cache:
            d = pymupdf.open(os.path.join(SRC, f"m {s['v']:02d} Qraan nos .pdf"))
            pix = d[s["p"] - 1].get_pixmap(matrix=pymupdf.Matrix(6, 6),
                                            clip=pymupdf.Rect(70, 32, 200, 64),
                                            alpha=False, colorspace=pymupdf.csRGB)
            cache[key] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            d.close()
        t = cache[key].resize((cell, cell // 2), Image.LANCZOS)
        x = (k % cols) * cell; y = (k // cols) * (cell // 2 + 16)
        img.paste(t, (x, y + 15))
        dr.text((x + 3, y + 2), f"S{k} v{s['v']}p{s['p']} pr{s['printed']} n{s['n']}", fill=(0, 0, 0))
    out = os.path.join(WORK, "segments_sheet.png")
    img.save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()