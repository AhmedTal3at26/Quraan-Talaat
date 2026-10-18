/* PDF.js rendering + page spread management */

import * as pdfjsLib from '../vendor/pdf.min.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('../vendor/pdf.worker.min.mjs', import.meta.url).href;

const VOLUME_FILES = Array.from({length:20}, (_,i)=>
  `assets/mushaf/m ${String(i+1).padStart(2,'0')} Qraan nos .pdf`);

export class MushafSource {
  constructor(onProgress){
    this.docs = new Array(20).fill(null);
    this.counts = new Array(20).fill(0);
    this.onProgress = onProgress || (()=>{});
  }

  async loadVolume(v){            // v is 1-based
    if (this.docs[v-1]) return this.docs[v-1];
    this.onProgress(`تحميل الجزء ${v}`);
    const url = encodeURI(VOLUME_FILES[v-1]);
    const task = pdfjsLib.getDocument({ url, withCredentials:false });
    const doc = await task.promise;
    this.docs[v-1] = doc;
    this.counts[v-1] = doc.numPages;
    return doc;
  }

  getCount(v){ return this.counts[v-1] || 0; }

  async render(v, pno, canvas, targetW, dpr){
    const doc = await this.loadVolume(v);
    const page = await doc.getPage(pno + 1);   // 0-based
    const base = page.getViewport({ scale: 1 });
    const scale = (targetW / base.width) * dpr;
    const vp = page.getViewport({ scale });
    canvas.width = Math.floor(vp.width);
    canvas.height = Math.floor(vp.height);
    const ctx = canvas.getContext('2d', { alpha:false });
    ctx.fillStyle = '#fff';
    ctx.fillRect(0,0,canvas.width,canvas.height);
    await page.render({ canvasContext: ctx, viewport: vp }).promise;
    page.cleanup();
    return { w: canvas.width, h: canvas.height, pageW: base.width, pageH: base.height };
  }

  async thumb(v, pno, canvas, h){
    const doc = await this.loadVolume(v);
    const page = await doc.getPage(pno + 1);
    const base = page.getViewport({ scale: 1 });
    const scale = (h / base.height);
    const vp = page.getViewport({ scale });
    canvas.width = Math.floor(vp.width);
    canvas.height = Math.floor(vp.height);
    const ctx = canvas.getContext('2d', { alpha:false });
    ctx.fillStyle='#fff'; ctx.fillRect(0,0,canvas.width,canvas.height);
    await page.render({ canvasContext: ctx, viewport: vp }).promise;
    page.cleanup();
  }
}