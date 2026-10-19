"""
medstats.py — يستخرج زخارف أرقام الآيات من كل صفحة ويحفظها في work/meds_all.pkl

كل سجل:  { v: رقم المجلد, p: رقم الصفحة داخل المجلد, meds: [(x,y,w,h,fill), ...] }

الصفحات المشمولة:
  - المجلد 1 من الصفحة 6 فما بعد (قبلها مقدّمة)
  - المجلد 20 الصفحة 1 فقط (وهي الصفحة الأخيرة ٦٠٤ من المصحف)
  - باقي صفحات المجلد 20 مقدّمة وفهرس (تُستبعد)

    python tools/medstats.py
"""
import argparse, glob, json, os, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pymupdf
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"

DET_Z = 4
PAGE_W, PAGE_H = 488.976, 701.575


def include(v, p):
    """هل الصفحة p (1-based) من المجلد v جزء من نصّ المصحف؟"""
    if v == 1:
        return p >= 6
    if v == 20:
        return p == 1
    return True


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
    doc = pymupdf.open(path)
    res = []
    for pno in range(doc.page_count):
        p1 = pno + 1
        if not include(vol, p1):
            res.append(dict(v=vol, p=p1, meds=[]))
            continue
        for attempt in range(3):
            try:
                a = page_rgb(doc[pno])
                h = all_hits(a)
                del a
                break
            except MemoryError:
                time.sleep(2)
        else:
            h = []
        res.append(dict(v=vol, p=p1, meds=h))
    doc.close()
    return vol, res


def main():
    os.makedirs(WORK, exist_ok=True)
    # ملفات المصحف هي الـ 20 Kronzen المرقّمة فقط، ونستبعد أي كتاب آخر بالمجلد
    def vnum(path):
        import re
        m = re.search(r"m\s+(\d+)\s+Qraan", os.path.basename(path))
        return int(m.group(1)) if m else None

    found = {}
    for f in glob.glob(os.path.join(SRC, "*.pdf")):
        n = vnum(f)
        if n is not None:
            found[n] = f
    jobs = [(found[n], n) for n in sorted(found)]
    if not jobs:
        sys.exit(f"no mushaf PDFs in {SRC}")
    print(f"mushaf volumes: {len(jobs)}")
    if len(jobs) != 20:
        print(f"WARNING: expected 20 volumes, found {sorted(found)}")
    results = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(work, j): j for j in jobs}
        for fu in as_completed(futs):
            job, (vol, res) = futs[fu], fu.result()
            if vol in results:
                raise SystemExit(f"duplicate volume {vol}")
            npages = len(pymupdf.open(job[0]))
            if len(res) != npages:
                raise SystemExit(f"volume {vol}: expected {npages} pages, got {len(res)}")
            results[vol] = res
            print(f"  volume {vol:2d} done ({time.time()-t0:.0f}s)", flush=True)

    missing = [v for _, v in jobs if v not in results]
    if missing:
        raise SystemExit(f"missing volumes: {missing}")

    pages = []
    for v in sorted(results):
        pages.extend(results[v])
    expected = sum(1 for r in pages if any(m["meds"] or True for m in [r]) and include(r["v"], r["p"]))
    print(f"total records: {len(pages)}  included: {expected}")
    pickle.dump(pages, open(os.path.join(WORK, "meds_all.pkl"), "wb"))

    text = [r for r in pages if include(r["v"], r["p"])]
    W = np.array([m[2] for pg in text for m in pg["meds"]])
    H = np.array([m[3] for pg in text for m in pg["meds"]])
    F = np.array([m[4] for pg in text for m in pg["meds"]])
    print("candidates:", len(W))
    for name, arr in (("w", W), ("h", H), ("fill", F)):
        print("  %-5s p5 %.3f med %.3f p95 %.3f" %
              (name, np.percentile(arr, 5), np.median(arr), np.percentile(arr, 95)))
    for wlo, whi, hlo, hhi, flo, fhi in [
        (21.0, 25.0, 25.0, 29.5, 0.24, 0.34),
        (21.0, 25.0, 25.0, 29.5, 0.22, 0.36),
    ]:
        tot = sum(1 for pg in text for m in pg["meds"]
                  if wlo <= m[2] <= whi and hlo <= m[3] <= hhi and flo <= m[4] <= fhi)
        print("  w[%.1f,%.1f] h[%.1f,%.1f] f[%.2f,%.2f] -> %d" % (wlo, whi, hlo, hhi, flo, fhi, tot))


if __name__ == "__main__":
    main()