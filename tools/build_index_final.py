"""
build_index_final.py — يبني الفهرس النهائي من زخارف الآيات المرصودة.

الزخرفة تظهر مرة واحدة لكل آية، وعدّها على كل الصفحات يعطي عدد آيات الصفحة.
بجمعها تسلسليًا نحصل على خريطة (سورة، آية) لكل صفحة، مع تصحيح الانزياح
ليطابق المجموع الكلي ٦٢٣٦ آية.

    python tools/build_index_final.py
"""
import json, os, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")

def include(v, p):
    """صفحات نصّ المصحف: 1:6+ ، 20:1 فقط"""
    if v == 1: return p >= 6
    if v == 20: return p == 1
    return True


# نافذة الكشف الضيقة (الذروة عند عرض ٢٢٫٧٥ وارتفاع ٢٧٫٢٥)
W_LO, W_HI = 21.0, 25.0
H_LO, H_HI = 25.0, 29.5
F_LO, F_HI = 0.24, 0.34


def load_pages():
    rows = pickle.load(open(os.path.join(WORK, "meds_all.pkl"), "rb"))
    out = []
    for r in rows:
        if not include(r["v"], r["p"]):
            continue
        meds = [m for m in r["meds"] if W_LO <= m[2] <= W_HI and H_LO <= m[3] <= H_HI
                and F_LO <= m[4] <= F_HI]
        out.append(dict(v=r["v"], p=r["p"], meds=[[m[0], m[1]] for m in meds]))
    return out


def build():
    pages = load_pages()
    total_ayah = 6236
    detected = sum(len(p["meds"]) for p in pages)
    print("text pages:", len(pages), " detected markers:", detected, " expected:", total_ayah)

    # تصحيح الانزياح: نعلى التوزيع التراكمي على الإجمالي الصحيح
    prefix, acc = [], 0
    for p in pages:
        acc += len(p["meds"])
        prefix.append(acc)
    k = total_ayah / detected
    cum = [int(round(x * k)) for x in prefix]
    # ضمان التدرج
    for i in range(1, len(cum)):
        if cum[i] <= cum[i - 1]:
            cum[i] = cum[i - 1] + 1
    cum[-1] = total_ayah

    counts = json.load(open(os.path.join(DATA, "surahs.json"), encoding="utf-8"))
    scounts = [s["numberOfAyahs"] for s in counts]
    starts, t = {}, 1
    for n in range(1, 115):
        starts[n] = t
        t += scounts[n - 1]

    def to_sa(g):
        """رقم الآية العام -> (سورة، آية)"""
        lo, hi = 1, 114
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= g:
                lo = mid
            else:
                hi = mid - 1
        return lo, g - starts[lo] + 1

    out = []
    prev = 0
    for i, p in enumerate(pages):
        g1 = prev + 1
        g2 = cum[i]
        prev = g2
        s1, a1 = to_sa(g1)
        out.append(dict(i=i, v=p["v"], p=p["p"], g=g1, s=s1, a=a1,
                        n=g2 - g1 + 1, meds=p["meds"]))
    json.dump(dict(total=len(out), source="medallion-walk-v1", pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json:", len(out), "pages")
    print("first:", out[0]["s"], out[0]["a"], "-", out[0]["a"] + out[0]["n"] - 1)
    print("last :", out[-1]["s"], out[-1]["a"], "-", out[-1]["a"] + out[-1]["n"] - 1)

    sur = {}
    for o in out:
        sur.setdefault(o["s"], []).append(o)
    print("pages whose first ayah is in surah X (count):", len(sur))
    # تحقق: صفحة بداية كل سورة = الصفحة التي تقع فيها آية ١
    print("\nsurah -> page ( ayah 1 ):")
    starts_map = {}
    for n in range(1, 115):
        g = starts[n]
        pg = next(o for o in out if o["g"] <= g <= o["g"] + o["n"] - 1)
        starts_map[n] = pg["i"]
        if n in (1, 2, 3, 4, 5, 6, 7, 8, 18, 36, 55, 78, 112, 114):
            print("   surah %3d -> index %4d (v%d p%d)  [%d..%d]" %
                  (n, pg["i"] + 1, pg["v"], pg["p"], pg["g"], pg["g"] + pg["n"] - 1))
    json.dump(starts_map, open(os.path.join(WORK, "surah_page.json"), "w"), indent=0)


if __name__ == "__main__":
    build()