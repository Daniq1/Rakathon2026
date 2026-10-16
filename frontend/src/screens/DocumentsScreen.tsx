// Všechny zprávy pacienta, text se zvýrazněnými citacemi všech faktů.
import { DocumentText } from "../components/DocumentText";
import { factById, marksForPage, quoteFound } from "../lib/caseView";
import { FIELD_LABELS } from "../lib/fields";
import { DOC_TYPE_LABEL } from "../lib/labels";
import { navigate } from "../router";
import { useCase } from "../state/caseStore";
import type { NorFieldName } from "../types";

const METHOD_LABEL = { text_layer: "textová vrstva PDF", ocr_tesseract: "OCR Tesseract", ocr_azure_di: "OCR Azure DI", llm_vision: "LLM vision" };

export function DocumentsScreen({ caseId, activeFactId }: { caseId: string; activeFactId: string | null }) {
  const { bundle } = useCase(caseId);
  if (!bundle) return null;
  const unverified = bundle.facts.filter((f) => !quoteFound(bundle, f));

  return (
    <div className="page documents">
      {unverified.length > 0 && (
        <div className="issue-box sev-warning">
          Citace nenalezené v textu: {unverified.map((f) => `${f.fact_id} (${FIELD_LABELS[f.field]})`).join(", ")}
        </div>
      )}
      <p className="muted small">Klik na zvýrazněnou citaci otevře pole ve formuláři NOR.</p>
      {bundle.documents.map((doc) => (
        <article key={doc.doc_id} className="document">
          <header>
            <h2>{DOC_TYPE_LABEL[doc.doc_type]}</h2>
            <span className="muted small">
              {doc.source_file} · {METHOD_LABEL[doc.extraction_method]}
              {doc.ocr_confidence != null && ` (${Math.round(doc.ocr_confidence * 100)} %)`} · sha256 {doc.sha256.slice(0, 12)}…
            </span>
          </header>
          {doc.pages.map((p) => (
            <section key={p.page} className="doc-page">
              <div className="page-no muted small">strana {p.page}</div>
              <DocumentText
                text={p.text}
                marks={marksForPage(bundle, doc.doc_id, p.page, p.text)}
                activeFactId={activeFactId}
                markTitle={(m) => {
                  const f = factById(bundle, m.factId);
                  return `${FIELD_LABELS[m.field as NorFieldName]}: ${f?.value_code ?? f?.value_raw ?? ""} (${m.factId})`;
                }}
                onMarkClick={(m) => navigate({ name: "case", caseId, field: m.field as NorFieldName })}
              />
            </section>
          ))}
        </article>
      ))}
    </div>
  );
}
