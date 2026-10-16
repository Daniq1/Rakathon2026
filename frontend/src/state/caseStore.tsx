// Stav otevřeného případu: editace polí v paměti, každá změna jde do auditu (pravidlo 5).
// V řezu 3 se akce přepnou na PATCH /api/cases/{id}/fields/{field}.
import { createContext, useContext, useReducer, type ReactNode } from "react";
import type { AuditEvent, CaseBundle, FieldValue, NorFieldName } from "../types";
import { bandOf } from "../lib/labels";

export const REVIEWER = "lékař (demo)";

type Action =
  | { type: "confirm"; field: NorFieldName }
  | { type: "reject"; field: NorFieldName }
  | { type: "edit"; field: NorFieldName; value: FieldValue["value"]; label: string | null }
  | { type: "choose_fact"; field: NorFieldName; factId: string }
  | { type: "approve"; reviewSeconds: number }
  | { type: "view" };

export function emptyField(): FieldValue {
  return {
    value: null,
    label: null,
    status: "missing",
    source: "manual",
    chosen_fact_id: null,
    alternative_fact_ids: [],
    confidence: null,
    confidence_band: null,
    automation_level: "E",
    review: "pending",
  };
}

function reducer(state: CaseBundle, action: Action): CaseBundle {
  const ts = new Date().toISOString();
  // Omit<> nad typem s indexovou signaturou ztrácí pojmenované vlastnosti, proto Pick
  type Entry = Pick<AuditEvent, "action"> & Partial<Pick<AuditEvent, "field" | "old" | "new" | "detail">>;
  const log = (e: Entry): AuditEvent[] => [
    ...(state.audit ?? []),
    { ts, actor: REVIEWER, ...e },
  ];

  if (action.type === "view") {
    return { ...state, audit: log({ action: "view", field: null, detail: "otevření případu" }) };
  }

  if (action.type === "approve") {
    return {
      ...state,
      case: {
        ...state.case,
        status: "approved",
        metrics: { ...state.case.metrics, review_seconds: action.reviewSeconds },
      },
      audit: log({
        action: "confirm",
        field: null,
        old: state.case.status,
        new: "approved",
        detail: `schválení případu, aktivní čas kontroly ${Math.round(action.reviewSeconds)} s`,
      }),
    };
  }

  const old = state.case.fields[action.field] ?? emptyField();
  let next: FieldValue;
  let audit: AuditEvent[];
  let edited = false;

  switch (action.type) {
    case "confirm":
      next = { ...old, review: "confirmed" };
      audit = log({ action: "confirm", field: action.field, old: old.value, new: old.value });
      break;
    case "reject":
      next = { ...old, review: "rejected", value: null, label: null, status: "missing" };
      audit = log({ action: "edit", field: action.field, old: old.value, new: null, detail: "zamítnuto" });
      edited = true;
      break;
    case "edit":
      next = {
        ...old,
        value: action.value,
        label: action.label,
        status: action.value === null || action.value === "" ? "missing" : "filled",
        source: "manual",
        review: "edited",
        confidence: 1,
        confidence_band: "high",
      };
      audit = log({ action: "edit", field: action.field, old: old.value, new: action.value });
      edited = true;
      break;
    case "choose_fact": {
      const fact = state.facts.find((f) => f.fact_id === action.factId);
      if (!fact) return state;
      const others = [old.chosen_fact_id, ...(old.alternative_fact_ids ?? [])].filter(
        (id): id is string => !!id && id !== fact.fact_id,
      );
      next = {
        ...old,
        value: fact.value_code ?? fact.value_raw,
        label: null,
        status: "filled",
        chosen_fact_id: fact.fact_id,
        alternative_fact_ids: others,
        confidence: fact.confidence.score,
        confidence_band: bandOf(fact.confidence.score),
        review: "edited",
      };
      audit = log({
        action: "edit",
        field: action.field,
        old: old.value,
        new: next.value,
        detail: `zvolena alternativa ${fact.fact_id}`,
      });
      edited = true;
      break;
    }
  }

  next = { ...next, reviewed_by: REVIEWER, reviewed_at: ts };
  const metrics = state.case.metrics ?? {};
  // Počítat opravy po polích, ne po kliknutích
  const firstEdit = edited && old.review !== "edited" && old.review !== "rejected";
  return {
    ...state,
    case: {
      ...state.case,
      status: state.case.status === "draft" ? "in_review" : state.case.status,
      fields: { ...state.case.fields, [action.field]: next },
      metrics: firstEdit ? { ...metrics, fields_edited: (metrics.fields_edited ?? 0) + 1 } : metrics,
    },
    audit,
  };
}

// Všechny načtené případy podle case_id
type Store = Record<string, CaseBundle>;
type StoreAction = { caseId: string; action: Action };

function storeReducer(store: Store, { caseId, action }: StoreAction): Store {
  const bundle = store[caseId];
  return bundle ? { ...store, [caseId]: reducer(bundle, action) } : store;
}

type Ctx = { store: Store; dispatch: (a: StoreAction) => void };
const CaseContext = createContext<Ctx | null>(null);

export function CaseProvider({ initial, children }: { initial: CaseBundle[]; children: ReactNode }) {
  const [store, dispatch] = useReducer(
    storeReducer,
    initial,
    (list): Store => Object.fromEntries(list.map((b) => [b.case.case_id, b])),
  );
  return <CaseContext.Provider value={{ store, dispatch }}>{children}</CaseContext.Provider>;
}

function useStore(): Ctx {
  const ctx = useContext(CaseContext);
  if (!ctx) throw new Error("useCase mimo CaseProvider");
  return ctx;
}

export function useAllCases(): CaseBundle[] {
  return Object.values(useStore().store);
}

export function useCase(caseId: string): { bundle: CaseBundle | undefined; dispatch: (a: Action) => void } {
  const { store, dispatch } = useStore();
  return { bundle: store[caseId], dispatch: (action) => dispatch({ caseId, action }) };
}
