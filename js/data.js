/* Quran data + index helpers */

export const AZ = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];

export function toArabicDigits(n){
  return String(n).replace(/\d/g, d => AZ[+d]);
}

/** تطبيع للبحث: حذف الحركات وتوحيد الحروف */
function baseNorm(s, dagger){
  let t = s
    .replace(/\u0670/g, dagger ? '\u0627' : '')        // الألف الخنجرية
    .replace(/\u0671/g, '\u0627')                    // ألف الوصل
    .replace(/[\u0610-\u061A\u064B-\u065F\u06D6-\u06ED\u0640]/g, '');
  return t
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/ؤ/g, 'و')
    .replace(/ئ/g, 'ي')
    .replace(/\s+/g, ' ')
    .trim();
}

export function normalize(s){ return baseNorm(s, true); }
export function normalize2(s){ return baseNorm(s, false); }

/** اسم السورة بلا تشكيل */
export function plain(s){ return s.replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g, '').trim(); }

export class QuranData {
  constructor(){ this.surahs = null; this.verses = null; this.juz = null; this.index = null; }

  async load(){
    const [s, v, j, ix] = await Promise.all([
      fetch('data/surahs.json').then(r=>r.json()),
      fetch('data/verses-uthmani.json').then(r=>r.json()),
      fetch('data/juz.json').then(r=>r.json()),
      fetch('data/mushaf-index.json').then(r=>r.json()),
    ]);
    this.surahs = s;
    this.verses = v;
    this.juz = j.juz;
    this.index = ix;
    this.buildSearch();
    return this;
  }

  buildSearch(){
    // this.starts[s-1] = رقم الآية العام لأول آية في السورة s
    this.starts = [];
    let t = 1;
    for (let n = 1; n <= 114; n++){
      this.starts.push(t);
      t += this.surahs[n-1].numberOfAyahs;
    }
    this.totalAyah = t - 1;

    this.flat = [];
    for (let n = 1; n <= 114; n++){
      const vs = this.verses[n] || [];
      for (let a = 1; a <= vs.length; a++){
        this.flat.push({ s:n, a, t:normalize(vs[a-1]), u:normalize2(vs[a-1]) });
      }
    }
  }

  /** رقم الآية العام لـ (سورة، آية) */
  global(s, a){ return this.starts[s-1] + a - 1; }

  /** (سورة، آية) من رقم الآية العام */
  fromGlobal(g){
    let lo = 0, hi = 113;
    while (lo < hi){
      const mid = (lo + hi + 1) >> 1;
      if (this.starts[mid] <= g) lo = mid; else hi = mid - 1;
    }
    return { s: lo + 1, a: g - this.starts[lo] + 1 };
  }

  verse(n, a){ return (this.verses[n] || [])[a-1] || ''; }
  surah(n){ return this.surahs[n-1]; }
  surahName(n){
    const s = this.surahs[n-1];
    if (!s) return '';
    return plain(s.name).replace(/^سورة\s*/, '').trim();
  }

  /** صفحة المصحف التي تقع فيها (سورة، آية) */
  locate(s, a){
    if (!this.index) return null;
    const g = this.global(s, a);
    const pages = this.index.pages;
    let lo = 0, hi = pages.length - 1;
    while (lo < hi){
      const mid = (lo + hi + 1) >> 1;
      if (pages[mid].g <= g) lo = mid; else hi = mid - 1;
    }
    const p = pages[lo];
    if (g < p.g || g >= p.g + p.n) return null;
    return { page: p, idx: lo, offset: g - p.g };
  }

  /** رقم الصفحة في المصحف لبداية السورة */
  surahStartPage(n){
    const r = this.locate(n, 1);
    return r ? r.idx : null;
  }

  juzOf(s, a){
    let cur = 1;
    for (const j of this.juz){
      if (j.s < s || (j.s === s && j.a <= a)) cur = j.j; else break;
    }
    return cur;
  }

  search(query, limit = 80){
    const qa = normalize(query);
    const qb = normalize2(query);
    if (!qa) return [];
    const A = qa.split(' ').filter(Boolean);
    const B = qb.split(' ').filter(Boolean);
    const out = [];
    for (const v of this.flat){
      let score = 0, ok = true;
      for (const t of A){
        const i = v.t.indexOf(t);
        if (i < 0){ ok = false; break; }
        score += (i === 0 ? 3 : 1);
      }
      if (!ok){
        ok = true; score = 0;
        for (const t of B){
          const i = v.u.indexOf(t);
          if (i < 0){ ok = false; break; }
          score += (i === 0 ? 3 : 1);
        }
      }
      if (ok){
        out.push({ s:v.s, a:v.a, t:v.t, score });
        if (out.length >= limit * 8) break;
      }
    }
    out.sort((a,b)=> b.score - a.score);
    return out.slice(0, limit);
  }

  /** Juz name for a juz number */
  juzName(j){
    const hit = this.juz.find(x=>x.j===j);
    return hit ? hit.name : ('الجزء ' + toArabicDigits(j));
  }
}