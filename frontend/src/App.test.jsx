// Integration test: renders the real app against a running backend.
// Run the backend first, then:  VITE_API_URL=http://localhost:5000 npm test
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";

const submit = () => userEvent.click(screen.getByRole("button", { name: /check payment/i }));

test("loads stats from the backend", async () => {
  render(<App />);
  expect(await screen.findByText("Checked")).toBeInTheDocument();
  expect(screen.queryByText(/can’t reach the backend/i)).not.toBeInTheDocument();
});

test("suspicious collect request is blocked with reasons", async () => {
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Refund collect request" }));
  await submit();
  const result = (await screen.findByText("Why")).closest("section");
  expect(within(result).getByText(/^■ Block$/)).toBeInTheDocument();
  expect(within(result).getByText("Collect request for a large amount")).toBeInTheDocument();
});

test("ordinary shop payment is allowed", async () => {
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: "Coffee at a shop" }));
  await submit();
  const result = (await screen.findByText("Why")).closest("section");
  expect(within(result).getByText(/^● Allow$/)).toBeInTheDocument();
  expect(within(result).getByText("Nothing unusual about this payment.")).toBeInTheDocument();
});

test("empty form shows field errors", async () => {
  render(<App />);
  await submit();
  expect(await screen.findByText("Enter a UPI ID like name@bank")).toBeInTheDocument();
  expect(screen.getByText("Required")).toBeInTheDocument();
});

test("sample payments fill the table and can be reviewed", async () => {
  render(<App />);
  await userEvent.click(screen.getByRole("button", { name: /add 20 sample payments/i }));
  await waitFor(() => expect(screen.getAllByRole("row").length).toBeGreaterThan(10));
  await userEvent.click(screen.getAllByRole("button", { name: "Fraud" })[0]);
  expect(await screen.findByText("Confirmed fraud")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Undo" }));
  await waitFor(() => expect(screen.queryByText("Confirmed fraud")).not.toBeInTheDocument());
});
