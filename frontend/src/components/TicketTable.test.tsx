import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TicketTable } from "./TicketTable";
import { mockFetch, sample } from "../test/mockApi";

afterEach(() => vi.unstubAllGlobals());
const noFilters = { agentId: null, week: null };

it("searches after typing pauses, not on every key", async () => {
  const { calls } = mockFetch({ "/tickets": sample.tickets });
  render(<TicketTable filters={noFilters} refreshKey={0} />);
  await screen.findByText("TCK-000001");
  const before = calls.length;
  await userEvent.type(screen.getByLabelText("Search tickets"), "jam");
  await waitFor(() => expect(calls.some((c) => c.includes("search=jam"))).toBe(true));
  expect(calls.slice(before).filter((c) => c.includes("search=")).length).toBe(1);
});

it("pages through results", async () => {
  const many = { total: 60, items: sample.tickets.items };
  const { calls } = mockFetch({ "/tickets": many });
  render(<TicketTable filters={noFilters} refreshKey={0} />);
  expect(await screen.findByText("1–25 of 60")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(calls.some((c) => c.includes("offset=25"))).toBe(true));
  expect(await screen.findByText("26–50 of 60")).toBeInTheDocument();
});

it("explains an empty search", async () => {
  mockFetch({ "/tickets": { total: 0, items: [] } });
  render(<TicketTable filters={noFilters} refreshKey={0} />);
  await userEvent.type(screen.getByLabelText("Search tickets"), "zzz");
  expect(await screen.findByText(/No tickets match "zzz"/)).toBeInTheDocument();
});
