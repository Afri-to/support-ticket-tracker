import { useEffect, useState } from "react";
import { api } from "../api";
import type { Filters, TicketPage } from "../types";
import { count, dateTime, hours } from "../format";

const PAGE_SIZE = 25;

/** Searchable, paged list of tickets for the current filters. */
export function TicketTable({ filters, refreshKey }: { filters: Filters; refreshKey: number }) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState(""); // search, applied after the person pauses typing
  const [page, setPage] = useState(0);
  const [data, setData] = useState<TicketPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = setTimeout(() => setQuery(search), 300);
    return () => clearTimeout(id);
  }, [search]);

  // New filters or a new search start again from the first page.
  useEffect(() => setPage(0), [filters, query, refreshKey]);

  useEffect(() => {
    let current = true;
    api
      .tickets(filters, query, PAGE_SIZE, page * PAGE_SIZE)
      .then((d) => current && (setData(d), setError(null)))
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [filters, query, page, refreshKey]);

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const first = total ? page * PAGE_SIZE + 1 : 0;
  const last = Math.min(total, (page + 1) * PAGE_SIZE);

  return (
    <section className="card" aria-label="Tickets">
      <div className="card-head">
        <div>
          <h2>Tickets</h2>
          <p className="card-sub">Newest first. Times are UTC.</p>
        </div>
        <label className="field">
          <span className="sr-only">Search tickets</span>
          <input
            type="search"
            placeholder="Search ID, agent, category, cause"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticket</th><th>Opened</th><th>Agent</th><th>Category</th><th>Root cause</th><th>Priority</th>
              <th className="num">Resolved in</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((t) => (
              <tr key={t.ticket_id}>
                <td className="mono">{t.ticket_id}</td>
                <td>{dateTime(t.opened_at)}</td>
                <td>{t.agent}</td>
                <td>{t.category}</td>
                <td>{t.root_cause}</td>
                <td><span className={`priority ${t.priority}`}>{t.priority}</span></td>
                <td className="num">{t.closed_at ? hours(t.resolve_hours) : <span className="open-badge">Open</span>}</td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr><td colSpan={7} className="muted">
                {query ? `No tickets match "${query}". Try a different search or clear the filters.` : "No tickets for these filters."}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <span>{total ? `${count(first)}–${count(last)} of ${count(total)}` : ""}</span>
        <span>
          <button type="button" onClick={() => setPage((p) => p - 1)} disabled={page === 0}>Previous</button>{" "}
          <button type="button" onClick={() => setPage((p) => p + 1)} disabled={page + 1 >= pages}>Next</button>
        </span>
      </div>
    </section>
  );
}
