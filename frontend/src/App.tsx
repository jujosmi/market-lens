import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from "motion/react";
import { Activity, ArrowDown, ArrowDownRight, ArrowUpRight, ChevronDown, CircleHelp, HelpCircle, Search, Settings2, ShieldCheck, SlidersHorizontal, Star, TrendingUp, X } from "lucide-react";
import { PriceChart, type ChartPreviewState } from "./components/PriceChart";
import { ExpandableResearchCard } from "./components/ExpandableResearchCard";
import { LandingPage } from "./components/LandingPage";
import { SpotlightCard } from "./components/SpotlightCard";
import { Sidebar } from "./components/Sidebar";
import { chartIntervals, pulseFixtures, tickerFixtures, type ChartInterval, type ChartStyle } from "./data/fixtures";
import { ApiRequestError, chartResolutions, fetchChart, fetchOverview, fetchTechnicalAnalysis, fetchTickerSearch, fetchWatchlistSummaries, type ApiEnvelope, type ChartData, type ChartResolution, type OverviewData, type TechnicalAnalysisData, type WatchlistSummaryData } from "./data/apiClient";
import type { DataMode, Workspace } from "./types";
import { tradingViewSymbols, tradingViewTickerSymbols } from "./data/tradingViewSymbols";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AuthAccountMenu } from "./auth/AuthAccountMenu";
import { createWatchlistRepository } from "./auth/watchlistRepository";
import { accountWatchlistForUser, accountWatchlistIsLoading, type AccountWatchlistState } from "./auth/watchlistState";
import { HelpGlossaryDialog } from "./components/HelpGlossaryDialog";
import { PreferencesDialog } from "./components/PreferencesDialog";
import { DEFAULT_PREFERENCES, readPreferences, writePreferences, type AppPreferences } from "./preferences";
import { isKestrelPreviewEnabled, isTradingViewWidgetEnabled } from "./releaseFeatures";

const KestrelResearchPreview = import.meta.env.DEV ? lazy(() => import("./components/KestrelResearchPreview").then((module) => ({ default: module.KestrelResearchPreview }))) : null;
const TradingViewAdvancedChart = lazy(() => import("./components/TradingViewAdvancedChart").then((module) => ({ default: module.TradingViewAdvancedChart })));
const DiscoveryWorkspace = lazy(() => import("./components/WorkspaceViews").then((module) => ({ default: module.DiscoveryWorkspace })));
const ResearchWorkspace = lazy(() => import("./components/WorkspaceViews").then((module) => ({ default: module.ResearchWorkspace })));
const WatchlistWorkspace = lazy(() => import("./components/WorkspaceViews").then((module) => ({ default: module.WatchlistWorkspace })));
const tradingViewWidgetEnabled = isTradingViewWidgetEnabled();

const workspaceLabels: Record<Workspace, string> = { overview: "Market Overview", discovery: "Discovery", research: "Company Research", watchlist: "Watchlist" };
const workspacePaths: Record<Workspace, string> = { overview: "/market-overview", discovery: "/discovery", research: "/research", watchlist: "/watchlist" };
const sectorActivityFixtures = [{ name: "Technology", value: 82 }, { name: "Industrials", value: 67 }, { name: "Healthcare", value: 58 }, { name: "Financials", value: 44 }];
const GUEST_WATCHLIST_KEY = "jujosmi_trade_guest_watchlist_v1";
function readGuestWatchlist() {
  try {
    const saved = window.sessionStorage.getItem(GUEST_WATCHLIST_KEY);
    if (saved) {
      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.every((symbol) => typeof symbol === "string" && /^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol))) return [...new Set(parsed)];
    }
  } catch { /* Session storage may be disabled; guest mode remains in memory. */ }
  return ["NVDA", "AAPL", "MSFT", "AMZN"];
}
function routeState() {
  const path = window.location.pathname;
  const workspace = (Object.entries(workspacePaths).find(([, route]) => route === path)?.[0] ?? "overview") as Workspace;
  return { workspace, landing: path === "/welcome" };
}

