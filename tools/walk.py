"""walk.py — يفكّ ترميز أرقام الآيات ويبني data/mushaf-index.json

يُستدعى بعد تسمية عناقيد الأرقام في tools/work/digit_labels.json
    python tools/walk.py
"""
import json, os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ROOT, "tools", "work")
DATA = os.path.join(ROOT, "data")


def load_surah_counts():
    with open(os.path.join(DATA, "surahs.json"), encoding="utf-8") as f:
        return [s["numberOfAyahs"] for s in json.load(f)]


def decode(ids, labels):
    try:
        return int("".join(str(labels[c]) for c in ids))
    except KeyError:
        return None


def main():
    labels = {int(k): int(v) for k, v in
              json.load(open(os.path.join(WORK, "digit_labels.json"), encoding="utf-8")).items()}
    blob = pickle.load(open(os.path.join(WORK, "detect.pkl"), "rb"))
    pages = blob["pages"]
    counts = load_surah_counts()

    s, a = 1, 1
    anomalies, out = [], []

    for i, pg in enumerate(pages):
        meds = sorted(pg["meds"], key=lambda m: m["y"])
        if not meds:
            continue
        start_s, start_a = s, a
        pts = []
        for m in meds:
            v = decode(m["d"], labels)
            pts.append([m["x"], m["y"]])
            if v is None:
                anomalies.append(dict(i=i, v=pg["v"], p=pg["p"], got=None, want=[s, a]))
                continue
            if v == a:
                a += 1
            elif v == 1:
                s += 1; a = 1
                if s > 114:
                    anomalies.append(dict(i=i, v=pg["v"], p=pg["p"], got=v, want="past-end"))
                    s, a = 114, counts[-1]
            else:
                anomalies.append(dict(i=i, v=pg["v"], p=pg["p"], got=v, want=[s, a]))
        if a > counts[s - 1]:
            s += 1; a = 1
        out.append(dict(i=len(out), v=pg["v"], p=pg["p"], s=start_s,
                        a1=start_a, a2=max(start_a, a - 1), meds=pts))

    json.dump(dict(anomalies=anomalies[:5000], n=len(anomalies)),
              open(os.path.join(WORK, "walk_log.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"anomalies: {len(anomalies)}  → tools/work/walk_log.json")
    if out:
        print(f"pages: {len(out)}  first: s{out[0]['s']}:{out[0]['a1']}  "
              f"last: s{out[-1]['s']}:{out[-1]['a2']} (expected 114:286)")

    json.dump(dict(version=1, total=len(out),
                   pageW=488.976, pageH=701.575, pages=out),
              open(os.path.join(DATA, "mushaf-index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("wrote data/mushaf-index.json")


if __name__ == "__main__":
    main()