interface Row {
  label: string;
  value: string;
  color?: string;
}

/** Shared tooltip body: a title line, then one row per series. Text stays in text colours. */
export function TooltipBox({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <div className="tooltip">
      <p className="tooltip-title">{title}</p>
      {rows.map((r) => (
        <div className="tooltip-row" key={r.label}>
          <span>
            {r.color && <i className="swatch" style={{ background: r.color }} />}
            {r.label}
          </span>
          <strong>{r.value}</strong>
        </div>
      ))}
    </div>
  );
}
