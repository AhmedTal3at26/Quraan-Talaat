"""
build_all.py — يولّد كل ما يحتاجه الموقع من ملفات PDF الأصلية.

الخطوات:
  1) كشف زخارف أرقام الآيات في كل صفحة      → tools/work/meds_all.pkl
  2) بناء خريطة (سورة، آية) لكل صفحة        → data/mushaf-index.json
  3) رسم الصفحات إلى صور WebP               → pages/ و thumbs/

    python tools/build_all.py
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

STEPS = [
    ("كشف زخارف الآيات", "medstats.py"),
    ("بناء فهرس الصفحات", "build_index_final.py"),
    ("رسم صور الصفحات", "render_pages.py"),
]

if __name__ == "__main__":
    for i, (title, script) in enumerate(STEPS, 1):
        print("\n" + "=" * 62)
        print(f"[{i}/{len(STEPS)}] {title}  ({script})")
        print("=" * 62)
        r = subprocess.run([PY, os.path.join(HERE, script)] + sys.argv[1:], cwd=HERE)
        if r.returncode != 0:
            sys.exit(f"فشلت الخطوة: {script}")
    print("\nتم. شغّل الخادم بالأمر:  python tools/serve.py")