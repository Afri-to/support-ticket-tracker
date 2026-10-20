import type { Summary } from "../types";
import { count, hours } from "../format";

/** Headline numbers. A number this important is a tile, not a chart. */
export function StatTiles({ summary }: { summary: Summary }) {
  const openShare = summary.total ? Math.round((100 * summary.open) / summary.total) : 0;
  return (
    <div className="tiles">
      <div className="tile">
        <p className="tile-label">Tickets</p>
        <p className="tile-value">{count(summary.total)}</p>
      </div>
      <div className="tile">
        <p className="tile-label">Still open</p>
        <p className="tile-value">{count(summary.open)}</p>
        <p className="tile-note">{openShare}% of tickets</p>
      </div>
      <div className="tile">
        <p className="tile-label">Average time to resolve</p>
        <p className="tile-value">{hours(summary.avg_resolve_hours)}</p>
      </div>
      <div className="tile">
        <p className="tile-label">Median time to resolve</p>
        <p className="tile-value">{hours(summary.median_resolve_hours)}</p>
        <p className="tile-note">Half of tickets close faster than this</p>
      </div>
    </div>
  );
}
