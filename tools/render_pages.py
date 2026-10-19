"""
render_pages.py — يحوّل صفحات المصحف إلى صور WebP للعرض السريع في الموقع.

  pages/####.webp   : 2.5×  (1222×1754) — للعرض والتكبير
  thumbs/####.webp  : 0.35× — للمصغّرات

    python tools/render_pages.py --workers 4 --scale 2.5
"""
import argparse, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
MUSH = os.path.join(ROOT, "assets", "mushaf")
OUT_PAGES = os.path.join(ROOT, "pages")
OUT_THUMBS = os.path.join(ROOT, "thumbs")

import json, pickle
WORK = os.path.join(HERE, "work")


def render_job(job):
    idx, pdf, page, scale, kind = job
    dst_dir = OUT_PAGES if kind == "page" else OUT_THUMBS
    out = os.path.join(dst_dir, "%04d.webp" % (idx + 1))
    tmp = os.path.join(dst_dir, "t%04d_%s.png" % (idx + 1, kind))
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return idx, kind, -1, os.path.getsize(out)
    try:
        doc = pymupdf.open(pdf)
        pix = doc[page].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        pix.save(tmp)
        doc.close()
        from PIL import Image
        im = Image.open(tmp).convert("RGB")
        im.save(out, "WEBP", quality=(82 if kind == "page" else 70), method=4)
        im.close()
        try: os.remove(tmp)
        except OSError: pass
        return idx, kind, os.path.getsize(out), os.path.getsize(out)
    except Exception as e:
        return idx, kind, -1, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--scale", type=float, default=2.5)
    ap.add_argument("--thumb-scale", type=float, default=0.36)
    args = ap.parse_args()

    os.makedirs(OUT_PAGES, exist_ok=True)
    os.makedirs(OUT_THUMBS, exist_ok=True)

    rows = pickle.load(open(os.path.join(WORK, "meds_all.pkl"), "rb"))
    jobs = []
    idx = 0
    for r in rows:
        if not (r["v"] == 1 and r["p"] < 6) and not (r["v"] == 20 and r["p"] > 1):
            pass
        else:
            continue
        pdf = os.path.join(MUSH, "m %02d Qraan nos .pdf" % r["v"])
        jobs.append((idx, pdf, r["p"] - 1, args.scale, "page"))
        jobs.append((idx, pdf, r["p"] - 1, args.thumb_scale, "thumb"))
        idx += 1
    print("pages:", idx, " jobs:", len(jobs))

    t0 = time.time()
    done = 0
    total_bytes = 0
    errors = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(render_job, j) for j in jobs]
        for fu in as_completed(futs):
            pidx, kind, size, extra = fu.result()
            done += 1
            if size < 0:
                if not isinstance(extra, int):
                    errors.append((pidx, kind, extra))
            else:
                total_bytes += extra
            if done % 120 == 0:
                print("  %d/%d  %.0fs  %.1f MB" %
                      (done, len(jobs), time.time() - t0, total_bytes / 1e6), flush=True)
    print("done in %.0fs, total %.1f MB" % (time.time() - t0, total_bytes / 1e6))
    if errors:
        print("errors:", errors[:10], "count", len(errors))
    for d in (OUT_PAGES, OUT_THUMBS):
        n = len([f for f in os.listdir(d) if f.endswith(".webp")])
        print(os.path.basename(d), n, "files")


if __name__ == "__main__":
    main()