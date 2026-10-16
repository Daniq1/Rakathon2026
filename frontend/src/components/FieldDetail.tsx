// Detail pole: hodnota, jistota, citace ve zdroji, alternativy, editace (Potvrdit / Upravit / Zamítnout).
import { useMemo, useState } from "react";
import { codelistFor } from "../api";
import { factById, getField, issuesFor, marksForPage, quoteFound } from "../lib/caseView";
import { FIELD_LABELS, codelistOf, isRequired } from "../lib/fields";
import {
  ASSERTION_LABEL, DOC_TYPE_LABEL, LEVEL_LABEL, METHOD_LABEL, REVIEW_LABEL,
  SOURCE_LABEL, STATUS_LABEL, TEMPORAL_LABEL, formatValue,
} from "../lib/labels";
import { href } from "../router";
import { useCase } from "../state/caseStore";
import type { CaseBundle, Fact, NorFieldName } from "../types";
import { ConfidenceBadge, LevelBadge, SeverityBadge, SourceIcon } from "./Badges";
import { DocumentText } from "./DocumentText";

export function FieldDetail({ caseId, field }: { caseId: string; field: NorFieldName }) {
  const { bundle, dispatch } = useCase(caseId);
  const [editing, setEditing] = useState(false);
  if (!bundle) return null;

  const fv = getField(bundle, field);
  const chosen = factById(bundle, fv?.chosen_fact_id);
  const alternatives = (fv?.alternative_fact_ids ?? [])
    .map((id) => factById(bundle, id))
    .filter((f): f is Fact => !!f);
  const otherFacts = bundle.facts.filter(
    (f) => f.field === field && f.fact_id !== chosen?.fact_id && !alternatives.includes(f),
  );
  const issues = issuesFor(bundle, field);
  const codelist = codelistOf(field);

  return (
    <div className="field-detail">
      <div className="fd-head">
        <h2>
          {FIELD_LABELS[field]} {isRequired(field) && <span className="req" title="Povinné v XSD">*</span>}
        </h2>
        <div className="muted code">
          {field} · číselník: {codelist ?? "bez číselníku"}
        </div>
      </div>

      <div className="fd-value">
        <div className="big">{formatValue(fv?.value)}</div>
        {fv?.label && <div>{fv.label}</div>}
        <div className="fd-badges">
          <SourceIcon source={fv?.source} />
          <ConfidenceBadge field={fv} />
          <LevelBadge level={fv?.automation_level} />
          {fv && <span className={`chip st-${fv.status}`}>{STATUS_LABEL[fv.status]}</span>}
          {fv?.review && <span className={`chip rv-${fv.review}`}>{REVIEW_LABEL[fv.review]}</span>}
        </div>
        {fv && (
          <div className="muted small">
            {SOURCE_LABEL[fv.source]}
            {fv.automation_level && ` · ${LEVEL_LABEL[fv.automation_level]}`}
            {fv.reviewed_at && ` · ${fv.reviewed_by}, ${new Date(fv.reviewed_at).toLocaleString("cs-CZ")}`}
          </div>
        )}
      </div>

      {issues.map((i, n) => (
        <div key={n} className={`issue-box sev-${i.severity}`}>
          <SeverityBadge severity={i.severity} /> <strong>{i.code}</strong> – {i.message}
        </div>
      ))}

      {editing ? (
        <FieldEditor
          field={field}
          codelist={codelist}
          initial={fv?.value == null ? "" : String(fv.value)}
          onCancel={() => setEditing(false)}
          onSave={(value, label) => {
            dispatch({ type: "edit", field, value, label });
            setEditing(false);
          }}
        />
      ) : (
        <div className="actions">
          <button className="primary" disabled={!fv || fv.value == null} onClick={() => dispatch({ type: "confirm", field })}>
            Potvrdit
          </button>
          <button onClick={() => setEditing(true)}>Upravit</button>
          <button className="danger" disabled={!fv || fv.value == null} onClick={() => dispatch({ type: "reject", field })}>
            Zamítnout
          </button>
        </div>
      )}

      {chosen ? (
        <FactCard bundle={bundle} fact={chosen} title="Zvolený fakt" showDocument />
      ) : (
        <p className="muted">
          {fv?.source === "admin"
            ? "Administrativní pole – hodnota z konfigurace pracoviště, nevytěžuje se z textu."
            : "Pro toto pole nebyl v dokumentaci nalezen žádný fakt. Doplňte ručně."}
        </p>
      )}

      {fv?.chosen_fact_id && !chosen && (
        <p className="issue-box sev-warning">Fakt {fv.chosen_fact_id} v datech případu chybí.</p>
      )}

      {[...alternatives, ...otherFacts].length > 0 && (
        <>
          <h3>Alternativy z jiných faktů</h3>
          {[...alternatives, ...otherFacts].map((f) => (
            <FactCard
              key={f.fact_id}
              bundle={bundle}
              fact={f}
              onUse={() => dispatch({ type: "choose_fact", field, factId: f.fact_id })}
            />
          ))}
        </>
      )}
    </div>
  );
}

