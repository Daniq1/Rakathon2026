// Hledání citací (Evidence.quote) v textu stránky a rozdělení textu na úseky pro zvýraznění.
import type { Evidence } from "../types";

export type Span = { start: number; end: number };

export type Mark = Span & { factId: string; field: string };

/** Najde citaci v textu. Nejdřív char_start/char_end, pak doslovně, pak s tolerancí bílých znaků. */
export function locateQuote(text: string, ev: Evidence): Span | null {
  if (ev.char_start != null && ev.char_end != null && text.slice(ev.char_start, ev.char_end) === ev.quote) {
    return { start: ev.char_start, end: ev.char_end };
  }
  const exact = text.indexOf(ev.quote);
  if (exact >= 0) return { start: exact, end: exact + ev.quote.length };

  // Tolerance zalomení řádků / vícenásobných mezer (OCR, pdfplumber)
  const escaped = ev.quote.trim().split(/\s+/).map(escapeRegExp).join("\\s+");
  if (!escaped) return null;
  const m = new RegExp(escaped).exec(text);
  return m ? { start: m.index, end: m.index + m[0].length } : null;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export type Segment = { text: string; marks: Mark[] };

/** Rozdělí text na segmenty podle hranic všech značek (značky se mohou překrývat). */
export function segment(text: string, marks: Mark[]): Segment[] {
  const cuts = new Set<number>([0, text.length]);
  for (const m of marks) {
    cuts.add(m.start);
    cuts.add(m.end);
  }
  const points = [...cuts].sort((a, b) => a - b);
  const out: Segment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const [a, b] = [points[i], points[i + 1]];
    if (a === b) continue;
    out.push({ text: text.slice(a, b), marks: marks.filter((m) => m.start <= a && m.end >= b) });
  }
  return out;
}
