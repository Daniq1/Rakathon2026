// České popisky výčtových hodnot ze schématu.
import type { Fact, FieldValue, Issue, NorCase, Document } from "../types";

export const BAND_LABEL: Record<NonNullable<FieldValue["confidence_band"]>, string> = {
  high: "vysoká",
  medium: "střední",
  low: "nízká",
};

export const LEVEL_LABEL: Record<NonNullable<FieldValue["automation_level"]>, string> = {
  A: "A – automaticky",
  B: "B – automaticky + kontrola",
  C: "C – předvyplněno k potvrzení",
  D: "D – jen upozornění",
  E: "E – ručně",
};

export const STATUS_LABEL: Record<FieldValue["status"], string> = {
  filled: "vyplněno",
  missing: "chybí",
  conflict: "konflikt",
  not_applicable: "nevztahuje se",
};

export const SOURCE_LABEL: Record<FieldValue["source"], string> = {
  auto: "vytěženo z dokumentace",
  computed: "vypočteno",
  manual: "zadáno ručně",
  admin: "administrativní (konfigurace pracoviště)",
};

export const REVIEW_LABEL: Record<NonNullable<FieldValue["review"]>, string> = {
  pending: "čeká na kontrolu",
  confirmed: "potvrzeno",
  edited: "upraveno",
  rejected: "zamítnuto",
};

export const CASE_STATUS_LABEL: Record<NorCase["status"], string> = {
  draft: "koncept",
  in_review: "v kontrole",
  approved: "schváleno",
  exported: "exportováno",
};

export const SEVERITY_LABEL: Record<Issue["severity"], string> = {
  error: "chyba",
  warning: "varování",
  info: "info",
};

export const ASSERTION_LABEL: Record<Fact["assertion"], string> = {
  affirmed: "potvrzeno",
  negated: "negováno",
  suspected: "suspektní",
  historical: "anamnesticky",
  unknown: "neurčeno",
};

export const TEMPORAL_LABEL: Record<Fact["temporal"], string> = {
  at_diagnosis: "při diagnóze",
  pre_treatment: "před léčbou",
  post_neoadjuvant: "po neoadjuvanci",
  post_surgery: "po operaci",
  current: "aktuální",
  unknown: "neurčeno",
};

export const METHOD_LABEL: Record<Fact["method"], string> = {
  llm: "LLM",
  regex: "regex",
  rule: "pravidlo",
  codelist_lookup: "číselník",
  manual: "ručně",
};

export const DOC_TYPE_LABEL: Record<Document["doc_type"], string> = {
  ambulantni_zprava: "Ambulantní zpráva",
  histologie: "Histologie",
  propoustejici_zprava: "Propouštěcí zpráva",
  cytologie: "Cytologie",
  zobrazovaci: "Zobrazovací vyšetření",
  jine: "Jiné",
  nezname: "Neznámý typ",
};

export function bandOf(score: number | null | undefined): FieldValue["confidence_band"] {
  if (score == null) return null;
  if (score >= 0.9) return "high";
  if (score >= 0.7) return "medium";
  return "low";
}

export function maskRc(rc: string): string {
  // 123456/1111 → 1234**/****: datum narození nechat, zbytek skrýt
  const digits = rc.replace(/\D/g, "");
  if (digits.length < 6) return "******";
  return `${digits.slice(0, 4)}**/${"*".repeat(Math.max(digits.length - 6, 3))}`;
}

export function formatValue(v: FieldValue["value"] | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "ano" : "ne";
  return String(v);
}
