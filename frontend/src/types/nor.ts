/* Generováno z schema/nor_case.schema.json (npm run gen:types). Needitovat ručně. */

/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "NorFieldName".
 */
export type NorFieldName =
  | "dat_dg"
  | "lateralita"
  | "dg_stan"
  | "dg_nov"
  | "dg_nov_slovne"
  | "topo"
  | "morfo"
  | "morfo_slovne"
  | "morfo_metoda"
  | "grade"
  | "t"
  | "n"
  | "m"
  | "ptnmy"
  | "pt"
  | "pn"
  | "pvu"
  | "ppu"
  | "psu"
  | "pm"
  | "metastaze"
  | "trofoblast"
  | "serove_markery"
  | "p16"
  | "stadium"
  | "rozsah"
  | "pozn"
  | "rodcis"
  | "pohlavi"
  | "dat_nar"
  | "obec"
  | "zeme"
  | "cizinec"
  | "bezdomovec"
  | "hzz"
  | "hodd"
  | "htyp"
  | "hdatum"
  | "lekar"
  | "idzz";

/**
 * Tok: Document (syrová data) -> Fact (vytěžené kandidáty s důkazem) -> NorCase.fields (zvolená hodnota pro každé pole NOR) -> export XML DASTA. Názvy polí = atributy nor_dg z XSD ds_idu_nor.
 */
export interface AINORInterniModelPripaduSmlouvaMeziModuly {
  schema_version: "0.1.0";
  patient: Patient;
  documents: Document[];
  facts: Fact[];
  case: NorCase;
  audit?: AuditEvent[];
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Patient".
 */
export interface Patient {
  /**
   * Normalizované RČ (jen číslice) – primární klíč. V LLM promptech se nepoužívá.
   */
  patient_key: string;
  rc_raw: string;
  /**
   * Kontrola délky, data a dělitelnosti 11. Anonymizovaná ukázková RČ budou false.
   */
  rc_valid: boolean;
  /**
   * Např. 'Pacient 1' – jediná identita, kterou vidí LLM.
   */
  pseudonym?: string;
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Document".
 */
export interface Document {
  doc_id: string;
  patient_key: string;
  doc_type:
    "ambulantni_zprava" | "histologie" | "propoustejici_zprava" | "cytologie" | "zobrazovaci" | "jine" | "nezname";
  doc_date?: PartialDate;
  source_file: string;
  mime?: string;
  /**
   * Klíč pro cache – stejný soubor se nezpracovává dvakrát.
   */
  sha256: string;
  extraction_method: "text_layer" | "ocr_tesseract" | "ocr_azure_di" | "llm_vision";
  ocr_confidence?: number | null;
  pages: {
    page: number;
    text: string;
    [k: string]: unknown;
  }[];
  ingested_at?: string;
  [k: string]: unknown;
}
/**
 * Datum s vyznačenou přesností – zprávy často uvádějí jen '3/26'.
 *
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "PartialDate".
 */
export interface PartialDate {
  /**
   * ISO: RRRR, RRRR-MM nebo RRRR-MM-DD
   */
  value?: string | null;
  precision: "day" | "month" | "year" | "unknown";
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Fact".
 */
export interface Fact {
  fact_id: string;
  field: NorFieldName;
  /**
   * Jak to stojí v textu, např. 'ypN3b', 'adenoca', '3/26'.
   */
  value_raw: string;
  /**
   * Kód po namapování na číselník.
   */
  value_code?: string | null;
  codelist?: string | null;
  codelist_candidates?: {
    code?: string;
    label?: string;
    score?: number;
    [k: string]: unknown;
  }[];
  assertion: "affirmed" | "negated" | "suspected" | "historical" | "unknown";
  temporal: "at_diagnosis" | "pre_treatment" | "post_neoadjuvant" | "post_surgery" | "current" | "unknown";
  /**
   * @minItems 1
   */
  evidence: [Evidence, ...Evidence[]];
  method: "llm" | "regex" | "rule" | "codelist_lookup" | "manual";
  model?: string | null;
  prompt_version?: string | null;
  confidence: Confidence;
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Evidence".
 */
export interface Evidence {
  doc_id: string;
  page: number;
  char_start?: number | null;
  char_end?: number | null;
  /**
   * Doslovný úryvek; backend ověří, že v textu stránky opravdu je.
   */
  quote: string;
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Confidence".
 */
export interface Confidence {
  /**
   * Složené skóre, kalibrované na gold standardu.
   */
  score: number;
  components?: {
    llm_self?: number;
    quote_verified?: boolean;
    codelist_match?: number;
    cross_doc_agreement?: number;
    rules_passed?: boolean;
    [k: string]: unknown;
  };
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "NorCase".
 */
export interface NorCase {
  case_id: string;
  patient_key: string;
  status: "draft" | "in_review" | "approved" | "exported";
  fields: {
    [k: string]: FieldValue;
  };
  issues: Issue[];
  metrics?: {
    fields_total?: number;
    fields_auto?: number;
    fields_edited?: number;
    review_seconds?: number;
    [k: string]: unknown;
  };
  export?: {
    xml_file?: string;
    xsd_valid?: boolean;
    exported_at?: string;
    [k: string]: unknown;
  } | null;
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "FieldValue".
 */
export interface FieldValue {
  /**
   * Hodnota pro XML (kód).
   */
  value: string | number | boolean | null;
  /**
   * Lidsky čitelný název z číselníku.
   */
  label?: string | null;
  status: "filled" | "missing" | "conflict" | "not_applicable";
  source: "auto" | "computed" | "manual" | "admin";
  chosen_fact_id?: string | null;
  alternative_fact_ids?: string[];
  confidence?: number | null;
  /**
   * >=0.90 high, 0.70–0.89 medium, <0.70 low (prahy doladit kalibrací).
   */
  confidence_band?: "high" | "medium" | "low" | null;
  /**
   * Podle metodiky ÚZIS: A auto, B auto+kontrola, C předvyplnit k potvrzení, D jen upozornit, E ručně.
   */
  automation_level?: "A" | "B" | "C" | "D" | "E";
  review?: "pending" | "confirmed" | "edited" | "rejected";
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "Issue".
 */
export interface Issue {
  /**
   * Např. MISSING_REQUIRED, CONFLICT_VALUE, TNM_STAGE_MISMATCH, DATE_IMPRECISE, RC_INVALID, SEX_CONFLICT
   */
  code: string;
  severity: "error" | "warning" | "info";
  fields: NorFieldName[];
  message: string;
  fact_ids?: string[];
  [k: string]: unknown;
}
/**
 * This interface was referenced by `AINORInterniModelPripaduSmlouvaMeziModuly`'s JSON-Schema
 * via the `definition` "AuditEvent".
 */
export interface AuditEvent {
  ts: string;
  actor: string;
  action: "upload" | "extract" | "llm_call" | "view" | "edit" | "confirm" | "export";
  field?: string | null;
  old?: unknown;
  new?: unknown;
  detail?: string;
  [k: string]: unknown;
}
