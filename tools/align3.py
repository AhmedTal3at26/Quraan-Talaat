"""
align3.py — محاذاة ديناميكية كاملة لصفحات المصحف مع توزيع الآيات القياسي.

المصحف يكثّف أكثر قليلًا من التوزيع القياسي، فيزاح الترقيم تدريجيًا.
نبحث عن تسلسل رتيب (strictly increasing) يربط ٦٠٣ صفحة بصفحات ١..٦٠٤
مع أقل كلفة، مثبَّتًا على الطرفين.

    python tools/align3.py
"""
import json, os, pickle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")
INF = float("inf")


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


def dp_align(layout, pages, skip_pen, weight, last):
    N, M = len(pages), max(layout)
    dp = {}
    for sp in range(1, 8):
        dp[sp] = weight * abs(len(layout[sp]) - pages[0]["n"])
    backs = []
    for i in range(1, N):
        hi = min(M, (i + 1) * 3)
        ndp, bk = {}, {}
        for sp in range(1, hi + 1):
            c = weight * abs(len(layout[sp]) - pages[i]["n"])
            best, bp = INF, None
            for psp, val in dp.items():
                if psp >= sp:
                    continue
                t = val + c + skip_pen * (sp - psp - 1)
                if t < best:
                    best, bp = t, psp
            if bp is not None:
                ndp[sp] = best; bk[sp] = bp
        if not ndp:
            return None
        dp = ndp; backs.append(bk)
    end = min((k for k in dp if k == last), default=None)
    if end is None:
        return None
    seq = [end]
    for bk in reversed(backs):
        end = bk[end]; seq.append(end)
    return list(reversed(seq))


def main():
    layout, pages = load()
    N, M = len(pages), max(layout)
    print("mushaf pages:", N, "std:", M)
    best = None
    for sp in [5, 8, 12, 16, 20, 25, 30]:
        for w in [1.0, 2.0]:
            seq = dp_align(layout, pages, sp, w, M)
            if not seq:
                continue
            exact = sum(1 for i, s in enumerate(seq) if len(layout[s]) == pages[i]["n"])
            cont = 0
            for i in range(len(seq) - 1):
                a = layout[seq[i]][-1]; b = layout[seq[i + 1]][0]
                if b[0] > a[0] or (b[0] == a[0] and b[1] == a[1] + 1):
                    cont += 1
            total_err = sum(abs(len(layout[s]) - pages[i]["n"]) for i, s in enumerate(seq))
            print("skip_pen=%-4s w=%.0f  exact=%3d(%.0f%%) contig=%d  err=%d" %
                  (sp, w, exact, 100.0 * exact / N, cont, total_err))
            key = (cont, -total_err)
            if best is None or key > best[0]:
                best = (key, seq, sp, w, exact, total_err)
    if not best:
        raise SystemExit("no alignment")
    _, seq, sp_pen, w, exact, err = best
    print("\nchosen skip_pen=%s w=%.0f exact=%d err=%d" % (sp_pen, w, exact, err))
    print("first std page:", seq[0], "last:", seq[-1])
    print("first ayah:", layout[seq[0]][0], " last ayah:", layout[seq[-1]][-1])
    json.dump(seq, open(os.path.join(WORK, "aligned_seq.json"), "w"))

    out = []
    for i, s in enumerate(seq):
        ay = layout[s]
        st, a1 = ay[0]; _, a2 = ay[-1]
        out.append(dict(i=i, v=pages[i]["v"], p=pages[i]["p"], sp=s, s=st, a1=a1, a2=a2,
                        meds=[[round(m[0], 5), round(m[1], 5)] for m in pages[i]["meds"]]))
    json.dump(dict(total=len(out), source="aligned-604", pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json", len(out))
    starts = {}
    for o in out:
        starts.setdefault(o["s"], []).append(o["i"])
    print("surahs covered:", len(starts))
    print({k: starts[k][0] + 1 for k in sorted(starts)[:12]})


if __name__ == "__main__":
    main()