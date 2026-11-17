import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { HelpGlossaryDialog } from "./HelpGlossaryDialog";

describe("Help & Glossary", () => {
  it("filters terms and exposes workspace and source explanations", async () => {
    const user = userEvent.setup();
    render(<HelpGlossaryDialog onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: "Help & glossary" });
    const search = within(dialog).getByRole("textbox", { name: "Search help and glossary" });
    expect(search).toHaveFocus();
    expect(within(dialog).getByText("Market Overview")).toBeInTheDocument();
    expect(within(dialog).getByText(/Jujosmi does not read, extract, or use widget data/)).toBeInTheDocument();
    await user.type(search, "OHLCV");
    expect(within(dialog).getByText("OHLCV")).toBeInTheDocument();
    expect(within(dialog).queryByText("Revenue", { exact: true })).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}");
    expect(within(dialog).getByText("OHLCV")).toHaveFocus();
    fireEvent.click(within(dialog).getByText("OHLCV"));
    expect(dialog.querySelector("details")?.open).toBe(true);
    expect(dialog.querySelector("details p")?.textContent).toMatch(/open, high, low, close, and volume/i);
  });
});
