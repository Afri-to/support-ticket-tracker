import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AgentKpi, RootCause, Week } from "../types";
import { count, hours, shortDay, weekLabel } from "../format";
import { useChartColors } from "../useChartColors";
import { ChartCard } from "./ChartCard";
import { TooltipBox } from "./Tooltip";

const AXIS = { fontSize: 12 };
// Faded marks outside the current filter keep context without competing.
const DIM = 0.3;

/* eslint-disable @typescript-eslint/no-explicit-any */
type TipProps = { active?: boolean; payload?: any[] };

export function WeeklyVolumeChart({ weeks, selectedWeek }: { weeks: Week[]; selectedWeek: string | null }) {
  const c = useChartColors();
  const Tip = ({ active, payload }: TipProps) =>
    active && payload?.length ? (
      <TooltipBox
        title={`Week of ${weekLabel(payload[0].payload.week_start)}`}
        rows={[
          { label: "Opened", value: count(payload[0].payload.opened), color: c["series-1"] },
          { label: "Closed", value: count(payload[0].payload.closed), color: c["series-2"] },
        ]}
      />
    ) : null;
  const dim = (w: Week) => (selectedWeek && w.week_start !== selectedWeek ? DIM : 1);
  return (
    <ChartCard
      title="Tickets per week"
      subtitle="Opened and closed by week (Mon–Sun)"
      chart={
        <>
          <ul className="legend" aria-hidden="true">
            <li><i className="swatch" style={{ background: c["series-1"] }} />Opened</li>
            <li><i className="swatch" style={{ background: c["series-2"] }} />Closed</li>
          </ul>
          <div className="chart">
            <ResponsiveContainer>
              <BarChart data={weeks} barGap={2} barCategoryGap="22%" margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                <CartesianGrid vertical={false} stroke={c.grid} />
                <XAxis dataKey="week_start" tickFormatter={shortDay} tick={{ ...AXIS, fill: c["text-muted"] }} tickLine={false} axisLine={{ stroke: c.grid }} minTickGap={12} />
                <YAxis allowDecimals={false} tick={{ ...AXIS, fill: c["text-muted"] }} tickLine={false} axisLine={false} />
                <Tooltip content={<Tip />} cursor={{ fill: c.grid, opacity: 0.6 }} />
                <Bar dataKey="opened" name="Opened" fill={c["series-1"]} radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {weeks.map((w) => <Cell key={w.week_start} fillOpacity={dim(w)} />)}
                </Bar>
                <Bar dataKey="closed" name="Closed" fill={c["series-2"]} radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {weeks.map((w) => <Cell key={w.week_start} fillOpacity={dim(w)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      }
      table={
        <table className="data-table">
          <thead><tr><th>Week</th><th className="num">Opened</th><th className="num">Closed</th></tr></thead>
          <tbody>
            {weeks.map((w) => (
              <tr key={w.week_start}><td>{weekLabel(w.week_start)}</td><td className="num">{count(w.opened)}</td><td className="num">{count(w.closed)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    />
  );
}

export function ResolveTimeChart({ weeks, selectedWeek }: { weeks: Week[]; selectedWeek: string | null }) {
  const c = useChartColors();
  const data = weeks.map((w) => ({ ...w, value: w.avg_resolve_hours === null ? null : Number(w.avg_resolve_hours) }));
  const Tip = ({ active, payload }: TipProps) =>
    active && payload?.length ? (
      <TooltipBox
        title={`Week of ${weekLabel(payload[0].payload.week_start)}`}
        rows={[{ label: "Average time to resolve", value: hours(payload[0].payload.value) }]}
      />
    ) : null;
  return (
    <ChartCard
      title="Average time to resolve"
      subtitle="Hours from opened to closed, by week opened"
      chart={
        <div className="chart">
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke={c.grid} />
              <XAxis dataKey="week_start" tickFormatter={shortDay} tick={{ ...AXIS, fill: c["text-muted"] }} tickLine={false} axisLine={{ stroke: c.grid }} minTickGap={12} />
              <YAxis tick={{ ...AXIS, fill: c["text-muted"] }} tickLine={false} axisLine={false} unit=" h" />
              <Tooltip content={<Tip />} cursor={{ stroke: c["text-muted"], strokeDasharray: "3 3" }} />
              <Line
                dataKey="value"
                stroke={c["series-1"]}
                strokeWidth={2}
                isAnimationActive={false}
                connectNulls
                dot={(p: any) => {
                  const on = selectedWeek !== null && p.payload.week_start === selectedWeek;
                  return (
                    <circle key={p.key ?? p.index} cx={p.cx} cy={p.cy} r={on ? 6 : 3} fill={on ? c["series-1"] : c.surface} stroke={c["series-1"]} strokeWidth={2} />
                  );
                }}
                activeDot={{ r: 5, stroke: c.surface, strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      }
      table={
        <table className="data-table">
          <thead><tr><th>Week</th><th className="num">Average time to resolve</th></tr></thead>
          <tbody>
            {weeks.map((w) => (
              <tr key={w.week_start}><td>{weekLabel(w.week_start)}</td><td className="num">{hours(w.avg_resolve_hours)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    />
  );
}

export function RootCausesChart({ causes }: { causes: RootCause[] }) {
  const c = useChartColors();
  const data = causes.map((r) => ({ ...r, label: r.root_cause, share: Number(r.share_pct) }));
  const Tip = ({ active, payload }: TipProps) =>
    active && payload?.length ? (
      <TooltipBox
        title={`${payload[0].payload.root_cause} (${payload[0].payload.category})`}
        rows={[
          { label: "Tickets", value: count(payload[0].payload.tickets) },
          { label: "Share of all tickets", value: `${payload[0].payload.share_pct}%` },
        ]}
      />
    ) : null;
  return (
    <ChartCard
      title="Top root causes"
      subtitle="Share of tickets in the current filter"
      chart={
        <div className="chart">
          <ResponsiveContainer>
            <BarChart data={data} layout="vertical" barCategoryGap="22%" margin={{ top: 0, right: 44, bottom: 0, left: 0 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" width={150} tick={{ ...AXIS, fill: c["text-secondary"] }} tickLine={false} axisLine={false} />
              <Tooltip content={<Tip />} cursor={{ fill: c.grid, opacity: 0.6 }} />
              <Bar
                dataKey="tickets"
                fill={c["series-1"]}
                radius={[0, 4, 4, 0]}
                isAnimationActive={false}
                label={{ position: "right", fontSize: 12, fill: c["text-secondary"], formatter: (v: any) => count(Number(v)) }}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      }
      table={
        <table className="data-table">
          <thead><tr><th>Root cause</th><th>Category</th><th className="num">Tickets</th><th className="num">Share</th></tr></thead>
          <tbody>
            {causes.map((r) => (
              <tr key={`${r.category}-${r.root_cause}`}><td>{r.root_cause}</td><td>{r.category}</td><td className="num">{count(r.tickets)}</td><td className="num">{r.share_pct}%</td></tr>
            ))}
          </tbody>
        </table>
      }
    />
  );
}

export function AgentsChart({ agents, selectedAgent }: { agents: AgentKpi[]; selectedAgent: number | null }) {
  const c = useChartColors();
  const Tip = ({ active, payload }: TipProps) =>
    active && payload?.length ? (
      <TooltipBox
        title={payload[0].payload.agent}
        rows={[
          { label: "Tickets", value: count(payload[0].payload.tickets) },
          { label: "Still open", value: count(payload[0].payload.open) },
          { label: "Average time to resolve", value: hours(payload[0].payload.avg_resolve_hours) },
        ]}
      />
    ) : null;
  return (
    <ChartCard
      title="Tickets per agent"
      subtitle="All agents, selected agent highlighted"
      chart={
        <div className="chart">
          <ResponsiveContainer>
            <BarChart data={agents} layout="vertical" barCategoryGap="22%" margin={{ top: 0, right: 44, bottom: 0, left: 0 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="agent" width={130} tick={{ ...AXIS, fill: c["text-secondary"] }} tickLine={false} axisLine={false} interval={0} />
              <Tooltip content={<Tip />} cursor={{ fill: c.grid, opacity: 0.6 }} />
              <Bar
                dataKey="tickets"
                fill={c["series-1"]}
                radius={[0, 4, 4, 0]}
                isAnimationActive={false}
                label={{ position: "right", fontSize: 12, fill: c["text-secondary"], formatter: (v: any) => count(Number(v)) }}
              >
                {agents.map((a) => (
                  <Cell key={a.agent_id} fillOpacity={selectedAgent && a.agent_id !== selectedAgent ? DIM : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      }
      table={
        <table className="data-table">
          <thead><tr><th>Agent</th><th className="num">Tickets</th><th className="num">Open</th><th className="num">Avg. to resolve</th></tr></thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.agent_id}><td>{a.agent}</td><td className="num">{count(a.tickets)}</td><td className="num">{count(a.open)}</td><td className="num">{hours(a.avg_resolve_hours)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    />
  );
}
