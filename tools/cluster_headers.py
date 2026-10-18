"""
cluster_headers.py — يستخرج توقيعًا بصريًا لخانة اسم السورة في كل صفحة.

الخانة تتحرك يمينًا/يسارًا حسب زوجية رقم الصفحة (وجه/ظهر)، لذا نستخدم
مربعين: أحدهما للصفحات الفردية والآخر للزوجية.

    python tools/cluster_headers.py
"""
import glob, os, pickle, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np, pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
SRC = r"D:\My Projects\Religion\Dad's Quraan"

BOX_ODD = (82, 42, 134, 58)     # printed page odd
BOX_EVEN = (112, 42, 164, 58)    # printed page even
HZ = 8
NW, NH = 104, 32


def printed_no(v, p):
    """مطبوع رقم الصفحة؛ v1 تبدأ من الصفحة 6."""
    if v == 1: return p - 5
    return 27 + (v - 2) * 32 + p


def sig_of(page, box):
    """توقيع ثنائي بدقة كاملة: صفحات السورة الواحدة متطابقة تمامًا (تشابه = 1)."""
    pix = page.get_pixmap(matrix=pymupdf.Matrix(HZ, HZ), clip=pymupdf.Rect(*box),
                          alpha=False, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride // pix.n)[:, :pix.width]
    return (a > 150).astype(np.float32).ravel()


def work(job):
    path, vol = job
    doc = pymupdf.open(path)
    out = []
    for pno in range(doc.page_count):
        pr = printed_no(vol, pno + 1)
        box = BOX_ODD if pr % 2 == 1 else BOX_EVEN
        try:
            s = sig_of(doc[pno], box)
        except Exception:
            s = None
        out.append(dict(v=vol, p=pno + 1, pr=pr, sig=None if s is None else s.astype(np.float32)))
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
    rows = []
    for v in sorted(res): rows += res[v]
    print("pages:", len(rows), "with signature:", sum(1 for r in rows if r["sig"] is not None),
          "(%.0fs)" % (time.time() - t0))
    # hash of the exact ink bitmap, per parity -> pages of one surah share it
    import hashlib
    for r in rows:
        if r["sig"] is not None:
            r["hash"] = hashlib.sha1(r["sig"].astype(np.uint8).tobytes()).hexdigest()[:16]
        else:
            r["hash"] = None
    pickle.dump(dict(rows=rows), open(os.path.join(WORK, "header_sigs.pkl"), "wb"))
    print("saved tools/work/header_sigs.pkl")


if __name__ == "__main__":
    main()