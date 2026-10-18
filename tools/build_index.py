"""
build_index.py — يبني فهرس الصفحات للمصحف من ملفات PDF.

 1) كشف زخارف أرقام الآيات (rosette) في كل صفحة بالتوقيع الهندسي.
 2) قصّ أرقام الآية داخل كل زخرفة (ب clips صغيرة) وتجميعها في عناقيد.
 3) وسم العناقيد (٠..٩) مرة واحدة، ثم فكّ ترميز كل الأرقام.
 4) مشي تسلسلي على الصفحات لبناء خريطة (سورة، آية) لكل صفحة.
 5) كتابة data/mushaf-index.json

    python tools/build_index.py
    python tools/build_index.py --workers 6
"""
import argparse, glob, json, os, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pymupdf
from scipy import ndimage
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")

DET_Z = 4        # px/pt, medallion geometry
GLY_Z = 8        # px/pt, digit crops (clipped)
NORM = 28
PAGE_W, PAGE_H = 488.976, 701.575


# ───────────────────────────────────────────── medallion detection
def page_gray(p, zoom, clip=None):
    pix = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip,
                       alpha=False, colorspace=pymupdf.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride // pix.n)[:, :pix.width]


def detect_medallions(arr, page_w, page_h):
    dark = arr.min(axis=2) < 200
    lab, n = ndimage.label(dark, np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = np.array(ndimage.sum(dark, lab, range(1, n + 1)), dtype=float)
    out = []
    for i, sl in enumerate(objs, 1):
        ys, xs = sl
        w = (xs.stop - xs.start) / DET_Z
        h = (ys.stop - ys.start) / DET_Z
        if not (20.0 <= w <= 26.0 and 24.5 <= h <= 30.0):
            continue
        area = sizes[i - 1] / ((xs.stop - xs.start) * (ys.stop - ys.start))
        if not (0.20 <= area <= 0.40):
            continue
        cx = (xs.start + xs.stop) / 2 / DET_Z
        cy = (ys.start + ys.stop) / 2 / DET_Z
        if not (60 <= cx <= page_w - 4 and 58 <= cy <= page_h - 56):
            continue
        out.append((cx, cy, w, h, float(area)))
    return out


# ───────────────────────────────────────────── digit crops
def medallion_digits(p, cx, cy, w, h):
    rect = pymupdf.Rect(cx - w * 0.30, cy - h * 0.26, cx + w * 0.30, cy + h * 0.26)
    g = page_gray(p, GLY_Z, clip=rect)
    dark = g < 120
    lab, n = ndimage.label(dark, np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = np.array(ndimage.sum(dark, lab, range(1, n + 1)), dtype=float)
    res = []
    for i, sl in enumerate(objs, 1):
        ys, xs = sl
        gw = xs.stop - xs.start; gh = ys.stop - ys.start
        if sizes[i - 1] < 30: continue
        if gh < 8 or gw < 4: continue
        if sizes[i - 1] / (gw * gh) < 0.15: continue
        if gw > 0.85 * dark.shape[1] and gh > 0.85 * dark.shape[0]: continue
        res.append(dict(gx=xs.start, gy=ys.start, w=gw, h=gh, size=float(sizes[i - 1])))
    res.sort(key=lambda d: d["gx"])          # left → right
    return g, res


def norm_glyph(crop):
    im = Image.fromarray(crop)
    w, h = im.size
    s = (NORM - 4) / max(w, h)
    nw, nh = max(3, int(round(w * s))), max(3, int(round(h * s)))
    a = np.array(im.resize((nw, nh), Image.LANCZOS))
    canvas = np.zeros((NORM, NORM), np.uint8)
    oy = (NORM - nh) // 2; ox = (NORM - nw) // 2
    canvas[oy:oy + nh, ox:ox + nw] = (a < 128).astype(np.uint8)
    return canvas


# ───────────────────────────────────────────── per-volume worker
def process_volume(job):
    path, vol = job
    doc = pymupdf.open(path)
    pages, samples = [], []
    for pno in range(doc.page_count):
        p = doc[pno]
        rec = dict(v=vol, p=pno + 1, meds=[])
        try:
            pix = p.get_pixmap(matrix=pymupdf.Matrix(DET_Z, DET_Z), alpha=False, colorspace=pymupdf.csRGB)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.stride // pix.n, pix.n)[:, :pix.width, :3]
            hits = detect_medallions(arr, PAGE_W, PAGE_H)
            del arr
            for cx, cy, w, h, _ in sorted(hits, key=lambda t: t[1]):
                g, glyphs = medallion_digits(p, cx, cy, w, h)
                d = dict(x=round(cx / PAGE_W, 5), y=round(cy / PAGE_H, 5), n=len(glyphs))
                for gi, gl in enumerate(glyphs):
                    crop = g[gl["gy"]:gl["gy"] + gl["h"], gl["gx"]:gl["gx"] + gl["w"]]
                    samples.append((vol, pno + 1, len(rec["meds"]), gi, float(gl["size"]), crop.tobytes(), crop.shape))
                d["order"] = list(range(len(glyphs)))
                rec["meds"].append(d)
        except Exception as e:
            rec["error"] = str(e)
        pages.append(rec)
    doc.close()
    return vol, pages, samples


# ───────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=r"D:\My Projects\Religion\Dad's Quraan")
    ap.add_argument("--workers", type=int, default=min(6, (os.cpu_count() or 4)))
    ap.add_argument("--only-detect", action="store_true")
    args = ap.parse_args()

    os.makedirs(WORK, exist_ok=True); os.makedirs(DATA, exist_ok=True)
    files = sorted(glob.glob(os.path.join(args.source, "*.pdf")))
    if not files: sys.exit(f"no PDFs in {args.source}")
    print(f"volumes: {len(files)}  workers: {args.workers}")

    jobs = [(f, i + 1) for i, f in enumerate(files)]
    results = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_volume, j): j[1] for j in jobs}
        for fu in as_completed(futs):
            vol, pages, samples = fu.result()
            results[vol] = (pages, samples)
            print(f"  volume {vol:2d} done  ({len(samples)} glyphs)  {time.time()-t0:.0f}s", flush=True)

    pages, samples = [], []
    for v in sorted(results):
        pages += results[v][0]; samples += results[v][1]
    errs = [p for p in pages if "error" in p]
    if errs: print(f"  !! {len(errs)} pages had errors, e.g. {errs[0]}")
    print(f"detect done: {len(pages)} pages, {len(samples)} glyphs, {time.time()-t0:.0f}s")

    keys = [norm_glyph(np.frombuffer(s[5], np.uint8).reshape(s[6])) for s in samples]
    flat = np.array(keys, np.float32).reshape(len(keys), -1)
    cents, assign = [], np.full(len(flat), -1, np.int32)
    for i in np.argsort([-s[4] for s in samples]):
        v = flat[i]; nv = np.linalg.norm(v) + 1e-9
        best, bi = -1, -1
        for j, c in enumerate(cents):
            sim = float((c * v).sum() / (np.linalg.norm(c) * nv))
            if sim > best: best, bi = sim, j
        if best >= 0.86:
            assign[i] = bi
            cents[bi] += v
            n = np.linalg.norm(cents[bi])
            if n: cents[bi] = cents[bi] / n
        else:
            cents.append(v / nv); assign[i] = len(cents) - 1
    counts = np.bincount(assign, minlength=len(cents))
    print(f"digit clusters: {len(cents)}  sizes={counts.tolist()}")

    # contact sheet for labelling
    cols = 10; rows = (len(cents) + cols - 1) // cols; cell = NORM * 2
    img = Image.new("L", (cols * cell, rows * (cell + 18)), 255)
    d = ImageDraw.Draw(img)
    for j in range(len(cents)):
        idx = int(np.where(assign == j)[0][0])
        r, c = j // cols, j % cols
        img.paste(Image.fromarray(((1 - keys[idx]) * 255).astype(np.uint8)).resize((cell, cell), Image.NEAREST),
                  (c * cell, r * (cell + 18) + 18))
        d.text((c * cell + 4, r * (cell + 18) + 3), f"C{j} ({counts[j]})", fill=0)
    sheet = os.path.join(WORK, "digit_clusters.png")
    img.save(sheet); print("  cluster sheet →", sheet)

    # attach cluster ids
    pos = 0
    for pg in pages:
        for m in pg["meds"]:
            m["d"] = [int(assign[pos + i]) for i in range(m["n"])]
            pos += m["n"]

    with open(os.path.join(WORK, "detect.pkl"), "wb") as f:
        pickle.dump(dict(pages=pages, nclusters=len(cents)), f)

    labels_file = os.path.join(WORK, "digit_labels.json")
    labels = {}
    if os.path.exists(labels_file):
        labels = {int(k): int(v) for k, v in json.load(open(labels_file, encoding="utf-8")).items()}
    if len(labels) == len(cents):
        walk(pages, labels)
    else:
        print(f"\n>>>.label {len(cents)} digit clusters in {labels_file} then re-run (or pass --labels-only)")


if __name__ == "__main__":
    main()