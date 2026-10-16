// Minimalistický hash router (bez závislostí): #/ , #/cases/<id>[/documents|/issues][?field=<pole>]
import { useEffect, useState } from "react";

export type Route =
  | { name: "patients" }
  | { name: "case"; caseId: string; field: string | null }
  | { name: "documents"; caseId: string; factId: string | null }
  | { name: "issues"; caseId: string };

export function parseHash(hash: string): Route {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const params = new URLSearchParams(query);
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "cases" && parts[1]) {
    const caseId = parts[1];
    if (parts[2] === "documents") return { name: "documents", caseId, factId: params.get("fact") };
    if (parts[2] === "issues") return { name: "issues", caseId };
    return { name: "case", caseId, field: params.get("field") };
  }
  return { name: "patients" };
}

export function href(route: Route): string {
  switch (route.name) {
    case "patients":
      return "#/";
    case "case":
      return `#/cases/${encodeURIComponent(route.caseId)}${route.field ? `?field=${route.field}` : ""}`;
    case "documents":
      return `#/cases/${encodeURIComponent(route.caseId)}/documents${route.factId ? `?fact=${route.factId}` : ""}`;
    case "issues":
      return `#/cases/${encodeURIComponent(route.caseId)}/issues`;
  }
}

export function navigate(route: Route): void {
  window.location.hash = href(route);
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
