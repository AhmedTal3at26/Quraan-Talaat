"""label_headers.py — يجمّع خانات اسم السورة ويخرج جدولًا للمراجعة + لوحة صور."""
import argparse, json, os, pickle
import numpy as np
from PIL import Image, ImageDraw
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"
HX0, HY0, HX1, HY1 = 66, 33, 154, 65


def cluster(rows, thr):
    idx = [i for i, r in enumerate(rows) if r["sig"] is not None]
    cents, assign = [], {}
    for i in idx:
        v = rows[i]["sig"]; nv = np.linalg.norm(v) + 1e-9
        best, bi = -1, -1
        for j, c in enumerate(cents):
            s = float((c @ v) / (np.linalg.norm(c) * nv))
            if s > best: best, bi = s, j
        if best >= thr:
            assign[i] = bi
            cents[bi] += v; cents[bi] /= (np.linalg.norm(cents[bi]) or 1)
        else:
            cents.append(v / nv); assign[i] = len(cents) - 1
    groups = {}
    for i in idx:
        groups.setdefault(assign[i], []).append(i)
    for g in groups.values():
        g.sort(key=lambda i: (rows[i]["v"], rows[i]["p"]))
    return sorted(groups.values(), key=lambda g: (rows[g[0]]["v"], rows[g[0]]["p"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thr", type=float, default=0.93)
    ap.add_argument("--show", type=int, default=40)
    args = ap.parse_args()
    rows = pickle.load(open(os.path.join(WORK, "header_sigs.pkl"), "rb"))["rows"]
    groups = cluster(rows, args.thr)
    print("clusters:", len(groups))
    table = []
    for k, g in enumerate(groups):
        f = rows[g[0]]
        table.append(dict(k=k, v=f["v"], p=f["p"], n=len(g),
                          pages=[[rows[i]["v"], rows[i]["p"]] for i in g]))
        if k < args.show or len(groups) <= args.show:
            print("  C%-3d first v%-2d p%-3d n=%-3d %s" % (k, f["v"], f["p"], len(g),
                                                         table[-1]["pages"][:5]))
    json.dump(table, open(os.path.join(WORK, "header_groups_ordered.json"), "w"), indent=0)

    cell = 260
    cols = 8
    rn = (len(groups) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rn * (cell // 2 + 16)), (245, 245, 245))
    dr = ImageDraw.Draw(img)
    cache = {}
    for k, g in enumerate(groups):
        r = rows[g[0]]; key = (r["v"], r["p"])
        if key not in cache:
            d = pymupdf.open(os.path.join(SRC, f"m {r['v']:02d} Qraan nos .pdf"))
            pix = d[r["p"] - 1].get_pixmap(matrix=pymupdf.Matrix(6, 6),
                                            clip=pymupdf.Rect(HX0, HY0, HX1, HY1),
                                            alpha=False, colorspace=pymupdf.csRGB)
            cache[key] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            d.close()
        t = cache[key].resize((cell, cell // 2), Image.LANCZOS)
        x = (k % cols) * cell; y = (k // cols) * (cell // 2 + 16)
        img.paste(t, (x, y + 15))
        dr.text((x + 3, y + 2), f"C{k} v{r['v']}p{r['p']} n{len(g)}", fill=(0, 0, 0))
    out = os.path.join(WORK, "header_sheet.png")
    img.save(out)
    print("sheet ->", out)


if __name__ == "__main__":
    main()