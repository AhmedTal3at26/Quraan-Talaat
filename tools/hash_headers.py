"""
hash_headers.py — يستخرج خانة اسم السورة من أعلى يسار كل صفحة ويجميعها بالهاش.

نفس اسم السورة يُرسم بشكل متطابق تمامًا في كل صفحاتها، لذا التجميع بالهاش
يعطي_boundary الصفحة الأولى لكل سورة بدقة تامة.

    python tools/hash_headers.py
"""
import glob, hashlib, json, os, pickle, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"

# surah-name cartouche (fixed-size frame) in pt, measured from page renders
HX0, HY0, HX1, HY1 = 75, 33, 143, 63
HZ = 4


def work(job):
    path, vol = job
    doc = pymupdf.open(path)
    out = []
    for pno in range(doc.page_count):
        pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(HZ, HZ),
                                  clip=pymupdf.Rect(HX0, HY0, HX1, HY1),
                                  alpha=False, colorspace=pymupdf.csGRAY)
        a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride // pix.n)[:, :pix.width]
        ink = int((a < 128).sum())
        h = hashlib.sha1(np.packbits(a < 128).tobytes()).hexdigest()[:16]
        out.append(dict(v=vol, p=pno + 1, h=h, ink=ink))
    doc.close()
    return vol, out


def main():
    os.makedirs(WORK, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC, "*.pdf")))
    res = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(work, (f, i + 1)) for i, f in enumerate(files)]):
            v, rows = fu.result(); res[v] = rows
            print("vol %2d ok (%.0fs)" % (v, time.time() - t0), flush=True)

    rows = []
    for v in sorted(res): rows += res[v]
    pickle.dump(rows, open(os.path.join(WORK, "headers.pkl"), "wb"))

    counts = {}
    for r in rows: counts.setdefault(r["h"], []).append(r)
    print("\ndistinct header hashes:", len(counts))
    ink0 = sum(1 for r in rows if r["ink"] == 0)
    print("pages with no header ink:", ink0)
    sizes = sorted((len(v), k) for k, v in counts.items())[::-1]
    print("largest groups:", sizes[:12])
    json.dump({k: [dict(v=x["v"], p=x["p"]) for x in v] for k, v in counts.items()},
              open(os.path.join(WORK, "header_groups.json"), "w"), indent=0)
    print("saved tools/work/headers.pkl")


if __name__ == "__main__":
    main()