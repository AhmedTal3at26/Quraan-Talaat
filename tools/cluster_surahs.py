"""
cluster_surahs.py — يجمّع خانة اسم السورة لكل سورة.

خانة الاسم تتحرك بين الوجه والظهر، فتظهر كل سورة كمجموعتين (وجه/ظهر).
نرتّب المجموعات حسب أول صفحة، ثم ندمج كل مجموعتين متتاليتين = سورة واحدة.

    python tools/cluster_surahs.py --thr 0.95
"""
import argparse, json, os, pickle
import numpy as np
from PIL import Image, ImageDraw
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr", type=float, default=0.95)
    args = ap.parse_args()

    rows = {(r["v"], r["p"]): r for r in
            pickle.load(open(os.path.join(WORK, "header_sigs.pkl"), "rb"))["rows"]}
    jobs = [(v, p) for v in range(1, 20) for p in range(1, 33) if not (v == 1 and p < 6)]
    S = [rows[j]["sig"] for j in jobs]
    n = len(jobs)
    print("text pages:", n)

    cents, assign = [], []
    for v in S:
        nv = np.linalg.norm(v) + 1e-9
        best, bi = -1, -1
        for j, c in enumerate(cents):
            s = float((c @ v) / (np.linalg.norm(c) * nv))
            if s > best: best, bi = s, j
        if best >= args.thr:
            assign.append(bi)          # المرجع ثابت (medoid) - لا ينزاح
        else:
            cents.append(v / nv); assign.append(len(cents) - 1)
    print("raw clusters:", len(cents))

    groups = {}
    for i, a in enumerate(assign):
        groups.setdefault(a, []).append(i)
    order = sorted(groups.values(), key=lambda g: g[0])
    print("ordered clusters:", len(order))

    surahs = [order[i] + order[i + 1] for i in range(0, len(order) - 1, 2)]
    if len(order) % 2:
        surahs.append(order[-1])
    print("merged surah groups:", len(surahs))

    # quality: within-group stride-2 similarity
    bad = 0
    for g in surahs:
        for i in range(2, len(g)):
            a, b = S[g[i - 2]], S[g[i]]
            if float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)) < 0.95:
                bad += 1
    print("intra-group violations:", bad)

    def printed(idx):
        v, p = jobs[idx]
        return (p - 5) if v == 1 else 27 + (v - 2) * 32 + p

    table = []
    for k, g in enumerate(surahs):
        v, p = jobs[g[0]]
        v2, p2 = jobs[g[-1]]
        table.append(dict(k=k, startIdx=g[0], endIdx=g[-1], v=v, p=p, v2=v2, p2=p2,
                          n=len(g), printed=printed(g[0]), printedEnd=printed(g[-1])))
    json.dump(table, open(os.path.join(WORK, "surah_starts.json"), "w"), indent=0)
    for t in table:
        print("  S%-3d printed %3d..%3d  (%d pages)  v%d p%d" %
              (t["k"], t["printed"], t["printedEnd"], t["n"], t["v"], t["p"]))

    cell = 300; cols = 8
    rn = (len(table) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rn * (cell // 2 + 16)), (245, 245, 245))
    dr = ImageDraw.Draw(img)
    cache = {}
    for k, t in enumerate(table):
        key = (t["v"], t["p"])
        if key not in cache:
            d = pymupdf.open(os.path.join(SRC, f"m {t['v']:02d} Qraan nos .pdf"))
            pix = d[t["p"] - 1].get_pixmap(matrix=pymupdf.Matrix(6, 6),
                                            clip=pymupdf.Rect(70, 32, 200, 64),
                                            alpha=False, colorspace=pymupdf.csRGB)
            cache[key] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            d.close()
        t2 = cache[key].resize((cell, cell // 2), Image.LANCZOS)
        x = (k % cols) * cell; y = (k // cols) * (cell // 2 + 16)
        img.paste(t2, (x, y + 15))
        dr.text((x + 3, y + 2), f"S{k} pr{t['printed']} n{t['n']}", fill=(0, 0, 0))
    out = os.path.join(WORK, "surah_sheet.png")
    img.save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()