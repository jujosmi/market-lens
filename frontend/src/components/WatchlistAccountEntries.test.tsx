import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WatchlistWorkspace } from "./WorkspaceViews";
import { tickerFixtures } from "../data/fixtures";

describe("exchange-qualified account watchlist presentation", () => {
  it("keeps same-symbol entries distinct and removes only the selected venue", async () => {
    const remove = vi.fn(async () => true);
    render(<WatchlistWorkspace
      dataMode="fixtures"
      selectedSymbol="AAPL"
      selectedSecExchange="NASDAQ"
      selectedTicker={tickerFixtures[1]!}
      watchlist={["AAPL"]}
      accountEntries={[
        { id: "aapl-nasdaq", symbol: "AAPL", exchange: "NASDAQ" },
        { id: "aapl-nyse", symbol: "AAPL", exchange: "NYSE" },
      ]}
      onSelectTicker={vi.fn()}
      onAddTicker={vi.fn(async () => true)}
      onRemoveTicker={remove}
      onNavigate={vi.fn()}
      persistent
      accountLoading={false}
    />);

    expect(screen.getByRole("heading", { name: "2 tickers" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Saved account watchlist" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove AAPL from NYSE watchlist entry" }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("AAPL", "NYSE"));
    expect(remove).toHaveBeenCalledTimes(1);
  });
});