function sparklinePath(values: readonly number[]) {
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  return values.map((value, index) => {
    const x = (index / (values.length - 1)) * 120;
    const y = 26 - ((value - min) / span) * 22;
    return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function TradeApp() {
  const initialRoute = routeState();
  const systemReducedMotion = Boolean(useReducedMotion());
  const [preferences, setPreferences] = useState<AppPreferences>(() => readPreferences(Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches)));
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>(initialRoute.workspace);
  const [showLanding, setShowLanding] = useState(initialRoute.landing);
  const [selectedSymbol, setSelectedSymbol] = useState(preferences.defaultSymbol);
  const [selectedSecExchange, setSelectedSecExchange] = useState<string | null>(null);
  const [guestWatchlist, setGuestWatchlist] = useState(readGuestWatchlist);
  const [accountWatchlistState, setAccountWatchlistState] = useState<AccountWatchlistState>({ ownerId: null, rows: [], loading: false, error: "" });
  const [watchlistRetry, setWatchlistRetry] = useState(0);
  const [confirmGuestImport, setConfirmGuestImport] = useState(false);
  const [guestImportState, setGuestImportState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const auth = useAuth();
  const activeUserId = useRef<string | null>(auth.user?.id ?? null);
  activeUserId.current = auth.user?.id ?? null;
  const accountWatchlist = accountWatchlistForUser(accountWatchlistState, auth.user?.id ?? null);
  const accountWatchlistLoading = accountWatchlistIsLoading(accountWatchlistState, auth.user?.id ?? null);
  const watchlistError = auth.user && accountWatchlistState.ownerId === auth.user.id ? accountWatchlistState.error : "";
  const guestWatchlistToImport = guestWatchlist.filter((symbol) => !accountWatchlist.some((entry) => entry.symbol === symbol && entry.exchange === exchangeFor(symbol)));
  const watchlist = auth.loading ? [] : auth.user ? [...new Set(accountWatchlist.map((entry) => entry.symbol))] : guestWatchlist;
  const sidebarWatchlistEntries = auth.user ? accountWatchlist.map(({ symbol, exchange }) => ({ symbol, exchange })) : guestWatchlist.map((symbol) => ({ symbol, exchange: exchangeFor(symbol) }));
  const [range, setRange] = useState<ChartInterval>("1M");
  const [resolution, setResolution] = useState<ChartResolution>("1d");
  const [chartStyle, setChartStyle] = useState<ChartStyle>("Area");
  const [previewDataState, setPreviewDataState] = useState<ChartPreviewState>("ready");
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<"preferences" | "help" | null>(null);
  const [helpQuery, setHelpQuery] = useState("");
  const [expandedChart, setExpandedChart] = useState(false);
  const [showSummary, setShowSummary] = useState(true);
  const [saved, setSaved] = useState(watchlist.includes(selectedSymbol));
  const [dataMode, setDataMode] = useState<DataMode>("public");
  const [overviewState, setOverviewState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [overviewEnvelope, setOverviewEnvelope] = useState<ApiEnvelope<OverviewData> | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [analysisEnvelope, setAnalysisEnvelope] = useState<ApiEnvelope<TechnicalAnalysisData> | null>(null);
  const [analysisState, setAnalysisState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [chartEnvelope, setChartEnvelope] = useState<ApiEnvelope<ChartData> | null>(null);
  const [chartState, setChartState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [chartError, setChartError] = useState<string | null>(null);
  const [chartRetry, setChartRetry] = useState(0);
  const [tickerSearchEnvelope, setTickerSearchEnvelope] = useState<ApiEnvelope<{ query: string; results: { symbol: string }[] }> | null>(null);
  const [tickerSearchState, setTickerSearchState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [tickerSearchError, setTickerSearchError] = useState<string | null>(null);
  const [overviewWatchlist, setOverviewWatchlist] = useState<ApiEnvelope<WatchlistSummaryData> | null>(null);
  const [overviewWatchlistError, setOverviewWatchlistError] = useState("");
  const [overviewWatchlistState, setOverviewWatchlistState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const reduced = systemReducedMotion || preferences.reduceAnimations;

  useEffect(() => { writePreferences(preferences); }, [preferences]);

  useEffect(() => {
    try { window.sessionStorage.setItem(GUEST_WATCHLIST_KEY, JSON.stringify(guestWatchlist)); } catch { /* Guest list still works in memory. */ }
  }, [guestWatchlist]);

  useEffect(() => {
    let active = true;
    if (auth.loading) return () => { active = false; };
    if (!auth.user || !auth.client) {
      setAccountWatchlistState({ ownerId: null, rows: [], loading: false, error: "" });
      setConfirmGuestImport(false);
      setGuestImportState("idle");
      return () => { active = false; };
    }
    const ownerId = auth.user.id;
    const repository = createWatchlistRepository(auth.client, ownerId);
    setAccountWatchlistState({ ownerId, rows: [], loading: true, error: "" });
    void repository.list().then((rows) => {
      if (active && activeUserId.current === ownerId) setAccountWatchlistState({ ownerId, rows, loading: false, error: "" });
    }).catch(() => {
      if (active && activeUserId.current === ownerId) setAccountWatchlistState({ ownerId, rows: [], loading: false, error: "Saved watchlist could not be loaded. Retry after confirming your session." });
    });
    return () => { active = false; };
  }, [auth.loading, auth.user?.id, auth.client, watchlistRetry]);

  useEffect(() => {
    if (auth.loading || accountWatchlistLoading) return;
    setSaved(isWatchlisted(selectedSymbol, selectedSecExchange ?? exchangeFor(selectedSymbol)));
  }, [auth.loading, accountWatchlistLoading, auth.user?.id, watchlist.join(","), accountWatchlist.map((row) => `${row.symbol}:${row.exchange}`).join(","), selectedSymbol, selectedSecExchange]);

  const ticker = tickerFixtures.find((item) => item.symbol === selectedSymbol) ?? tickerFixtures[0]!;
  const engineLast = analysisEnvelope?.data?.indicators.last ?? null;
  const engineChange = analysisEnvelope?.data?.indicators.change ?? null;
  const displayedPrice = dataMode === "public" ? null : dataMode === "fastapi" ? engineLast : Number(ticker.price);
  const displayedChange = dataMode === "public" ? null : dataMode === "fastapi" ? engineChange : Number.parseFloat(ticker.change.replace("−", "-").replace("+", ""));
  const displayedChartValues = dataMode === "public" ? [] : dataMode === "fastapi"
    ? chartEnvelope?.data?.symbol === ticker.symbol ? chartEnvelope.data.bars.map((bar) => bar.close) : []
    : ticker.series;
  const displayedSectorActivity = dataMode === "public" ? [] : dataMode === "fastapi" ? overviewEnvelope?.data?.sector_activity ?? [] : sectorActivityFixtures;
  const localMatches = useMemo(() => tickerFixtures.filter((item) => `${item.symbol} ${item.name}`.toLowerCase().includes(search.toLowerCase())).slice(0, 5), [search]);
  const apiMatches = tickerSearchEnvelope?.data?.results.map((item) => tickerFixtures.find((fixture) => fixture.symbol === item.symbol)).filter((item): item is (typeof tickerFixtures)[number] => Boolean(item)) ?? [];
  const matches = dataMode === "fastapi" ? apiMatches : dataMode === "public" ? tickerFixtures.filter((item) => tradingViewTickerSymbols.includes(item.symbol) && item.symbol.toLowerCase().includes(search.toLowerCase())).slice(0, 5) : localMatches;

  useEffect(() => {
    if (dataMode !== "fastapi" || activeWorkspace !== "overview") {
      setOverviewState("idle");
      setOverviewEnvelope(null);
      setOverviewError(null);
      return;
    }
    const controller = new AbortController();
    setOverviewState("loading");
    setOverviewError(null);
    fetchOverview(controller.signal).then((response) => {
      setOverviewEnvelope(response);
      setOverviewState("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setOverviewEnvelope(null);
      setOverviewError(error instanceof ApiRequestError ? error.message : "The local API demo could not complete the request.");
      setOverviewState("error");
    });
    return () => controller.abort();
  }, [dataMode, activeWorkspace]);

  useEffect(() => {
    if (dataMode !== "fastapi" || activeWorkspace !== "overview" || !watchlist.length) {
      setOverviewWatchlist(null); setOverviewWatchlistError(""); setOverviewWatchlistState("idle"); return;
    }
    const controller = new AbortController();
    setOverviewWatchlistState("loading"); setOverviewWatchlistError("");
    fetchWatchlistSummaries(watchlist.slice(0, 4), controller.signal).then((response) => {
      setOverviewWatchlist(response); setOverviewWatchlistState("ready");
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) {
        setOverviewWatchlist(null);
        setOverviewWatchlistError(cause instanceof ApiRequestError ? cause.message : "The local Python Watchlist summary could not complete the request.");
        setOverviewWatchlistState("error");
      }
    });
    return () => controller.abort();
  }, [dataMode, activeWorkspace, watchlist.join(",")]);

  useEffect(() => {
    if (dataMode !== "fastapi" || activeWorkspace !== "overview") {
      setAnalysisState("idle"); setAnalysisEnvelope(null); setAnalysisError(null); return;
    }
    const controller = new AbortController();
    setAnalysisState("loading"); setAnalysisError(null);
    fetchTechnicalAnalysis(selectedSymbol, controller.signal).then((response) => {
      setAnalysisEnvelope(response); setAnalysisState("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setAnalysisEnvelope(null); setAnalysisError(error instanceof ApiRequestError ? error.message : "The Python analysis demo could not complete the request."); setAnalysisState("error");
    });
    return () => controller.abort();
  }, [dataMode, activeWorkspace, selectedSymbol]);

  useEffect(() => {
    if (dataMode !== "fastapi" || activeWorkspace !== "overview") {
      setChartState("idle"); setChartEnvelope(null); setChartError(null); return;
    }
    const controller = new AbortController();
    setChartState("loading"); setChartError(null);
    fetchChart(selectedSymbol, range, resolution, controller.signal).then((response) => {
      setChartEnvelope(response); setChartState("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setChartEnvelope(null); setChartError(error instanceof ApiRequestError ? error.message : "The Python chart demo could not complete the request."); setChartState("error");
    });
    return () => controller.abort();
  }, [dataMode, activeWorkspace, selectedSymbol, range, resolution, chartRetry]);

  useEffect(() => {
    if (dataMode !== "fastapi" || !search.trim()) {
      setTickerSearchState("idle"); setTickerSearchEnvelope(null); setTickerSearchError(null); return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setTickerSearchState("loading"); setTickerSearchError(null);
      fetchTickerSearch(search.trim(), controller.signal).then((response) => {
        setTickerSearchEnvelope(response); setTickerSearchState("ready");
      }).catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setTickerSearchEnvelope(null); setTickerSearchError(error instanceof ApiRequestError ? error.message : "Ticker search could not complete."); setTickerSearchState("error");
      });
    }, 220);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [dataMode, search]);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openTickerSearch();
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setExpandedChart(false);
        setMobileOpen(false);
        setActivePanel(null);
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [activeWorkspace, dataMode, showLanding]);

  useEffect(() => {
    function syncRoute() {
      const route = routeState();
      setActiveWorkspace(route.workspace);
      setShowLanding(route.landing);
    }
    window.addEventListener("popstate", syncRoute);
    return () => window.removeEventListener("popstate", syncRoute);
  }, []);

  function chooseTicker(symbol: string, exchange?: string) {
    setSelectedSymbol(symbol);
    setSelectedSecExchange(exchange ?? null);
    setSearch("");
    setSearchOpen(false);
    setSaved(isWatchlisted(symbol, exchange));
  }

  function toggleWatchlist() {
    const exchange = selectedSecExchange ?? exchangeFor(ticker.symbol);
    if (isWatchlisted(ticker.symbol, exchange)) void removeWatchlistTicker(ticker.symbol, exchange);
    else void addWatchlistTicker(ticker.symbol, exchange);
  }

  function isWatchlisted(symbol: string, exchange?: string) {
    if (!auth.user) return guestWatchlist.includes(symbol);
    const normalizedExchange = (exchange ?? exchangeFor(symbol)).toUpperCase();
    return accountWatchlist.some((entry) => entry.symbol === symbol && entry.exchange.toUpperCase() === normalizedExchange);
  }

  function exchangeFor(symbol: string) {
    return tickerFixtures.find((item) => item.symbol === symbol)?.exchange?.toUpperCase().replace(/[^A-Z0-9._-]/g, "") ?? "";
  }

  async function addWatchlistTicker(symbol: string, exchange?: string): Promise<boolean> {
    const normalizedExchange = exchange ?? exchangeFor(symbol);
    if (!auth.user || !auth.client) {
      setGuestWatchlist((current) => current.includes(symbol) ? current : [...current, symbol]);
      if (symbol === selectedSymbol) setSaved(true);
      return true;
    }
    const ownerId = auth.user.id;
    const repository = createWatchlistRepository(auth.client, ownerId);
    try {
      await repository.add(symbol, normalizedExchange);
      const rows = await repository.list();
      if (activeUserId.current === ownerId) setAccountWatchlistState({ ownerId, rows, loading: false, error: "" });
      if (activeUserId.current === ownerId && symbol === selectedSymbol && normalizedExchange.toUpperCase() === (selectedSecExchange ?? exchangeFor(symbol)).toUpperCase()) setSaved(true);
      return true;
    } catch (cause) {
      if (activeUserId.current === ownerId) setAccountWatchlistState((current) => ({ ...current, ownerId, loading: false, error: cause instanceof Error ? cause.message : "Saved watchlist could not be updated." }));
      return false;
    }
  }

  async function removeWatchlistTicker(symbol: string, exchange?: string): Promise<boolean> {
    const normalizedExchange = exchange ?? exchangeFor(symbol);
    if (!auth.user || !auth.client) {
      setGuestWatchlist((current) => current.filter((item) => item !== symbol));
      if (symbol === selectedSymbol) setSaved(false);
      return true;
    }
    const ownerId = auth.user.id;
    const repository = createWatchlistRepository(auth.client, ownerId);
    try {
      for (const row of accountWatchlist.filter((item) => item.symbol === symbol && item.exchange.toUpperCase() === normalizedExchange.toUpperCase())) await repository.remove(row.id);
      const rows = await repository.list();
      if (activeUserId.current === ownerId) setAccountWatchlistState({ ownerId, rows, loading: false, error: "" });
      if (activeUserId.current === ownerId && symbol === selectedSymbol && normalizedExchange.toUpperCase() === (selectedSecExchange ?? exchangeFor(symbol)).toUpperCase()) setSaved(false);
      return true;
    } catch (cause) {
      if (activeUserId.current === ownerId) setAccountWatchlistState((current) => ({ ...current, ownerId, loading: false, error: cause instanceof Error ? cause.message : "Saved watchlist could not be updated." }));
      return false;
    }
  }

  async function importGuestWatchlist(): Promise<boolean> {
    if (!auth.user || !auth.client || !guestWatchlist.length) return false;
    const ownerId = auth.user.id;
    const repository = createWatchlistRepository(auth.client, ownerId);
    setGuestImportState("saving");
    try {
      await repository.importSymbols(guestWatchlist, Object.fromEntries(guestWatchlist.map((symbol) => [symbol, exchangeFor(symbol)])));
      const rows = await repository.list();
      if (activeUserId.current === ownerId) setAccountWatchlistState({ ownerId, rows, loading: false, error: "" });
      setGuestImportState("saved");
      setConfirmGuestImport(false);
      return true;
    } catch (cause) {
      setGuestImportState("error");
      if (activeUserId.current === ownerId) setAccountWatchlistState((current) => ({ ...current, ownerId, loading: false, error: cause instanceof Error ? cause.message : "Guest watchlist import did not complete." }));
      return false;
    }
  }

  function moveWorkspace(workspace: Workspace) {
    setActiveWorkspace(workspace);
    setShowLanding(false);
    if (window.location.pathname !== workspacePaths[workspace]) window.history.pushState({ workspace }, "", workspacePaths[workspace]);
    setMobileOpen(false);
  }

  function openTickerSearch() {
    if (showLanding || activeWorkspace !== "overview") moveWorkspace("overview");
    setSearchOpen(dataMode !== "public");
    window.setTimeout(() => document.getElementById("ticker-search")?.focus(), 0);
  }

  function updatePreferences(next: AppPreferences) {
    setPreferences(next);
    if (next.defaultSymbol !== preferences.defaultSymbol) setSelectedSymbol(next.defaultSymbol);
  }

  function resetPreferences() {
    const resetValue = { ...DEFAULT_PREFERENCES, reduceAnimations: systemReducedMotion };
    setPreferences(resetValue);
    setSelectedSymbol(resetValue.defaultSymbol);
  }

  function changeDataMode(next: DataMode) {
    setDataMode(next);
    if (next === "public") moveWorkspace("overview");
  }

  function openPublicCharts() {
    setDataMode("public");
    moveWorkspace("overview");
    setSearchOpen(false);
  }

  function openHelp(query = "") {
    setHelpQuery(query);
    setActivePanel("help");
  }

  function enterTerminal() { moveWorkspace("overview"); }
  if (showLanding) return <MotionConfig reducedMotion={reduced ? "always" : "user"}><LandingPage onEnter={enterTerminal} /></MotionConfig>;

  return (
    <MotionConfig reducedMotion={reduced ? "always" : "user"}><div className={`app-frame ${reduced ? "reduce-motion" : ""}`}>
      <div className="ambient ambient-a" /><div className="ambient ambient-b" />
      <Sidebar active={activeWorkspace} onChange={moveWorkspace} collapsed={preferences.sidebarCollapsed} onCollapse={() => updatePreferences({ ...preferences, sidebarCollapsed: !preferences.sidebarCollapsed })} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} watchlist={watchlist} watchlistEntries={sidebarWatchlistEntries} onSelectTicker={chooseTicker} onSearch={openTickerSearch} onPreferences={() => setActivePanel("preferences")} onHelp={() => openHelp()} onPublicCharts={openPublicCharts} dataMode={dataMode} accountName={auth.user?.email ?? "Jujosmi Labs"} accountStatus={auth.loading ? "Restoring session" : auth.user ? "Account watchlist" : !auth.enabled ? "Guest · sign-in disabled" : auth.configured ? "Guest · sign-in available" : "Guest · accounts not configured"} />
      <main className="main-region">
        <header className="topbar">
          <div className="topbar-left"><button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><SlidersHorizontal size={17} /></button><a className="breadcrumb-muted brand-home" href="https://jujosmi.com" aria-label="Visit Jujosmi.com">Jujosmi Trade</a><span className="breadcrumb-slash">/</span><span className="breadcrumb-current">{workspaceLabels[activeWorkspace]}</span>{import.meta.env.DEV && <span className="prototype-pill"><span /> PROTOTYPE</span>}</div>
          <div className="topbar-actions">{import.meta.env.DEV && <><label className="data-mode-control"><span className="sr-only">Data mode</span><select aria-label="Data mode" value={dataMode} onChange={(event) => changeDataMode(event.target.value as DataMode)}><option value="public">Public chart (TradingView)</option><option value="fixtures">Offline fixtures (dev)</option><option value="fastapi">FastAPI demo (synthetic)</option></select><ChevronDown size={11} /></label><span className="fixture-indicator"><span className="fixture-indicator-dot" /> {dataMode === "public" ? "PUBLIC CHART" : dataMode === "fastapi" ? "LOCAL API · SYNTHETIC" : "OFFLINE · SYNTHETIC"}</span></>}<button className="icon-button top-icon" aria-label="Open Help and glossary" title="Help & glossary" onClick={() => openHelp()}><HelpCircle size={17} /></button><button className="icon-button top-icon" aria-label="Open Preferences" title="Preferences" onClick={() => setActivePanel("preferences")}><Settings2 size={17} /></button><div className="topbar-divider" /><AuthAccountMenu /></div>
        </header>
        <div className="workspace-content">
          {activeWorkspace === "watchlist" && auth.user && accountWatchlistLoading && <div className="workspace-state" role="status">Loading your private watchlist…</div>}
          {activeWorkspace === "watchlist" && watchlistError && <div className="workspace-state workspace-error" role="alert"><span>{watchlistError}</span><button className="quiet-button" onClick={() => setWatchlistRetry((value) => value + 1)}>Retry saved watchlist</button></div>}
          {activeWorkspace === "watchlist" && auth.user && !accountWatchlistLoading && guestWatchlistToImport.length > 0 && <section className="watchlist-import-banner"><div><b>Temporary guest list available</b><p>{guestWatchlistToImport.length} browser-session symbols are available to add. Existing account entries will be kept; nothing is copied until you confirm.</p></div>{!confirmGuestImport ? <button className="account-action" onClick={() => { setGuestImportState("idle"); setConfirmGuestImport(true); }}><ShieldCheck size={15} />Review import</button> : <div className="watchlist-import-confirm" role="alertdialog" aria-label="Confirm guest watchlist import"><p>Import {guestWatchlistToImport.length} guest ticker/exchange entries into this account?</p><button className="account-action" disabled={guestImportState === "saving"} onClick={() => void importGuestWatchlist()}>{guestImportState === "saving" ? "Importing…" : "Confirm import"}</button><button className="quiet-button" disabled={guestImportState === "saving"} onClick={() => setConfirmGuestImport(false)}>Cancel</button></div>}{guestImportState === "saved" && <span role="status">Guest symbols were added; existing account entries were preserved.</span>}{guestImportState === "error" && <span role="alert">Import failed. Your guest list and saved account list remain available; retry when the connection is restored.</span>}</section>}
          {activeWorkspace === "overview" ? dataMode === "public" ? <PublicMarketOverview selectedSymbol={selectedSymbol} watchlist={watchlist} onSelectTicker={chooseTicker} onToggleWatchlist={toggleWatchlist} onNavigate={moveWorkspace} onHelp={() => openHelp("TradingView charts")} /> : <>
        <section className="page-heading">
              <div><div className="eyebrow"><span className="eyebrow-line" /> MARKET INTELLIGENCE <span className="eyebrow-dot">·</span> SAMPLE SESSION</div><h1>Good morning. <span>Let’s find clarity.</span></h1><p className="heading-subtitle">Your market view, with the details that matter.</p></div>
              <div className="heading-controls"><div className="search-wrap"><Search size={16} /><input id="ticker-search" value={search} placeholder="Search ticker or company" onFocus={() => setSearchOpen(true)} onChange={(event) => { setSearch(event.target.value); setSearchOpen(true); }} onKeyDown={(event) => { if (event.key === "Enter" && matches[0]) chooseTicker(matches[0].symbol); if (event.key === "Escape") setSearchOpen(false); }} aria-label="Search ticker or company" aria-controls="ticker-suggestions" aria-expanded={searchOpen} /><kbd>Ctrl/⌘ K</kbd>{searchOpen && <><button className="search-dismiss" aria-label="Close ticker search" onClick={() => setSearchOpen(false)} /><div id="ticker-suggestions" className="search-popover" role="listbox" aria-label="Ticker suggestions">{dataMode === "fastapi" && tickerSearchState === "loading" && <div className="search-empty" role="status">Searching Python ticker fixtures…</div>}{dataMode === "fastapi" && tickerSearchState === "error" && <div className="search-empty" role="alert">{tickerSearchError}</div>}{matches.map((item) => <button key={item.symbol} role="option" aria-selected={item.symbol === selectedSymbol} onClick={() => chooseTicker(item.symbol)}><span className="search-result-symbol">{item.symbol}</span><span className="search-result-name">{item.name}<small>{item.exchange} · {item.sector}</small></span><ArrowDownRight className="search-result-arrow" size={15} /></button>)}{!matches.length && tickerSearchState !== "loading" && tickerSearchState !== "error" && <div className="search-empty">No {dataMode === "fastapi" ? "Python ticker fixture" : "fixture"} match. Try NVDA, AAPL, MSFT, AMZN, GOOGL, JPM, or LLY.</div>}</div></>}</div><button className="quiet-button" onClick={() => setShowSummary((value) => !value)} aria-expanded={showSummary}><SlidersHorizontal size={15} /><span>{showSummary ? "Hide summary" : "Show summary"}</span></button></div>
            </section>
      <div className="fixture-notice"><ShieldCheck size={15} /><span>{dataMode === "fastapi" ? "Python engine demo" : "Prototype data"}</span><span className="notice-separator">·</span><span>{dataMode === "fastapi" ? "Market summary, ticker analysis, chart, Discovery directory and calendar, company research, and Watchlist summaries use the local API with synthetic inputs." : "Every price and metric on this screen is illustrative fixture data, not live market information."}</span><button aria-label="About prototype data" className="notice-help" onClick={() => openHelp("Synthetic vs. actual financial information")}><CircleHelp size={14} /></button></div>
      {dataMode === "fastapi" && [overviewEnvelope, analysisEnvelope, chartEnvelope, overviewWatchlist].some((response) => response?.stale) && <div className="workspace-fixture-note" role="status">Showing the last successful cached response. It is marked stale because the latest provider request did not complete.</div>}
            <details className="state-preview"><summary>Preview response states</summary><div className="state-preview-panel"><span>Local UI samples · no provider calls</span><div className="state-preview-buttons">{([{key:"ready",label:"Ready"},{key:"loading",label:"Loading"},{key:"unavailable",label:"Unavailable"},{key:"error",label:"Error"}] as const).map((option) => <button key={option.key} aria-pressed={previewDataState === option.key} className={previewDataState === option.key ? "state-preview-active" : ""} onClick={() => setPreviewDataState(option.key)}>{option.label}</button>)}</div></div></details>

            {import.meta.env.DEV && isKestrelPreviewEnabled() && KestrelResearchPreview && <Suspense fallback={<div className="workspace-state" role="status">Loading Kestrel preview…</div>}><KestrelResearchPreview /></Suspense>}
            {showSummary && <section className="overview-summary" aria-label="Market summary"><div className="section-heading-row"><div><span className="section-kicker">YOUR MARKET SNAPSHOT</span><h2>Markets at a glance</h2></div><button className="text-action" onClick={() => moveWorkspace("discovery")}>Explore directory <ArrowDownRight size={14} /></button></div><div className="pulse-grid">{dataMode === "fastapi" && overviewState === "loading" ? <div className="workspace-state" role="status"><span className="loading-ring" /> Requesting synthetic market summary from local API…</div> : dataMode === "fastapi" && overviewState === "error" ? <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>Local API response unavailable</b><span>{overviewError ?? "Confirm the FastAPI service is running on localhost:8000."}</span></div><button className="quiet-button" onClick={() => setDataMode("fixtures")}>Use local fixtures</button></div> : (dataMode === "fastapi" ? overviewEnvelope?.data?.markets ?? [] : pulseFixtures).map((pulse, index) => <SpotlightCard key={pulse.symbol} className={`pulse-card pulse-${index}`}><div className="pulse-card-top"><span>{pulse.name}</span><span className="pulse-symbol">{pulse.symbol}</span></div><div className="pulse-value-row"><strong>{pulse.value}</strong><span className={pulse.tone === "up" ? "tone-up" : "tone-down"}>{pulse.tone === "up" ? <ArrowUpRight size={14} /> : <ArrowDown size={13} />}{pulse.change}</span></div><div className="mini-spark" aria-hidden="true"><svg viewBox="0 0 120 28" preserveAspectRatio="none"><path d={sparklinePath(pulse.series)} /></svg></div><div className="pulse-card-foot"><span>{dataMode === "fastapi" ? "Synthetic API response" : "Illustrative fixture"}</span><span>·</span><span>Not live market data</span></div></SpotlightCard>)}</div>{dataMode === "fastapi" && overviewEnvelope?.data?.disclosure && <p className="api-disclosure">{overviewEnvelope.data.disclosure}</p>}<div className="market-summary-detail-grid">{(dataMode === "fastapi" ? overviewEnvelope?.data?.markets ?? [] : pulseFixtures).map((pulse) => <ExpandableResearchCard key={`detail-${pulse.symbol}`} title={`${pulse.name} context`} subtitle={`${pulse.symbol} · simulated market summary`} preview={<span>{pulse.value} · {pulse.change}</span>} className="market-summary-detail"><div className="expandable-fact-grid"><div><span>Sample level</span><b>{pulse.value}</b></div><div><span>Sample change</span><b>{pulse.change}</b></div><div><span>Direction label</span><b>{pulse.tone === "up" ? "Up sample" : "Down sample"}</b></div></div><p>These prewritten fixture fields illustrate how a market summary could be explained. They do not contain live market or investment analysis.</p></ExpandableResearchCard>)}</div></section>}

            <section className="stock-workspace" aria-label="Selected ticker workspace">
              <div className="stock-header"><div className="stock-identity"><div className="ticker-avatar">{ticker.symbol.slice(0, 1)}</div><div className="stock-name-block"><div className="stock-eyebrow">{ticker.exchange} <span>·</span> {ticker.sector}</div><div className="stock-title"><h2>{ticker.name}</h2><span className="stock-symbol">{ticker.symbol}</span></div><div className="stock-subtitle">{ticker.industry} <span>·</span> Sample data only</div></div></div><div className="stock-header-actions"><button className={`outline-button ${saved ? "saved" : ""}`} onClick={toggleWatchlist} aria-pressed={saved}><Star size={15} fill={saved ? "currentColor" : "none"} /><span>{saved ? "In watchlist" : "Add to watchlist"}</span></button></div></div>
              <div className="stock-main-grid">
                <SpotlightCard className="chart-card" label={dataMode === "fastapi" ? "Python-engine synthetic price chart" : "Illustrative price chart"}>
                  <div className="card-heading chart-card-heading"><div><div className="chart-title-overline"><span className="chart-status-dot" /> PRICE ACTION <span>·</span> SAMPLE</div><h3>Price chart</h3></div><div className="chart-control-group"><div className="chart-range-controls" aria-label="Chart range">{chartIntervals.map((interval) => <button key={interval} onClick={() => setRange(interval)} className={range === interval ? "range-active" : ""} aria-pressed={range === interval}>{interval}</button>)}</div><label className="chart-resolution-control"><span>Interval</span><select aria-label="Chart interval" title={dataMode === "fixtures" ? "Select FastAPI demo to load Python-generated interval samples" : "Synthetic bar interval"} disabled={dataMode === "fixtures"} value={resolution} onChange={(event) => setResolution(event.target.value as ChartResolution)}>{chartResolutions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div></div>
                  <PriceChart symbol={ticker.symbol} values={displayedChartValues} referencePrice={Number(ticker.price)} interval={range} style={chartStyle} dataState={dataMode === "fastapi" ? chartState === "loading" ? "loading" : chartState === "error" ? "error" : chartState === "ready" ? "ready" : "unavailable" : previewDataState} onStyleChange={setChartStyle} onExpand={() => setExpandedChart((value) => !value)} onRetry={() => dataMode === "fastapi" ? setChartRetry((value) => value + 1) : setPreviewDataState("ready")} useRawValues={dataMode === "fastapi"} />
                  {dataMode === "fastapi" && chartState === "error" && chartError && <p role="alert" className="table-caption">{chartError}</p>}
                </SpotlightCard>
                <div className="side-metrics">
                  <SpotlightCard className="price-card" label={dataMode === "fastapi" ? "Python-engine close and daily change from synthetic inputs" : "Illustrative ticker summary"}><div className="metric-card-heading"><span>{dataMode === "fastapi" ? "PYTHON SAMPLE CLOSE" : "INDICATIVE CLOSE"}</span><details className="metric-info-disclosure"><summary aria-label="Explain the sample close">i</summary><p>{dataMode === "fastapi" ? "This value comes from the local Python demonstration and synthetic inputs. It is not live market pricing." : "This illustrative fixture value is not a live quote or a verified company price."}</p></details></div><strong className="primary-price">{displayedPrice === null ? "—" : `$${displayedPrice.toFixed(2)}`}</strong><span className={displayedChange === null ? "price-change" : displayedChange >= 0 ? "price-change tone-up" : "price-change tone-down"}>{displayedChange === null ? "Waiting for Python analysis" : <>{displayedChange >= 0 ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}{displayedChange >= 0 ? "+" : ""}{displayedChange.toFixed(2)}%</>} <small>sample</small></span>{dataMode === "fixtures" && <><div className="price-card-divider" /><div className="price-card-meta"><span>Previous sample close</span><b>$140.10</b></div><div className="price-card-meta"><span>Sample range</span><b>$136.42 — $144.08</b></div></>}<div className="price-card-foot"><span className="fixture-dot" />{dataMode === "fastapi" ? "Python engine · synthetic history" : "Illustrative numbers"}</div></SpotlightCard>
                  <SpotlightCard className="strength-card" label={dataMode === "fastapi" ? "Python-engine technical analysis on synthetic inputs" : "Illustrative technical strength"}><div className="metric-card-heading"><span>{dataMode === "fastapi" ? "PYTHON TECHNICAL ANALYSIS" : "TECHNICAL STRENGTH"}</span><details className="metric-info-disclosure"><summary aria-label="Explain technical strength">i</summary><p>In this prototype, the rating is either an illustrative fixture or the existing Python engine result run on synthetic inputs. It is not based on the TradingView chart.</p></details></div>{dataMode === "fastapi" ? <>{analysisState === "loading" ? <div className="workspace-state" role="status">Running Python analysis on synthetic inputs…</div> : analysisState === "error" ? <div className="workspace-state workspace-error" role="alert">{analysisError}</div> : analysisEnvelope?.data && <><div className="strength-score-row"><div><strong>{analysisEnvelope.data.rating}</strong></div><span className="strength-tag">{analysisEnvelope.data.technical_rating} · technical</span></div><p>{analysisEnvelope.data.rating_source} · {analysisEnvelope.data.observations} synthetic observations</p><p>{analysisEnvelope.data.constructive_checks} constructive checks · {analysisEnvelope.data.caution_checks} caution checks</p></>}<ExpandableResearchCard title={`${ticker.symbol} Python analysis`} subtitle={`${ticker.name} · Python ${analysisEnvelope?.provenance ?? "engine snapshot"}`} preview={<span>{analysisEnvelope?.data?.trend_state ?? "Analysis details"}</span>} className="strength-detail-trigger"><p>{analysisEnvelope?.data?.disclosure ?? "Python engine calculation over deterministic synthetic inputs."}</p>{analysisEnvelope?.data && <div className="expandable-fact-grid">{[["20-day average", analysisEnvelope.data.indicators.sma20], ["50-day average", analysisEnvelope.data.indicators.sma50], ["200-day average", analysisEnvelope.data.indicators.sma200], ["RSI", analysisEnvelope.data.indicators.rsi], ["MACD", analysisEnvelope.data.indicators.macd], ["Annualized realized volatility", analysisEnvelope.data.indicators.hist_vol]].map(([label, value]) => <div key={String(label)}><span>{String(label)}</span><b>{value === null || value === undefined ? "Unavailable" : Number(value).toFixed(3)}</b></div>)}</div>}</ExpandableResearchCard></> : <><div className="strength-score-row"><div><strong>{ticker.strength}</strong><span>/ 100</span></div><span className="strength-tag"><TrendingUp size={12} />{ticker.strength >= 65 ? "Constructive sample" : ticker.strength >= 45 ? "Mixed sample" : "Cautious sample"}</span></div><div className="strength-meter"><span style={{ width: `${ticker.strength}%` }} /></div><div className="strength-scale"><span>WEAK</span><span>NEUTRAL</span><span>STRONG</span></div><p>Sample momentum profile based on illustrative inputs. Not an investment signal.</p><ExpandableResearchCard title={`${ticker.symbol} technical strength`} subtitle={`${ticker.name} · simulated research detail`} preview={<span>{ticker.strength} / 100 · sample score</span>} className="strength-detail-trigger"><p>The displayed strength score and descriptive band come directly from the selected ticker fixture. This prototype does not calculate or infer a production technical rating.</p><p>Sector: <b>{ticker.sector}</b> · Industry: <b>{ticker.industry}</b></p></ExpandableResearchCard></>}<button className="strength-link" onClick={() => moveWorkspace("research")}>View technical detail <ArrowDownRight size={14} /></button></SpotlightCard>
                </div>
              </div>
            </section>

            <section className="lower-grid">
              <SpotlightCard className="sector-card">
                <div className="card-heading"><div><span className="section-kicker">SECTOR LENS</span><h3>Leadership & participation</h3></div><span className="sample-tag">{dataMode === "fastapi" ? "API SAMPLE" : "UI SAMPLE"}</span></div>
                <div className="sector-bars">{dataMode === "fastapi" && overviewState === "loading" ? <div className="workspace-state" role="status">Loading sector samples from the local API…</div> : dataMode === "fastapi" && overviewState === "error" ? <div className="workspace-state workspace-error" role="alert">{overviewError ?? "Sector summary unavailable."}</div> : displayedSectorActivity.map((sector, index) => { const colors = ["#62daa0", "#8cbf9f", "#82a997", "#758d84"]; return <div className="sector-bar-row" key={sector.name}><span>{sector.name}</span><div className="sector-track"><i style={{ width: `${sector.value}%`, background: colors[index % colors.length] }} /></div><b>{sector.value}</b><small>sample</small></div>; })}</div>
                <div className="panel-note"><Activity size={14} /> Relative activity shown for interface illustration only.</div>
              </SpotlightCard>
              <SpotlightCard className="watch-card">
                <div className="card-heading"><div><span className="section-kicker">PINNED TICKERS</span><h3>On your radar</h3></div><button className="text-action" onClick={() => moveWorkspace("watchlist")}>Full list <ArrowDownRight size={14} /></button></div>
                <div className="watch-table-head"><span>COMPANY</span><span>{dataMode === "fastapi" ? "PYTHON SAMPLE" : "SAMPLE PRICE"}</span><span>MOVE</span></div>
                {dataMode === "fastapi" && overviewWatchlistError && <p className="table-caption" role="alert">{overviewWatchlistError}</p>}
                <div className="watch-table">{watchlist.slice(0, 4).map((symbol) => {
                  const item = tickerFixtures.find((fixture) => fixture.symbol === symbol);
                  const summary = overviewWatchlist?.data?.summaries.find((row) => row.symbol === symbol);
                  const companyName = dataMode === "fastapi" ? summary?.name ?? symbol : item?.name ?? symbol;
                  const price = dataMode === "fastapi" ? summary?.sample_close == null ? overviewWatchlistState === "loading" ? "Loading…" : "Unavailable" : `$${summary.sample_close.toFixed(2)}` : `$${item?.price ?? "—"}`;
                  const change = dataMode === "fastapi" ? summary?.sample_change_percent == null ? overviewWatchlistState === "loading" ? "Loading…" : "Unavailable" : `${summary.sample_change_percent >= 0 ? "+" : ""}${summary.sample_change_percent.toFixed(2)}%` : item?.change ?? "Unavailable";
                  const tone = dataMode === "fastapi" ? summary?.sample_change_percent != null && summary.sample_change_percent >= 0 ? "tone-up" : "tone-down" : item?.changeTone === "up" ? "tone-up" : "tone-down";
                  return <button key={symbol} className="watch-row" onClick={() => chooseTicker(symbol)}><span className="watch-company"><b>{symbol}</b><small>{companyName}</small></span><span className="watch-price">{price}</span><span className={`watch-change ${tone}`}>{change}</span></button>;
                })}</div>
                {dataMode === "fastapi" && overviewWatchlist?.warnings.length ? <p className="table-caption" role="status">{overviewWatchlist.warnings.join(" ")}</p> : null}
              </SpotlightCard>
            </section>

            <footer className="page-footnote"><span>JUJOSMI TRADE UI 2.0</span><span>Design prototype · all financial data is illustrative</span><span>Market tools for clearer thinking</span></footer>
          </> : <Suspense fallback={<div className="workspace-state" role="status">Loading workspace…</div>}>
            {activeWorkspace === "discovery" ? <DiscoveryWorkspace dataMode={dataMode} selectedSymbol={selectedSymbol} selectedSecExchange={selectedSecExchange} selectedTicker={ticker} watchlist={watchlist} onSelectTicker={chooseTicker} onNavigate={moveWorkspace} /> : activeWorkspace === "research" ? <ResearchWorkspace dataMode={dataMode} selectedSymbol={selectedSymbol} selectedSecExchange={selectedSecExchange} selectedTicker={ticker} watchlist={watchlist} onSelectTicker={chooseTicker} onNavigate={moveWorkspace} onToggleWatchlist={(symbol) => { if (watchlist.includes(symbol)) void removeWatchlistTicker(symbol); else void addWatchlistTicker(symbol); }} /> : <WatchlistWorkspace dataMode={dataMode} selectedSymbol={selectedSymbol} selectedSecExchange={selectedSecExchange} selectedTicker={ticker} watchlist={watchlist} onSelectTicker={chooseTicker} onAddTicker={addWatchlistTicker} onRemoveTicker={removeWatchlistTicker} onNavigate={moveWorkspace} persistent={Boolean(auth.user)} accountLoading={accountWatchlistLoading} accountEntries={accountWatchlist} watchlistError={watchlistError} reviewScope={auth.user ? "account:" + auth.user.id : "guest"} />}
          </Suspense>}
        </div>
      </main>
      <AnimatePresence>{expandedChart && <motion.div className="chart-modal" initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} role="dialog" aria-modal="true" aria-label="Expanded chart" onClick={(event) => { if (event.target === event.currentTarget) setExpandedChart(false); }}><motion.div className="chart-modal-content" initial={reduced ? false : { y: 12, scale: 0.99 }} animate={{ y: 0, scale: 1 }} exit={{ y: 8, scale: 0.99 }}><div className="modal-head"><div><span className="section-kicker">{ticker.symbol} · SYNTHETIC FIXTURE</span><h2>Expanded chart</h2></div><button className="icon-button" onClick={() => setExpandedChart(false)} aria-label="Close expanded chart"><X size={18} /></button></div><PriceChart symbol={ticker.symbol} values={displayedChartValues} referencePrice={Number(ticker.price)} interval={range} style={chartStyle} dataState={dataMode === "fastapi" ? chartState === "loading" ? "loading" : chartState === "error" ? "error" : chartState === "ready" ? "ready" : "unavailable" : previewDataState} onStyleChange={setChartStyle} onExpand={() => setExpandedChart(false)} onRetry={() => dataMode === "fastapi" ? setChartRetry((value) => value + 1) : setPreviewDataState("ready")} useRawValues={dataMode === "fastapi"} /></motion.div></motion.div>}</AnimatePresence>
      <div className="mobile-bottom-nav" aria-label="Workspace quick navigation">{[{id:"overview" as const,label:"Markets",icon:Activity},{id:"discovery" as const,label:"Discover",icon:Search},{id:"research" as const,label:"Research",icon:TrendingUp},{id:"watchlist" as const,label:"Saved",icon:Star}].map(({id,label,icon:Icon}) => <button key={id} className={activeWorkspace === id ? "mobile-nav-active" : ""} onClick={() => moveWorkspace(id)} aria-current={activeWorkspace === id ? "page" : undefined}><Icon size={17} /><span>{label}</span></button>)}</div>
    {activePanel === "preferences" && <PreferencesDialog value={preferences} systemReducedMotion={systemReducedMotion} onChange={updatePreferences} onReset={resetPreferences} onClose={() => setActivePanel(null)} />}
    {activePanel === "help" && <HelpGlossaryDialog key={`help-${helpQuery}`} initialQuery={helpQuery} onClose={() => setActivePanel(null)} />}
    </div></MotionConfig>
  );
}

function PublicMarketOverview({ selectedSymbol, watchlist, onSelectTicker, onToggleWatchlist, onNavigate, onHelp }: {
  selectedSymbol: string;
  watchlist: string[];
  onSelectTicker: (symbol: string) => void;
  onToggleWatchlist: () => void;
  onNavigate: (workspace: Workspace) => void;
  onHelp: () => void;
}) {
  const [query, setQuery] = useState("");
  const matches = tradingViewTickerSymbols.filter((symbol) => symbol.includes(query.trim().toUpperCase()));
  return <div className="public-workspace">
    <section className="page-heading public-heading">
      <div><div className="eyebrow"><span className="eyebrow-line" /> JUJOSMI TRADE <span className="eyebrow-dot">·</span> PUBLIC VIEW</div><h1>Market Overview</h1><p className="heading-subtitle">{tradingViewWidgetEnabled ? "A TradingView chart with exchange-qualified symbol selection." : "Third-party charts are disabled in this release; SEC Company Research and guest watchlists remain available."}</p></div>
      <div className="public-symbol-tools">
        <label className="public-symbol-search"><Search size={15} /><input id="ticker-search" aria-label="Find supported chart ticker" aria-controls="public-symbol-suggestions" aria-expanded={Boolean(query)} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && matches[0]) { onSelectTicker(matches[0]); setQuery(""); } if (event.key === "Escape") setQuery(""); }} placeholder="Find a ticker" /><select aria-label="Selected chart ticker" value={selectedSymbol} onChange={(event) => onSelectTicker(event.target.value)}>{tradingViewTickerSymbols.map((symbol) => <option key={symbol} value={symbol}>{tradingViewSymbols[symbol]}</option>)}</select></label>
        {query && <div id="public-symbol-suggestions" className="public-symbol-suggestions" role="listbox" aria-label="Matching configured symbols">{matches.map((symbol) => <button role="option" aria-selected={symbol === selectedSymbol} key={symbol} onClick={() => { onSelectTicker(symbol); setQuery(""); }}>{tradingViewSymbols[symbol]}</button>)}{!matches.length && <span role="status">No configured ticker match.</span>}</div>}
      </div>
    </section>
    <div className="public-data-note" role="note"><ShieldCheck size={16} /><span>{tradingViewWidgetEnabled ? "TradingView chart · hosted by TradingView. Jujosmi does not extract chart data or use it in ratings. Other research sources are not enabled in this public view." : "TradingView is not loaded in this release. Third-party chart display remains disabled pending licensing review."}</span>{tradingViewWidgetEnabled && <button type="button" className="notice-help" onClick={onHelp} aria-label="TradingView chart help"><CircleHelp size={14} /></button>}</div>
    <section className="public-chart-panel">
      <header className="public-chart-header"><div><span className="section-kicker">{tradingViewWidgetEnabled ? "INTERACTIVE MARKET CHART" : "CHART DISPLAY"}</span><h2>{tradingViewWidgetEnabled ? tradingViewSymbols[selectedSymbol] ?? selectedSymbol : "Chart unavailable"}</h2></div><button className={`outline-button ${watchlist.includes(selectedSymbol) ? "saved" : ""}`} onClick={onToggleWatchlist} aria-pressed={watchlist.includes(selectedSymbol)}><Star size={15} fill={watchlist.includes(selectedSymbol) ? "currentColor" : "none"} />{watchlist.includes(selectedSymbol) ? "In watchlist" : "Add to watchlist"}</button></header>
      {tradingViewWidgetEnabled ? <Suspense fallback={<div className="workspace-state" role="status">Loading TradingView chart…</div>}><TradingViewAdvancedChart symbol={selectedSymbol} theme="dark" /></Suspense> : <div className="workspace-state release-disabled-state" role="status">
        <div><b>TradingView chart is disabled in this release.</b><span>Third-party chart display is awaiting a confirmed licensing decision. SEC Company Research and the guest watchlist remain available.</span></div>
        <div className="chart-disabled-actions"><button className="text-action" onClick={() => onNavigate("research")}>Open Company Research</button><button className="text-action" onClick={() => onNavigate("watchlist")}>Open Guest Watchlist</button></div>
      </div>}
    </section>
    <section className="public-unavailable-grid" aria-label="Market research availability">
      <UnavailableCard title="Market summary" detail="Market indices, volatility measures, and sector participation are unavailable because no licensed market-summary source is connected." />
      <UnavailableCard title="Technical ratings" detail="Jujosmi technical calculations are retained for future licensed inputs. TradingView widget data is not read or used for ratings." />
      <UnavailableCard title="Company information" detail="Company fundamentals, analyst views, headlines, and calendars are unavailable in public mode until their sources and use rights are approved." />
    </section>
    <footer className="page-footnote"><span>JUJOSMI TRADE UI 2.0</span>{tradingViewWidgetEnabled && <span>Chart © TradingView · availability may vary by market</span>}<button className="text-action" onClick={() => onNavigate("research")}>Open Company Research <ArrowDownRight size={14} /></button></footer>
  </div>;
}

export function UnavailableCard({ title, detail }: { title: string; detail: string }) {
  return <section className="public-unavailable-card"><span className="section-kicker">SOURCE NOT CONNECTED</span><h3>{title}</h3><p>{detail}</p></section>;
}

function App() {
  return <AuthProvider><TradeApp /></AuthProvider>;
}

export default App;
