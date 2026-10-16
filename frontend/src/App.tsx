import { useEffect, useState } from "react";
import { loadCases } from "./api";
import { FIELD_NAMES } from "./lib/fields";
import { useRoute } from "./router";
import { CaseLayout } from "./screens/CaseLayout";
import { CaseScreen } from "./screens/CaseScreen";
import { DocumentsScreen } from "./screens/DocumentsScreen";
import { IssuesScreen } from "./screens/IssuesScreen";
import { PatientsScreen } from "./screens/PatientsScreen";
import { CaseProvider } from "./state/caseStore";
import type { CaseBundle, NorFieldName } from "./types";

export function App() {
  const [cases, setCases] = useState<CaseBundle[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCases().then(setCases, (e) => setError(String(e)));
  }, []);

  if (error) return <div className="page">Nepodařilo se načíst data: {error}</div>;
  if (!cases) return <div className="page muted">Načítám…</div>;

  return (
    <CaseProvider initial={cases}>
      <TopBar />
      <Routes />
    </CaseProvider>
  );
}

function TopBar() {
  return (
    <div className="topbar">
      <a href="#/" className="brand">AI NOR</a>
      <span className="muted small">Incidence zhoubného novotvaru · ukázková data (řez 1)</span>
    </div>
  );
}

function Routes() {
  const route = useRoute();
  switch (route.name) {
    case "patients":
      return <PatientsScreen />;
    case "case": {
      const field = FIELD_NAMES.includes(route.field as NorFieldName) ? (route.field as NorFieldName) : null;
      return (
        <CaseLayout caseId={route.caseId} route={route}>
          <CaseScreen caseId={route.caseId} selected={field} />
        </CaseLayout>
      );
    }
    case "documents":
      return (
        <CaseLayout caseId={route.caseId} route={route}>
          <DocumentsScreen caseId={route.caseId} activeFactId={route.factId} />
        </CaseLayout>
      );
    case "issues":
      return (
        <CaseLayout caseId={route.caseId} route={route}>
          <IssuesScreen caseId={route.caseId} />
        </CaseLayout>
      );
  }
}
