"""
align_layout.py — يطابق صفحات المصحف (بترتيبها) مع توزيع الآيات القياسي (٦٠٤ صفحة)
باستخدام محاذاة ديناميكية تحترم تسلسل الآيات.

    python tools/align_layout.py
"""
import glob, json, os, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")

BIG = 1e9


def load():
    layout = {int(k): v for k, v in json.load(open(os.path.join(WORK, "std_layout.json"))).items()}
    rows = pickle.load(open(os.path.join(WORK, "meds.pkl"), "rb"))
    pages = []
    for r in rows:
        if r["v"] == 1 and r["p"] < 6:
            continue
        if r["v"] >= 20:
            continue
        pages.append(dict(v=r["v"], p=r["p"], n=len(r["meds"]), meds=r["meds"]))
    return layout, pages


def cost(i, sp, layout, n):
    """تكلفة مطابقة صفحة المصحف i بالصفحة القياسية sp"""
    ay = layout.get(sp)
    if not ay:
        return BIG
    c = abs(len(ay) - n) * 1.0
    return c


def align(layout, pages):
    N = len(pages)
    M = max(layout)
    INF = float("inf")
    # prev[sp] = أقل تكلفة للوصول للصفحة sp بعد معالجة i-1
    dp = {}
    for sp in range(1, min(M, N + 6) + 1):
        dp[sp] = cost(0, sp, layout, pages[0]["n"])
    back = []
    for i in range(1, N):
        ndp = {}
        bk = {}
        for sp in range(1, min(M, N + 6) + 1):
            c = cost(i, sp, layout, pages[i]["n"])
            if c >= INF:
                continue
            best, bp = INF, None
            for psp, v in dp.items():
                if psp >= sp:
                    continue
                gap = sp - psp - 1
                t = v + c + 120.0 * gap        # كلفة القفز/skipped صفحات
                if t < best:
                    best, bp = t, psp
            if bp is not None:
                ndp[sp] = best; bk[sp] = bp
        dp = ndp; back.append(bk)
        if not dp:
            break
    end = min(dp, key=lambda k: dp[k]) if dp else None
    if end is None:
        raise SystemExit("alignment failed")
    seq = [end]
    for bk in reversed(back):
        end = bk.get(end)
        if end is None:
            break
        seq.append(end)
    return list(reversed(seq))


def main():
    layout, pages = load()
    N, M = len(pages), max(layout)
    print("mushaf pages:", N, " std pages:", M)
    seq = align(layout, pages)
    print("aligned", len(seq), "pages; first std page:", seq[0], "last:", seq[-1])

    # تقرير الجودة
    exact = sum(1 for i, sp in enumerate(seq) if len(layout.get(sp, [])) == pages[i]["n"])
    print("count-exact match: %d/%d (%.1f%%)" % (exact, len(seq), 100.0 * exact / max(1, len(seq))))

    # فجوات
    gaps = [(i, seq[i], seq[i + 1]) for i in range(len(seq) - 1) if seq[i + 1] - seq[i] != 1]
    print("gaps:", gaps[:20], "count:", len(gaps))
    # انقلاب في ترتيب الآيات
    bad = 0
    for i in range(len(seq) - 1):
        a = layout[seq[i]][-1]; b = layout[seq[i + 1]][0]
        if not (b[0] > a[0] or (b[0] == a[0] and b[1] == a[1] + 1)):
            bad += 1
    print("non-contiguous joins:", bad)

    out = []
    for i, sp in enumerate(seq):
        ay = layout[sp]
        s, a1 = ay[0]; _, a2 = ay[-1]
        out.append(dict(i=i, v=pages[i]["v"], p=pages[i]["p"], sp=sp,
                        s=s, a1=a1, a2=a2,
                        meds=[[round(m[0], 5), round(m[1], 5)] for m in pages[i]["meds"]]))
    json.dump(dict(total=len(out), source="aligned-604", pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json:", len(out), "pages")
    print("first:", out[0]["s"], out[0]["a1"], " last:", out[-1]["s"], out[-1]["a2"])
    for k in range(1, 115):
        st = next((o for o in out if o["s"] == k), None)
        if st:
            pass
    print("surah start pages:", {k: [o["i"] + 1 for o in out if o["s"] == k][:1] for k in range(1, 8)})


if __name__ == "__main__":
    main()