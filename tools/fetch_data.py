"""Fetch surah metadata + Uthmani text from alquran.cloud into data/ files."""
import json, os, urllib.request, time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT, exist_ok=True)

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("  retry", i, e)
            time.sleep(2)
    raise SystemExit("failed " + url)

meta = get("https://api.alquran.cloud/v1/surah")
surahs = []
for s in meta["data"]:
    surahs.append(dict(n=s["number"], name=s["name"],
                       englishName=s["englishName"],
                       englishNameTranslation=s["englishNameTranslation"],
                       revelationType=s["revelationType"],
                       numberOfAyahs=s["numberOfAyahs"]))
with open(os.path.join(OUT, "surahs.json"), "w", encoding="utf-8") as f:
    json.dump(surahs, f, ensure_ascii=False, indent=1)
print("surahs:", len(surahs))

verses = {}
for n in range(1, 115):
    d = get(f"https://api.alquran.cloud/v1/surah/{n}/quran-uthmani")
    vs = d["data"]["ayahs"]
    verses[n] = [v["text"] for v in vs]
    if n % 15 == 0:
        print("  surah", n)
with open(os.path.join(OUT, "verses-uthmani.json"), "w", encoding="utf-8") as f:
    json.dump(verses, f, ensure_ascii=False)
print("verses saved")

# juz / page metadata from api
juz = get("https://api.alquran.cloud/v1/juz")
with open(os.path.join(OUT, "juz.json"), "w", encoding="utf-8") as f:
    json.dump(juz["data"], f, ensure_ascii=False, indent=1)
print("juz saved", len(juz["data"]))