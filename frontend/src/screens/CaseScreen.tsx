// Formulář NOR: sekce jako originální formulář, vpravo detail pole s citací.
import { ConfidenceBadge, LevelBadge, SourceIcon } from "../components/Badges";
import { FieldDetail } from "../components/FieldDetail";
import { getField, isMissing, issuesFor } from "../lib/caseView";
import { FIELD_LABELS, SECTIONS, isRequired } from "../lib/fields";
import { REVIEW_LABEL, STATUS_LABEL, formatValue } from "../lib/labels";
import { navigate } from "../router";
import { useCase } from "../state/caseStore";
import type { NorFieldName } from "../types";

export function CaseScreen({ caseId, selected }: { caseId: string; selected: NorFieldName | null }) {
  const { bundle } = useCase(caseId);
  if (!bundle) return null;

  const select = (field: NorFieldName) => navigate({ name: "case", caseId, field });

  return (
    <div className="split">
      <div className="form-pane">
        {SECTIONS.map((section) => (
          <section key={section.title} className="form-section">
            <h2>{section.title}</h2>
            <table className="field-table">
              <tbody>
                {section.fields.map((name) => {
                  const fv = getField(bundle, name);
                  const missing = isMissing(fv);
                  const required = isRequired(name);
                  const issues = issuesFor(bundle, name);
                  const cls = [
                    "field-row",
                    selected === name && "selected",
                    missing && required && "missing-required",
                    fv?.status === "conflict" && "conflict",
                  ].filter(Boolean).join(" ");
                  return (
                    <tr key={name} className={cls} onClick={() => select(name)}>
                      <td className="field-name">
                        {FIELD_LABELS[name]}
                        {required && <span className="req" title="Povinné v XSD">*</span>}
                        <div className="code muted">{name}</div>
                      </td>
                      <td className="field-value">
                        <span className={missing ? "muted" : ""}>{formatValue(fv?.value)}</span>
                        {fv?.label && <span className="muted"> · {fv.label}</span>}
                        {fv && fv.status !== "filled" && (
                          <span className={`chip st-${fv.status}`}>{STATUS_LABEL[fv.status]}</span>
                        )}
                        {!fv && required && <span className="chip st-missing">chybí</span>}
                      </td>
                      <td className="field-flags">
                        {issues.length > 0 && (
                          <span className="issue-dot" title={issues.map((i) => i.message).join("\n")}>!</span>
                        )}
                        <SourceIcon source={fv?.source} />
                        <ConfidenceBadge field={fv} />
                        <LevelBadge level={fv?.automation_level} />
                        {fv?.review && fv.review !== "pending" && (
                          <span className={`chip rv-${fv.review}`}>{REVIEW_LABEL[fv.review]}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ))}
      </div>
      <aside className="detail-pane">
        {selected ? (
          <FieldDetail key={selected} caseId={caseId} field={selected} />
        ) : (
          <div className="empty">
            <p>Vyberte pole vlevo – zobrazí se hodnota, jistota, alternativy a citace ze zdrojového dokumentu.</p>
            <Legend />
          </div>
        )}
      </aside>
    </div>
  );
}

function Legend() {
  return (
    <div className="legend">
      <h3>Legenda</h3>
      <p><span className="badge band-high">≥ 90 %</span> vysoká jistota · <span className="badge band-medium">70–89 %</span> střední · <span className="badge band-low">&lt; 70 %</span> nízká</p>
      <p><span className="badge level level-B">B</span> automaticky + kontrola · <span className="badge level level-C">C</span> předvyplněno k potvrzení · <span className="badge level level-D">D</span> jen upozornění · <span className="badge level level-E">E</span> ručně</p>
      <p>📄 vytěženo · ∑ vypočteno · ✎ ručně · ⚙ administrativní · <span className="req">*</span> povinné v XSD</p>
    </div>
  );
}
