"""
medstats.py — يجمع إحصاءات زخارف الآيات (العرض/الارتفاع/الكثافة) لكل الصفحات
              لاختيار أدق عتبة للكشف، ثم يعيد الكشف ويطبع الإجمالي.

    python tools/medstats.py --tight
"""
import argparse, glob, json, os, pickle, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pymupdf
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"
DET_Z = 4
PAGE_W, PAGE_H = 488.976, 701.575


def page_rgb(p, zoom=DET_Z):
    pix = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False, colorspace=pymupdf.csRGB)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride // pix.n, pix.n)
    return a[:, :pix.width, :3]


def all_hits(arr):
    dark = arr.min(axis=2) < 200
    lab, n = ndimage.label(dark, np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = np.array(ndimage.sum(dark, lab, range(1, n + 1)), dtype=np.int64)
    out = []
    for i, sl in enumerate(objs, 1):
        ys, xs = sl
        w = (xs.stop - xs.start) / DET_Z; h = (ys.stop - ys.start) / DET_Z
        if not (18.0 <= w <= 28.0 and 22.0 <= h <= 32.0):
            continue
        ar = sizes[i - 1] / ((xs.stop - xs.start) * (ys.stop - ys.start))
        if not (0.15 <= ar <= 0.45):
            continue
        cx = (xs.start + xs.stop) / 2 / DET_Z; cy = (ys.start + ys.stop) / 2 / DET_Z
        if not (60 <= cx <= PAGE_W - 4 and 58 <= cy <= PAGE_H - 56):
            continue
        out.append((round(cx / PAGE_W, 5), round(cy / PAGE_H, 5), round(w, 2), round(h, 2), round(ar, 3)))
    out.sort(key=lambda t: t[1])
    return out


def work(job):
    path, vol = job
    for _ in range(3):
        try:
            doc = pymupdf.open(path)
            res = []
            for pno in range(doc.page_count):
                if vol == 20:
                    res.append([]); continue
                if vol == 1 and pno < 5:
                    res.append([]); continue
                a = page_rgb(doc[pno])
                h = all_hits(a)
                del a
                res.append(h)
            doc.close()
            return vol, res
        except MemoryError:
            time.sleep(2)
    return vol, []


def main():
    ap = argparse.ArgumentParser()
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(SRC, "*.pdf")))
    out = {}
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(work, (f, i + 1)): i + 1 for i, f in enumerate(files)}
        for fu in as_completed(futs):
            v, res = fu.result(); out[v] = res
    pages = []
    for v in sorted(out):
        for i, h in enumerate(out[v]):
            pages.append(dict(v=v, p=i + 1, meds=h))
    pickle.dump(pages, open(os.path.join(WORK, "meds_all.pkl"), "wb"))

    W = np.array([m[2] for pg in pages for m in pg["meds"]])
    H = np.array([m[3] for pg in pages for m in pg["meds"]])
    F = np.array([m[4] for pg in pages for m in pg["meds"]])
    print("candidates:", len(W))
    for name, arr in (("w", W), ("h", H), ("fill", F)):
        print("  %-5s min %.3f p1 %.3f p5 %.3f p25 %.3f med %.3f p95 %.3f max %.3f" %
              (name, arr.min(), np.percentile(arr,1), np.percentile(arr,5), np.percentile(arr,25),
               np.median(arr), np.percentile(arr,95), arr.max()))
    # histogram of w
    h, e = np.histogram(W, bins=24, range=(18, 28))
    print("  w hist:", " ".join("%.1f:%d" % (e[k], h[k]) for k in range(24)))
    h, e = np.histogram(H, bins=24, range=(22, 32))
    print("  h hist:", " ".join("%.1f:%d" % (e[k], h[k]) for k in range(24)))

    # tight filter sweep
    for wlo, whi, hlo, hhi, flo, fhi in [
        (21.0, 25.0, 25.0, 29.5, 0.24, 0.34),
        (21.5, 24.5, 25.5, 29.0, 0.25, 0.33),
        (22.0, 24.0, 26.0, 28.5, 0.26, 0.32),
        (21.0, 25.0, 25.0, 29.5, 0.22, 0.36),
    ]:
        tot = sum(1 for pg in pages for m in pg["meds"]
                  if wlo <= m[2] <= whi and hlo <= m[3] <= hhi and flo <= m[4] <= fhi)
        print("  w[%.1f,%.1f] h[%.1f,%.1f] f[%.2f,%.2f] -> %d" % (wlo, whi, hlo, hhi, flo, fhi, tot))


if __name__ == "__main__":
    main()