// Odvozené pohledy nad CaseBundle (bez vedlejších efektů).
import type { CaseBundle, Fact, FieldValue, Issue, NorFieldName } from "../types";
import { FIELD_NAMES, isRequired } from "./fields";
import { locateQuote, type Mark } from "./highlight";

export function getField(bundle: CaseBundle, field: NorFieldName): FieldValue | undefined {
  return bundle.case.fields[field];
}

export function isMissing(fv: FieldValue | undefined): boolean {
  return !fv || fv.status === "missing" || fv.value === null || fv.value === "";
}

export function missingRequired(bundle: CaseBundle): NorFieldName[] {
  return FIELD_NAMES.filter((f) => isRequired(f) && isMissing(getField(bundle, f)));
}

export function factById(bundle: CaseBundle, id: string | null | undefined): Fact | undefined {
  return id ? bundle.facts.find((f) => f.fact_id === id) : undefined;
}

export function issuesFor(bundle: CaseBundle, field: NorFieldName): Issue[] {
  return bundle.case.issues.filter((i) => i.fields.includes(field));
}

/** Issue je v UI „zkontrolováno“, když lékař potvrdil/upravil všechna jeho pole. Pravidla přepočítá backend. */
export function issueReviewed(bundle: CaseBundle, issue: Issue): boolean {
  return issue.fields.every((f) => {
    const r = getField(bundle, f)?.review;
    return r === "confirmed" || r === "edited" || r === "rejected";
  });
}

/** Značky citací pro jednu stránku dokumentu; fakty, jejichž citace nejde najít, vrací zvlášť. */
export function marksForPage(bundle: CaseBundle, docId: string, page: number, text: string): Mark[] {
  const marks: Mark[] = [];
  for (const fact of bundle.facts) {
    for (const ev of fact.evidence) {
      if (ev.doc_id !== docId || ev.page !== page) continue;
      const span = locateQuote(text, ev);
      if (span) marks.push({ ...span, factId: fact.fact_id, field: fact.field });
    }
  }
  return marks;
}

export function quoteFound(bundle: CaseBundle, fact: Fact): boolean {
  return fact.evidence.every((ev) => {
    const doc = bundle.documents.find((d) => d.doc_id === ev.doc_id);
    const text = doc?.pages.find((p) => p.page === ev.page)?.text ?? "";
    return locateQuote(text, ev) !== null;
  });
}

export type CaseSummary = {
  caseId: string;
  pseudonym: string;
  rcRaw: string;
  documents: number;
  status: CaseBundle["case"]["status"];
  issues: Record<Issue["severity"], number>;
  missingRequired: number;
  avgConfidence: number | null;
};

export function summarize(bundle: CaseBundle): CaseSummary {
  const issues = { error: 0, warning: 0, info: 0 };
  for (const i of bundle.case.issues) issues[i.severity]++;
  const scores = Object.values(bundle.case.fields)
    .map((f) => f?.confidence)
    .filter((s): s is number => typeof s === "number");
  return {
    caseId: bundle.case.case_id,
    pseudonym: bundle.patient.pseudonym ?? bundle.patient.patient_key,
    rcRaw: bundle.patient.rc_raw,
    documents: bundle.documents.length,
    status: bundle.case.status,
    issues,
    missingRequired: missingRequired(bundle).length,
    avgConfidence: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
  };
}
