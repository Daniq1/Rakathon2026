// Seznam upozornění; chybějící povinná pole nahoře. Klik přeskočí na pole ve formuláři.
import { SeverityBadge } from "../components/Badges";
import { issueReviewed, missingRequired } from "../lib/caseView";
import { FIELD_LABELS } from "../lib/fields";
import { href } from "../router";
import { useCase } from "../state/caseStore";
import type { Issue } from "../types";

const SEVERITY_ORDER: Record<Issue["severity"], number> = { error: 0, warning: 1, info: 2 };

export function IssuesScreen({ caseId }: { caseId: string }) {
  const { bundle } = useCase(caseId);
  if (!bundle) return null;
  const missing = missingRequired(bundle);
  const issues = [...bundle.case.issues].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  return (
    <div className="page issues">
      <h2>Chybějící povinná pole ({missing.length})</h2>
      {missing.length === 0 ? (
        <p className="muted">Všechna povinná pole jsou vyplněná.</p>
      ) : (
        <ul className="issue-list">
          {missing.map((f) => (
            <li key={f}>
              <a href={href({ name: "case", caseId, field: f })}>
                <SeverityBadge severity="error" /> <strong>{FIELD_LABELS[f]}</strong>{" "}
                <span className="muted code">{f}</span> – povinné pole XSD bez hodnoty
              </a>
            </li>
          ))}
        </ul>
      )}

      <h2>Upozornění z pravidel ({issues.length})</h2>
      <ul className="issue-list">
        {issues.map((i, n) => {
          const reviewed = issueReviewed(bundle, i);
          return (
            <li key={n} className={reviewed ? "reviewed" : ""}>
              <a href={href({ name: "case", caseId, field: i.fields[0] ?? null })}>
                <SeverityBadge severity={i.severity} /> <strong>{i.code}</strong>{" "}
                <span className="muted">[{i.fields.map((f) => FIELD_LABELS[f]).join(", ")}]</span>
                <div>{i.message}</div>
                {reviewed && <div className="small ok-text">pole zkontrolováno lékařem – pravidla přepočítá backend</div>}
              </a>
            </li>
          );
        })}
      </ul>

      <h2>Audit ({bundle.audit?.length ?? 0})</h2>
      <table className="table small">
        <thead>
          <tr><th>Čas</th><th>Kdo</th><th>Akce</th><th>Pole</th><th>Staré → nové</th><th>Detail</th></tr>
        </thead>
        <tbody>
          {[...(bundle.audit ?? [])].reverse().map((a, n) => (
            <tr key={n}>
              <td>{new Date(a.ts).toLocaleString("cs-CZ")}</td>
              <td>{a.actor}</td>
              <td>{a.action}</td>
              <td className="code">{a.field ?? ""}</td>
              <td className="mono">{a.old !== undefined || a.new !== undefined ? `${JSON.stringify(a.old ?? null)} → ${JSON.stringify(a.new ?? null)}` : ""}</td>
              <td>{a.detail ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
