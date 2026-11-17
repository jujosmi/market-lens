import { useRef } from "react";
import { MonitorCog, PanelLeftClose, RotateCcw, Sparkles } from "lucide-react";
import { ModalPanel } from "./ModalPanel";
import type { AppPreferences } from "../preferences";
import { tradingViewSymbols, tradingViewTickerSymbols } from "../data/tradingViewSymbols";

type Props = {
  value: AppPreferences;
  systemReducedMotion: boolean;
  onChange: (value: AppPreferences) => void;
  onReset: () => void;
  onClose: () => void;
};

export function PreferencesDialog({ value, systemReducedMotion, onChange, onReset, onClose }: Props) {
  const firstRef = useRef<HTMLSelectElement>(null);
  return <ModalPanel title="Preferences" onClose={onClose} className="preferences-dialog" initialFocusRef={firstRef}>
    <p className="utility-dialog-intro">These settings apply in this browser only. They do not sync to an account or across devices.</p>
    <label className="preference-row"><span className="preference-icon"><Sparkles size={16} /></span><span className="preference-copy"><b>Reduce interface animations</b><small>{systemReducedMotion ? "Required by your operating-system accessibility setting." : "Reduce motion and transitions in this interface."}</small></span><input type="checkbox" checked={systemReducedMotion || value.reduceAnimations} disabled={systemReducedMotion} onChange={(event) => onChange({ ...value, reduceAnimations: event.target.checked })} aria-label="Reduce interface animations" /></label>
    <label className="preference-row"><span className="preference-icon"><MonitorCog size={16} /></span><span className="preference-copy"><b>Default TradingView symbol</b><small>Used when this browser opens the public chart.</small></span><select ref={firstRef} value={value.defaultSymbol} onChange={(event) => onChange({ ...value, defaultSymbol: event.target.value })} aria-label="Default TradingView symbol">{tradingViewTickerSymbols.map((symbol) => <option key={symbol} value={symbol}>{tradingViewSymbols[symbol]}</option>)}</select></label>
    <label className="preference-row"><span className="preference-icon"><PanelLeftClose size={16} /></span><span className="preference-copy"><b>Collapse sidebar on desktop</b><small>Keep workspace navigation compact on wider screens.</small></span><input type="checkbox" checked={value.sidebarCollapsed} onChange={(event) => onChange({ ...value, sidebarCollapsed: event.target.checked })} aria-label="Collapse sidebar on desktop" /></label>
    <div className="preference-footer"><button className="quiet-button" type="button" onClick={onReset}><RotateCcw size={14} />Reset preferences</button><button className="account-action" type="button" onClick={onClose}>Done</button></div>
  </ModalPanel>;
}
