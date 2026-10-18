"""
fetch_layout.py — يجلب توزيع الآيات على صفحات المصحف القياسي (٦٠٤ صفحة)
                  ثم يطابقه بصفحات المصحف المستخرجة (كشف زخارف الآيات).

المصدر: api.alquran.cloud  →  604 صفحة (رواية حفص).
الناتج: data/mushaf-index.json
"""
import glob, json, os, pickle, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")


def get_page(n):
    url = f"https://api.alquran.cloud/v1/page/{n}/quran-uthmani"
    for _ in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read().decode("utf-8"))
            ayahs = d["data"]["ayahs"]
            return n, [(a["surah"]["number"], a["numberInSurah"]) for a in ayahs]
        except Exception:
            time.sleep(1.5)
    return n, []


def fetch_layout(total=604):
    cache = os.path.join(WORK, "std_layout.json")
    if os.path.exists(cache):
        return {int(k): v for k, v in json.load(open(cache)).items()}
    out = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for fu in as_completed([ex.submit(get_page, i) for i in range(1, total + 1)]):
            n, a = fu.result(); out[n] = a
            if n % 100 == 0:
                print("  page", n, "(%.0fs)" % (time.time() - t0), flush=True)
    json.dump({str(k): v for k, v in out.items()}, open(cache, "w"))
    print("fetched", len(out), "pages")
    return out


def mushaf_pages():
    """صفحات المصحف بالترتيب مع الزخارف المرصودة"""
    rows = pickle.load(open(os.path.join(WORK, "meds.pkl"), "rb"))
    pages = []
    for r in rows:
        if r["v"] == 1 and r["p"] < 6:
            continue
        if r["v"] >= 20:
            continue
        pages.append(dict(v=r["v"], p=r["p"], n=len(r["meds"]), meds=r["meds"]))
    return pages


def main():
    os.makedirs(WORK, exist_ok=True)
    layout = fetch_layout()
    pages = mushaf_pages()
    print("mushaf text pages:", len(pages), " std pages:", len(layout))

    # ---- مطابقة: نجرّب إزاحة لكل صفحة ثم نختار أفضل تطابق عبر الصفحة كاملة
    best_off, best_score = 0, -1
    for off in range(-4, 5):
        score = 0; tot = 0
        for i, pg in enumerate(pages):
            sp = i + 1 + off
            if 1 <= sp <= len(layout):
                score += 1 if len(layout[sp]) == pg["n"] else 0
                tot += 1
        if tot and score / tot > best_score:
            best_off, best_score = off, score / tot
    print("best offset:", best_off, "match ratio: %.3f" % best_score)

    # ---- محاذاة ديناميكية للصفحات (بعدها قد ينزلق الترقيم)
    seq = [i + 1 for i in range(len(pages))]
    out = []
    off = 0
    for i, pg in enumerate(pages):
        sp = seq[i] = i + 1 + off
        if sp < 1 or sp > len(layout):
            out.append(None); continue
        ay = layout[sp]
        s = ay[0]
        e = ay[-1]
        out.append(dict(i=i, v=pg["v"], p=pg["p"], sp=sp,
                        s=s[0], a1=s[1], a2=e[1],
                        meds=[[m[0], m[1]] for m in pg["meds"]]))
    json.dump(dict(total=len(out), source="aligned-medina-604", pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json with", len(out), "pages")
    if out and out[-1]:
        print("last page maps to surah", out[-1]["s"], "ayah", out[-1]["a2"])


if __name__ == "__main__":
    main()