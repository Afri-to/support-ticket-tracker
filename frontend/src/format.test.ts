import { count, dateTime, hours, parseDay, shortDay, toDay, weekEnd, weekLabel } from "./format";
import { filterQuery } from "./api";

describe("dates", () => {
  it("parses a day without shifting it across time zones", () => {
    expect(toDay(parseDay("2026-07-06"))).toBe("2026-07-06");
  });

  it("finds the Sunday that ends a week, across month ends", () => {
    expect(weekEnd("2026-07-06")).toBe("2026-07-12");
    expect(weekEnd("2026-07-27")).toBe("2026-08-02");
  });

  it("labels days and weeks", () => {
    expect(shortDay("2026-07-06")).toBe("Jul 6");
    expect(weekLabel("2026-07-27")).toBe("Jul 27 – Aug 2");
  });

  it("shows timestamps in UTC", () => {
    expect(dateTime("2026-07-06T23:30:00Z")).toBe("Jul 6, 11:30 PM");
  });
});

describe("numbers", () => {
  it("formats counts with separators", () => {
    expect(count(4789)).toBe("4,789");
  });

  it("formats hours, switching to days for long spans", () => {
    expect(hours("4.25")).toBe("4.3 h");
    expect(hours(72)).toBe("3.0 days");
    expect(hours(null)).toBe("–");
  });
});

describe("filterQuery", () => {
  it("is empty with no filters", () => {
    expect(filterQuery({ agentId: null, week: null }).toString()).toBe("");
  });

  it("turns a week into an inclusive Monday-to-Sunday range", () => {
    const q = filterQuery({ agentId: 3, week: "2026-07-06" });
    expect(q.get("agent_id")).toBe("3");
    expect(q.get("from")).toBe("2026-07-06");
    expect(q.get("to")).toBe("2026-07-12");
  });

  it("can leave out the week or the agent for comparison charts", () => {
    const f = { agentId: 3, week: "2026-07-06" };
    expect(filterQuery(f, { week: false }).has("from")).toBe(false);
    expect(filterQuery(f, { agent: false }).has("agent_id")).toBe(false);
  });
});
