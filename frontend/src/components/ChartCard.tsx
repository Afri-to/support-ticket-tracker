import { useState, type ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  chart: ReactNode;
  table: ReactNode; // the same numbers as a table, for screen readers and exact values
}

/** A titled chart with a "Show table" toggle so no number is locked inside a picture. */
export function ChartCard({ title, subtitle, chart, table }: Props) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="card" aria-label={title}>
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="card-sub">{subtitle}</p>}
        </div>
        <button type="button" className="link-button" onClick={() => setShowTable((v) => !v)} aria-pressed={showTable}>
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>
      {showTable ? <div className="table-scroll">{table}</div> : chart}
    </section>
  );
}
