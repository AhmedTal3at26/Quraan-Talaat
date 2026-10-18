"""
count_meds.py — عدّ زخارف أرقام الآيات في كل صفحة والتحقق من الإجمالي.

    python tools/count_meds.py
"""
import glob, json, os, pickle, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pymupdf
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"

DET_Z = 4
PAGE_W, PAGE_H = 488.976, 701.575


def detect(arr):
    dark = arr.min(axis=2) < 200
    lab, n = ndimage.label(dark, np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = np.array(ndimage.sum(dark, lab, range(1, n + 1)), dtype=np.int32)
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
        if not (60 <= cx <= PAGE_W - 4 and 58 <= cy <= PAGE_H - 56):
            continue
        out.append((round(cx / PAGE_W, 5), round(cy / PAGE_H, 5)))
    out.sort(key=lambda t: t[1])
    return out


def work(job):
    path, vol = job
    for attempt in range(3):
        try:
            doc = pymupdf.open(path)
            pages = []
            for pno in range(doc.page_count):
                pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(DET_Z, DET_Z),
                                          alpha=False, colorspace=pymupdf.csRGB)
                a = np.frombuffer(pix.samples, np.uint8).reshape(
                    pix.height, pix.stride // pix.n, pix.n)[:, :pix.width, :3]
                meds = detect(a)
                del a, pix
                pages.append(dict(v=vol, p=pno + 1, meds=meds))
            doc.close()
            return vol, pages
        except MemoryError:
            time.sleep(3)
    return vol, []


def main():
    os.makedirs(WORK, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, "*.pdf")))
    jobs = [(f, i + 1) for i, f in enumerate(files)]
    res = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=4) as ex:
        for fu in as_completed([ex.submit(work, j) for j in jobs]):
            v, pages = fu.result()
            res[v] = pages
            print("vol %2d: %3d pages, %4d medallions  (%ds)" %
                  (v, len(pages), sum(len(p["meds"]) for p in pages), time.time() - t0), flush=True)

    pages = []
    for v in sorted(res):
        pages += res[v]
    total = sum(len(p["meds"]) for p in pages)
    empty = [p for p in pages if not p["meds"]]
    print("\nTOTAL medallions:", total, " (expected ~6236 ayat)")
    print("pages without medallions:", len(empty))
    for p in empty:
        print("   v%d p%d" % (p["v"], p["p"]))

    pickle.dump(pages, open(os.path.join(WORK, "meds.pkl"), "wb"))
    json.dump([dict(v=p["v"], p=p["p"], n=len(p["meds"])) for p in pages],
              open(os.path.join(WORK, "meds_count.json"), "w"), indent=0)
    print("saved tools/work/meds.pkl")


if __name__ == "__main__":
    main()