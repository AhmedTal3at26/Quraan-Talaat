/* مصدر الصفحات: صور WebP مُجهَّزة مسبقًا (افتراضي) أو PDF.js (اختياري) */

import * as pdfjsLib from '../vendor/pdf.min.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('../vendor/pdf.worker.min.mjs', import.meta.url).href;

const VOLUME_FILES = Array.from({length:20}, (_,i)=>
  `assets/mushaf/m ${String(i+1).padStart(2,'0')} Qraan nos .pdf`);

export class PageSource {
  /** mode: 'image' (سريع) | 'pdf' (رسم مباشر من ملفات PDF) */
  constructor(mode = 'image'){
    this.mode = mode;
    this.docs = new Array(20).fill(null);
    this.counts = new Array(20).fill(0);
    this.cache = new Map();          // key -> Promise<HTMLImageElement>
  }

  /** صورة مصغّرة */
  thumbURL(i){ return `thumbs/${String(i+1).padStart(4,'0')}.webp`; }
  pageURL(i){ return `pages/${String(i+1).padStart(4,'0')}.webp`; }

  loadImage(i, full){
    const key = `${i}:${full ? 'p' : 't'}`;
    if (!this.cache.has(key)){
      const url = (full ? this.pageURL(i) : this.thumbURL(i));
      this.cache.set(key, new Promise((res, rej)=>{
        const im = new Image();
        im.decoding = 'async';
        im.onload = ()=>res(im);
        im.onerror = ()=>rej(new Error('image load failed: '+url));
        im.src = url;
      }));
    }
    return this.cache.get(key);
  }

  async loadVolume(v){
    if (this.docs[v-1]) return this.docs[v-1];
    const task = pdfjsLib.getDocument({ url: encodeURI(VOLUME_FILES[v-1]), withCredentials:false });
    const doc = await task.promise;
    this.docs[v-1] = doc;
    this.counts[v-1] = doc.numPages;
    return doc;
  }

  /**
   * يملأ العنصر <img> بصفحة i من الفهرس.
   * indexEntry: {v, p} من data/mushaf-index.json
   */
  async show(host, indexEntry, i){
    if (this.mode === 'image'){
      const im = await this.loadImage(i, true);
      host.replaceChildren(im);
      return { w: im.naturalWidth, h: im.naturalHeight };
    }
    // وضع PDF: رسم مباشر
    const canvas = document.createElement('canvas');
    host.replaceChildren(canvas);
    const doc = await this.loadVolume(indexEntry.v);
    const page = await doc.getPage(indexEntry.p);
    const cssW = host.clientWidth || 600;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const base = page.getViewport({ scale: 1 });
    const vp = page.getViewport({ scale: (cssW / base.width) * dpr });
    canvas.width = Math.floor(vp.width); canvas.height = Math.floor(vp.height);
    canvas.style.width = '100%'; canvas.style.height = '100%';
    const ctx = canvas.getContext('2d', { alpha:false });
    ctx.fillStyle = '#fff'; ctx.fillRect(0,0,canvas.width,canvas.height);
    await page.render({ canvasContext: ctx, viewport: vp }).promise;
    page.cleanup();
    return { w: base.width, h: base.height };
  }
}