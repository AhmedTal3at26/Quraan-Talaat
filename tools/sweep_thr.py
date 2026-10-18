"""Sweep the clustering threshold and report cluster counts."""
import pickle, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
blob = pickle.load(open(os.path.join(WORK, "header_clusters.pkl"), "rb"))
rows = blob["rows"]
idx = [i for i, r in enumerate(rows) if r["sig"] is not None]

for thr in [0.80, 0.85, 0.88, 0.90, 0.92, 0.94, 0.96, 0.975, 0.99]:
    cents, assign = [], {}
    for i in idx:
        v = rows[i]["sig"]
        nv = np.linalg.norm(v) + 1e-9
        best, bi = -1, -1
        for j, c in enumerate(cents):
            s = float((c @ v) / (np.linalg.norm(c) * nv))
            if s > best: best, bi = s, j
        if best >= thr:
            assign[i] = bi
            cents[bi] += v; cents[bi] /= (np.linalg.norm(cents[bi]) or 1)
        else:
            cents.append(v / nv); assign[i] = len(cents) - 1
    sizes = {}
    for i in idx: sizes[assign[i]] = sizes.get(assign[i], 0) + 1
    top = sorted(sizes.values(), reverse=True)[:6]
    print("thr %.3f -> %3d clusters, top sizes %s" % (thr, len(cents), top))