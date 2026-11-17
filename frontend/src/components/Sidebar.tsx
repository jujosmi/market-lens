import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Activity, Bookmark, BriefcaseBusiness, ChartNoAxesCombined, ChevronRight, Compass, HelpCircle, PanelLeftClose, PanelLeftOpen, Search, Settings2, Sparkles, X } from "lucide-react";
import type { DataMode, Workspace } from "../types";

const items = [
  { id: "overview", label: "Market Overview", icon: Activity },
  { id: "discovery", label: "Discovery", icon: Compass },
  { id: "research", label: "Company Research", icon: BriefcaseBusiness },
  { id: "watchlist", label: "Watchlist", icon: Bookmark },
] as const;

type Props = { active: Workspace; onChange: (workspace: Workspace) => void; collapsed: boolean; onCollapse: () => void; mobileOpen: boolean; onMobileClose: () => void; watchlist: string[]; onSelectTicker: (ticker: string) => void; onSearch: () => void; onPreferences: () => void; onHelp: () => void; onPublicCharts: () => void; dataMode: DataMode; accountName?: string; accountStatus?: string };

export function Sidebar({ active, onChange, collapsed, onCollapse, mobileOpen, onMobileClose, watchlist, onSelectTicker, onSearch, onPreferences, onHelp, onPublicCharts, dataMode, accountName = "Jujosmi Labs", accountStatus = "Guest mode" }: Props) {
  const [watchOpen, setWatchOpen] = useState(true);
  const reduced = useReducedMotion();
  return (
    <>
      <AnimatePresence>{mobileOpen && <motion.button className="mobile-scrim" aria-label="Close navigation" onClick={onMobileClose} initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />}</AnimatePresence>
      <motion.aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "sidebar-mobile-open" : ""}`} animate={{ width: collapsed ? 78 : 258 }} transition={{ duration: reduced ? 0 : 0.22, ease: "easeInOut" }} aria-label="Main navigation">
        <div className="sidebar-topline"><span className="brand-mark"><img src="/jujosmi-logo.png" alt="Jujosmi" /></span><button className="icon-button sidebar-toggle" onClick={onCollapse} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}</button><button className="icon-button mobile-close" onClick={onMobileClose} aria-label="Close navigation"><X size={17} /></button></div>
        <div className="sidebar-brand-copy"><span className="brand-overline">JUJOSMI LABS</span><span className="brand-product">TRADE<span className="brand-version">UI 2.0</span></span></div>
        <button className="sidebar-search" onClick={onSearch} aria-label="Search tickers (Ctrl or Command+K)" title="Search tickers (Ctrl or Command+K)"><Search size={15} /><span>Search ticker</span><kbd>Ctrl/⌘ K</kbd></button>
        <div className="sidebar-section-label">WORKSPACES</div>
        <nav className="workspace-nav" aria-label="Workspaces">{items.map(({ id, label, icon: Icon }) => <button key={id} onClick={() => { onChange(id); onMobileClose(); }} className={`nav-item ${active === id ? "nav-item-active" : ""}`} aria-current={active === id ? "page" : undefined} title={collapsed ? label : undefined}><span className="nav-icon"><Icon size={17} strokeWidth={1.8} /></span><span className="nav-label">{label}</span>{active === id && <motion.span className="nav-active-indicator" layoutId="nav-indicator" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}</button>)}</nav>
        <button className="sidebar-section-toggle" onClick={() => setWatchOpen((value) => !value)} aria-expanded={watchOpen}><span>YOUR WATCHLIST</span><ChevronRight size={14} className={watchOpen ? "chevron-open" : ""} /></button>
        <AnimatePresence initial={false}>{watchOpen && !collapsed && <motion.div className="sidebar-watchlist" initial={reduced ? false : { height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: reduced ? 0 : 0.18 }}>{watchlist.map((ticker) => <button className="watchlist-link" key={ticker} onClick={() => onSelectTicker(ticker)}><span className="watchlist-symbol">{ticker}</span><span className="watchlist-quote">{dataMode === "public" ? "Chart" : "Sample"}</span></button>)}<button className="watchlist-add" onClick={() => onChange("watchlist")}><span>＋</span> Add symbol</button></motion.div>}</AnimatePresence>
        <div className="sidebar-bottom"><div className="sidebar-plan"><div className="plan-icon"><Sparkles size={15} /></div><div className="plan-copy"><span>Research, clearly.</span><small>Built for thoughtful investors</small></div></div><button className="sidebar-bottom-link" onClick={onPublicCharts} aria-label="Open Public Charts" title="Public Charts"><ChartNoAxesCombined size={16} /><span>Public Charts</span></button><button className="sidebar-bottom-link" onClick={onPreferences} aria-label="Open Preferences" title="Preferences"><Settings2 size={16} /><span>Preferences</span></button><button className="sidebar-bottom-link" onClick={onHelp} aria-label="Open Help and glossary" title="Help & glossary"><HelpCircle size={16} /><span>Help & glossary</span></button><div className="sidebar-user"><div className="avatar">J</div><div className="sidebar-user-copy"><b>{accountName}</b><small>{accountStatus}</small></div></div></div>
      </motion.aside>
    </>
  );
}