function FactCard({
  bundle, fact, title, showDocument, onUse,
}: { bundle: CaseBundle; fact: Fact; title?: string; showDocument?: boolean; onUse?: () => void }) {
  const verified = quoteFound(bundle, fact);
  const c = fact.confidence.components;
  return (
    <div className="fact-card">
      <div className="fact-head">
        <strong>{title ?? `Fakt ${fact.fact_id}`}</strong>
        <span className="mono">{fact.value_code ?? "—"}</span>
        <span className="muted">„{fact.value_raw}“</span>
        <span className="badge band-none">{Math.round(fact.confidence.score * 100)} %</span>
        {onUse && <button className="small" onClick={onUse}>Použít</button>}
      </div>
      <div className="fact-meta small">
        <span className={`chip as-${fact.assertion}`}>{ASSERTION_LABEL[fact.assertion]}</span>
        <span className="chip">{TEMPORAL_LABEL[fact.temporal]}</span>
        <span className="chip">{METHOD_LABEL[fact.method]}{fact.prompt_version ? ` ${fact.prompt_version}` : ""}</span>
        <span className={verified ? "chip ok" : "chip bad"}>{verified ? "citace ověřena" : "citace nenalezena"}</span>
        {c?.codelist_match != null && <span className="chip">číselník {Math.round(c.codelist_match * 100)} %</span>}
        {c?.cross_doc_agreement != null && <span className="chip">shoda dokumentů {Math.round(c.cross_doc_agreement * 100)} %</span>}
      </div>
      {fact.codelist_candidates && fact.codelist_candidates.length > 0 && (
        <div className="small muted">
          Kandidáti z číselníku: {fact.codelist_candidates.map((k) => `${k.code} ${k.label ?? ""} (${k.score})`).join(", ")}
        </div>
      )}
      {fact.evidence.map((ev, i) => {
        const doc = bundle.documents.find((d) => d.doc_id === ev.doc_id);
        const page = doc?.pages.find((p) => p.page === ev.page);
        const docLabel = doc ? `${DOC_TYPE_LABEL[doc.doc_type]} (${doc.source_file})` : ev.doc_id;
        return (
          <div key={i} className="evidence">
            <div className="small">
              <a href={href({ name: "documents", caseId: bundle.case.case_id, factId: fact.fact_id })}>
                {docLabel}, str. {ev.page}
              </a>
            </div>
            <blockquote>{ev.quote}</blockquote>
            {showDocument && page && (
              <div className="doc-excerpt">
                <DocumentText
                  text={page.text}
                  marks={marksForPage(bundle, ev.doc_id, ev.page, page.text)}
                  activeFactId={fact.fact_id}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function FieldEditor({
  field, codelist, initial, onSave, onCancel,
}: {
  field: NorFieldName;
  codelist: string | null;
  initial: string;
  onSave: (value: string | null, label: string | null) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(initial);
  const items = codelistFor(codelist);
  const suggestions = useMemo(() => {
    if (!items || !text.trim()) return [];
    const q = text.trim().toLowerCase().replace(".", "");
    return items
      .filter((it) => it.code.toLowerCase().startsWith(q) || it.label.toLowerCase().includes(q))
      .slice(0, 8);
  }, [items, text]);
  const exact = items?.find((it) => it.code === text.trim().toUpperCase().replace(".", ""));
  const outsideCodelist = !!items && !!text.trim() && !exact;

  return (
    <div className="editor">
      <label className="small muted" htmlFor={`edit-${field}`}>
        Nová hodnota{items ? " (kód z číselníku)" : ""}
      </label>
      <input
        id={`edit-${field}`}
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel();
        }}
      />
      {suggestions.length > 0 && !exact && (
        <ul className="suggestions">
          {suggestions.map((s) => (
            <li key={s.code} onMouseDown={() => setText(s.code)}>
              <span className="mono">{s.dotted}</span> {s.label}
            </li>
          ))}
        </ul>
      )}
      {exact && <div className="small">{exact.dotted} – {exact.label}</div>}
      {outsideCodelist && <div className="small bad-text">Kód není v číselníku {codelist}.</div>}
      {!items && codelist && (
        <div className="small muted">Číselník {codelist} zatím není k dispozici – hodnota se uloží jako text.</div>
      )}
      <div className="actions">
        <button
          className="primary"
          disabled={outsideCodelist}
          onClick={() => onSave(text.trim() === "" ? null : exact?.code ?? text.trim(), exact?.label ?? null)}
        >
          Uložit
        </button>
        <button onClick={onCancel}>Zrušit</button>
      </div>
    </div>
  );
}
