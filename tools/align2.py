"""
align2.py — يحدد موضع الانزلاق الواحد بين صفحات المصحف (٦٠٣) وتوزيع ٦٠٤ القياسي.

المصحف يتبع ترقيم المدينة القياسي،Lithug فقط صفحة واحدة أقل، فنبحث عن موضع
الصفحة «المزدوجة» التي تجمع ما توزيعه القياسية على صفحتين.

    python tools/align2.py
"""
import json, os, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")


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


def seq_for(k, N):
    """صفحة المصحف i -> صفحة قياسية i+1 قبل k، و i+2 من k"""
    return [i + 1 if i < k else i + 2 for i in range(N)]


def main():
    layout, pages = load()
    N = len(pages)
    best = []
    for k in range(0, N + 1):
        seq = seq_for(k, N)
        if seq[-1] > 604:
            continue
        score = sum(1 for i, sp in enumerate(seq) if len(layout[sp]) == pages[i]["n"])
        cont = 0
        for i in range(len(seq) - 1):
            a = layout[seq[i]][-1]; b = layout[seq[i + 1]][0]
            if b[0] > a[0] or (b[0] == a[0] and b[1] == a[1] + 1):
                cont += 1
        best.append((score, cont, k))
    best.sort(reverse=True)
    print("top candidates (count-match, contiguous, skip-at):")
    for s, c, k in best[:12]:
        print("   score=%d (%.1f%%)  contiguous=%d  skip_at_index=%d" % (s, 100.0 * s / N, c, k))

    s, c, k = best[0]
    seq = seq_for(k, N)
    out = []
    for i, sp in enumerate(seq):
        ay = layout[sp]
        st, a1 = ay[0]; _, a2 = ay[-1]
        out.append(dict(i=i, v=pages[i]["v"], p=pages[i]["p"], sp=sp,
                        s=st, a1=a1, a2=a2,
                        meds=[[round(m[0], 5), round(m[1], 5)] for m in pages[i]["meds"]]))
    print("skip at index", k, "-> first", out[0]["s"], out[0]["a1"], "last", out[-1]["s"], out[-1]["a2"])
    json.dump(dict(total=len(out), source="aligned-604", skipAt=k, pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json", len(out))


if __name__ == "__main__":
    main()