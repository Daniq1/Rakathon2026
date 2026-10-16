import { useState, type DragEvent } from "react";
import { uploadDocuments, type UploadedFile } from "../api";
import { summarize } from "../lib/caseView";
import { CASE_STATUS_LABEL, bandOf, maskRc } from "../lib/labels";
import { href } from "../router";
import { useAllCases } from "../state/caseStore";

export function PatientsScreen() {
  const cases = useAllCases().map(summarize);
  const [uploaded, setUploaded] = useState<UploadedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);

  async function handleFiles(list: FileList | null) {
    if (!list?.length) return;
    const res = await uploadDocuments([...list]);
    setUploaded((u) => [...res, ...u]);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    void handleFiles(e.dataTransfer.files);
  }

  return (
    <div className="page">
      <h1>Pacienti</h1>
      <table className="table">
        <thead>
          <tr>
            <th>Pacient</th>
            <th>RČ</th>
            <th className="num">Dokumenty</th>
            <th>Stav případu</th>
            <th>Upozornění</th>
            <th className="num">Chybí povinných</th>
            <th className="num">Průměrná jistota</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => {
            const band = bandOf(c.avgConfidence);
            return (
              <tr key={c.caseId} className="clickable" onClick={() => (window.location.hash = href({ name: "case", caseId: c.caseId, field: null }))}>
                <td>
                  <a href={href({ name: "case", caseId: c.caseId, field: null })}>{c.pseudonym}</a>
                </td>
                <td className="mono">{maskRc(c.rcRaw)}</td>
                <td className="num">{c.documents}</td>
                <td>
                  <span className={`status status-${c.status}`}>{CASE_STATUS_LABEL[c.status]}</span>
                </td>
                <td>
                  <span className="issue-counts">
                    <span className="badge sev-error" title="chyby">{c.issues.error}</span>
                    <span className="badge sev-warning" title="varování">{c.issues.warning}</span>
                    <span className="badge sev-info" title="info">{c.issues.info}</span>
                  </span>
                </td>
                <td className="num">{c.missingRequired}</td>
                <td className="num">
                  {c.avgConfidence == null ? "—" : (
                    <span className={`badge band-${band}`}>{Math.round(c.avgConfidence * 100)} %</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Nahrát dokumenty</h2>
      <label
        className={dragOver ? "dropzone over" : "dropzone"}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <input type="file" multiple accept=".pdf,.txt,image/*" onChange={(e) => void handleFiles(e.target.files)} />
        <strong>Přetáhněte sem PDF nebo skeny</strong>
        <span className="muted">nebo klikněte a vyberte soubory (ambulantní zprávy, histologie, propouštěcí zprávy)</span>
      </label>
      {uploaded.length > 0 && (
        <>
          <p className="muted">
            Zpracování dokumentů zajistí backend (řez 2). Zatím se soubory jen evidují v prohlížeči.
          </p>
          <ul className="upload-list">
            {uploaded.map((f, i) => (
              <li key={i}>
                <span>{f.name}</span>
                <span className="muted">{(f.size / 1024).toFixed(0)} kB · čeká na zpracování</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
