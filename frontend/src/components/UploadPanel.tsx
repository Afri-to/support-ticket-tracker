import { useRef, useState } from "react";
import { api } from "../api";
import type { ImportSummary } from "../types";
import { count } from "../format";

const SAMPLE_URL = "https://raw.githubusercontent.com/Afri-to/support-ticket-tracker/main/data/sample_tickets.csv";
const SHOWN_ERRORS = 8;

/** Upload a CSV export and say exactly what happened to its rows. */
export function UploadPanel({ onImported }: { onImported: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const summary = await api.upload(file);
      setResult(summary);
      setFile(null);
      if (input.current) input.current.value = "";
      onImported();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label="Import tickets">
      <div className="card-head">
        <div>
          <h2>Import tickets</h2>
          <p className="card-sub">
            CSV with ticket_id, agent, category, root_cause, priority, opened_at, closed_at.{" "}
            <a href={SAMPLE_URL}>Download the sample file</a> (5,000 fake tickets).
          </p>
        </div>
      </div>
      <div className="upload">
        <label>
          <span className="sr-only">CSV file</span>
          <input ref={input} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <button type="button" className="primary" onClick={submit} disabled={!file || busy}>
          {busy ? "Importing…" : "Import CSV"}
        </button>
      </div>
      {error && <p className="error-text" role="alert">Import failed: {error}</p>}
      {result && (
        <div className="result" role="status">
          <p>
            <strong>{result.filename}</strong>: {count(result.imported)} imported, {count(result.duplicates)} duplicates removed,{" "}
            {count(result.already_imported)} already imported, {count(result.invalid)} invalid rows.
          </p>
          {result.errors.length > 0 && (
            <>
              <p className="muted">Rows that were rejected:</p>
              <ul>
                {result.errors.slice(0, SHOWN_ERRORS).map((e) => (
                  <li key={e.line}>
                    Line {e.line}{e.ticket_id ? ` (${e.ticket_id})` : ""}: {e.problems.map((p) => p.message).join(" ")}
                  </li>
                ))}
              </ul>
              {result.invalid > SHOWN_ERRORS && (
                <p className="muted">and {count(result.invalid - SHOWN_ERRORS)} more.</p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
