// Hlavička případu: pacient, stav, záložky, čas kontroly a schválení.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { missingRequired } from "../lib/caseView";
import { CASE_STATUS_LABEL, maskRc } from "../lib/labels";
import { href, type Route } from "../router";
import { useCase } from "../state/caseStore";

// Aktivní čas kontroly po případech (přežije přepínání záložek).
const activeSeconds = new Map<string, number>();

function useReviewTimer(caseId: string, running: boolean): number {
  const [seconds, setSeconds] = useState(activeSeconds.get(caseId) ?? 0);
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      // Počítat jen když je okno vidět (aktivní čas, ne čas otevřené záložky)
      if (document.visibilityState !== "visible") return;
      const next = (activeSeconds.get(caseId) ?? 0) + 1;
      activeSeconds.set(caseId, next);
      setSeconds(next);
    }, 1000);
    return () => window.clearInterval(id);
  }, [caseId, running]);
  return seconds;
}

function fmt(s: number): string {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function CaseLayout({ caseId, route, children }: { caseId: string; route: Route; children: ReactNode }) {
  const { bundle, dispatch } = useCase(caseId);
  const approved = bundle?.case.status === "approved" || bundle?.case.status === "exported";
  const seconds = useReviewTimer(caseId, !!bundle && !approved);
  const viewed = useRef(false);

  useEffect(() => {
    if (bundle && !viewed.current) {
      viewed.current = true;
      dispatch({ type: "view" });
    }
  }, [bundle, dispatch]);

  if (!bundle) {
    return (
      <div className="page">
        <p>Případ {caseId} nenalezen. <a href="#/">Zpět na pacienty</a></p>
      </div>
    );
  }

  const errors = bundle.case.issues.filter((i) => i.severity === "error").length;
  const missing = missingRequired(bundle).length;
  const tabs: { label: string; route: Route }[] = [
    { label: "Formulář NOR", route: { name: "case", caseId, field: null } },
    { label: "Dokumenty", route: { name: "documents", caseId, factId: null } },
    { label: `Upozornění (${bundle.case.issues.length + missing})`, route: { name: "issues", caseId } },
  ];

  function approve() {
    const warn = errors + missing > 0
      ? `Případ má ${errors} chyb a ${missing} chybějících povinných polí. Export zůstane zablokovaný, dokud je backend nevyřeší. Přesto schválit?`
      : "Schválit případ?";
    if (window.confirm(warn)) dispatch({ type: "approve", reviewSeconds: seconds });
  }

  return (
    <div className="case-layout">
      <header className="case-header">
        <div>
          <a href="#/" className="muted">← Pacienti</a>
          <h1>
            {bundle.patient.pseudonym ?? bundle.patient.patient_key}
            <span className="mono muted"> · RČ {maskRc(bundle.patient.rc_raw)}</span>
            {!bundle.patient.rc_valid && <span className="badge sev-info" title="RČ neprošlo kontrolou">RČ neplatné</span>}
          </h1>
        </div>
        <div className="case-meta">
          <span className={`status status-${bundle.case.status}`}>{CASE_STATUS_LABEL[bundle.case.status]}</span>
          <span className="timer" title="Aktivní čas kontroly">⏱ {fmt(approved ? Math.round(bundle.case.metrics?.review_seconds ?? seconds) : seconds)}</span>
          <span className="muted">opravy: {bundle.case.metrics?.fields_edited ?? 0}</span>
          <button className="primary" onClick={approve} disabled={approved}>
            {approved ? "Schváleno" : "Schválit případ"}
          </button>
        </div>
      </header>
      <nav className="tabs">
        {tabs.map((t) => (
          <a key={t.label} href={href(t.route)} className={t.route.name === route.name ? "tab active" : "tab"}>
            {t.label}
          </a>
        ))}
      </nav>
      {children}
    </div>
  );
}
