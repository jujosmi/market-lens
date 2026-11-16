import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ExpandableResearchCard } from "./ExpandableResearchCard";

afterEach(() => { document.body.style.overflow = ""; });

describe("ExpandableResearchCard", () => {
  it("opens with keyboard activation, traps focus, closes with Escape, and restores focus", async () => {
    const user = userEvent.setup();
    render(<ExpandableResearchCard title="Sample financial metric" preview={<b>$10.00</b>}><p>Existing sample detail.</p><button type="button">More detail</button></ExpandableResearchCard>);
    const trigger = screen.getByRole("button", { name: "Expand Sample financial metric" });
    trigger.focus();
    await user.keyboard("{Enter}");
    const dialog = screen.getByRole("dialog", { name: "Sample financial metric" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close Sample financial metric details" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "More detail" })).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("closes when the user clicks outside the dialog", async () => {
    const user = userEvent.setup();
    render(<ExpandableResearchCard title="Company profile" preview={<span>Profile</span>}><p>Fixture details.</p></ExpandableResearchCard>);
    await user.click(screen.getByRole("button", { name: "Expand Company profile" }));
    expect(screen.getByRole("dialog", { name: "Company profile" })).toBeInTheDocument();
    await user.click(screen.getByRole("dialog").parentElement!);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
