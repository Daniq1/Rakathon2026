import type { FieldValue, Issue } from "../types";
import { BAND_LABEL, LEVEL_LABEL, SEVERITY_LABEL, SOURCE_LABEL } from "../lib/labels";

export function ConfidenceBadge({ field }: { field: FieldValue | undefined }) {
  const band = field?.confidence_band ?? null;
  const score = field?.confidence;
  if (!band) return <span className="badge band-none" title="Jistota neurčena">—</span>;
  return (
    <span className={`badge band-${band}`} title={`Jistota ${BAND_LABEL[band]}`}>
      {score != null ? Math.round(score * 100) + " %" : BAND_LABEL[band]}
    </span>
  );
}

export function LevelBadge({ level }: { level: FieldValue["automation_level"] }) {
  if (!level) return null;
  return (
    <span className={`badge level level-${level}`} title={LEVEL_LABEL[level]}>
      {level}
    </span>
  );
}

const SOURCE_ICON: Record<FieldValue["source"], string> = {
  auto: "📄",
  computed: "∑",
  manual: "✎",
  admin: "⚙",
};

export function SourceIcon({ source }: { source: FieldValue["source"] | undefined }) {
  if (!source) return <span className="source-icon muted">·</span>;
  return (
    <span className="source-icon" title={SOURCE_LABEL[source]} aria-label={SOURCE_LABEL[source]}>
      {SOURCE_ICON[source]}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Issue["severity"] }) {
  return <span className={`badge sev-${severity}`}>{SEVERITY_LABEL[severity]}</span>;
}
