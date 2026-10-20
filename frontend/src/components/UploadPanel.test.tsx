import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadPanel } from "./UploadPanel";
import { mockFetch } from "../test/mockApi";

afterEach(() => vi.unstubAllGlobals());

const csv = () => new File(["ticket_id,agent\n"], "tickets.csv", { type: "text/csv" });

it("uploads a file and reports what happened to every row", async () => {
  const summary = {
    import_id: 1, filename: "tickets.csv", total_rows: 5000, imported: 4789, duplicates: 159,
    already_imported: 0, invalid: 52,
    errors: [{ line: 766, ticket_id: "TCK-000745", problems: [{ code: "UNKNOWN_PRIORITY", message: "'???' isn't one of Low, Medium, High, Critical." }] }],
  };
  const { calls } = mockFetch({ "/imports": summary });
  const onImported = vi.fn();
  render(<UploadPanel onImported={onImported} />);

  await userEvent.upload(screen.getByLabelText("CSV file"), csv());
  await userEvent.click(screen.getByRole("button", { name: "Import CSV" }));

  expect(await screen.findByRole("status")).toHaveTextContent("4,789 imported, 159 duplicates removed, 0 already imported, 52 invalid rows.");
  expect(screen.getByText(/Line 766 \(TCK-000745\)/)).toBeInTheDocument();
  expect(screen.getByText("and 44 more.")).toBeInTheDocument();
  expect(calls).toContain("POST /api/imports");
  expect(onImported).toHaveBeenCalledOnce();
});

it("shows the server's reason when a file is refused", async () => {
  mockFetch({
    "/imports": new Response(JSON.stringify({ detail: "Missing columns: category." }), { status: 422 }),
  });
  render(<UploadPanel onImported={vi.fn()} />);
  await userEvent.upload(screen.getByLabelText("CSV file"), csv());
  await userEvent.click(screen.getByRole("button", { name: "Import CSV" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Import failed: Missing columns: category.");
});
