import { useMemo } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Database, Expand, LineChart, RotateCw } from "lucide-react";
import { buildSeries, type ChartInterval, type ChartStyle } from "../data/fixtures";

export type ChartPreviewState = "ready" | "loading" | "unavailable" | "error";
type Props = { symbol: string; values: number[]; referencePrice: number; interval: ChartInterval; style: ChartStyle; dataState: ChartPreviewState; onStyleChange: (value: ChartStyle) => void; onExpand: () => void; onRetry: () => void; useRawValues?: boolean };

const width = 900;
const height = 315;
const plot = { left: 20, right: 875, top: 20, bottom: 258 };

export function PriceChart({ symbol, values, referencePrice, interval, style, dataState, onStyleChange, onExpand, onRetry, useRawValues = false }: Props) {
  const series = useMemo(() => values.length ? useRawValues ? values : buildSeries(values, interval, referencePrice) : [], [values, interval, referencePrice, useRawValues]);
  const min = series.length ? Math.min(...series) - 7 : 0;
  const max = series.length ? Math.max(...series) + 7 : 1;
  const coords = series.map((value, index) => ({
    x: series.length === 1 ? (plot.left + plot.right) / 2 : plot.left + (index / (series.length - 1)) * (plot.right - plot.left),
    y: plot.bottom - ((value - min) / (max - min)) * (plot.bottom - plot.top),
  }));
  const linePath = coords.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${plot.right},${plot.bottom} L${plot.left},${plot.bottom} Z`;
  const last = coords.at(-1)!;
  const positive = series.length > 1 ? series.at(-1)! >= series[0]! : true;
  const stroke = positive ? "#5ce0a2" : "#f28181";
  const gradientId = `chart-fill-${symbol}`;

  return (
    <div className="chart-shell" aria-label={`${symbol} ${useRawValues ? "Python synthetic" : "illustrative"} chart`}>
      <div className="chart-toolbar">
        <div className="chart-context"><span className="live-dot sample-dot" /> <span>{useRawValues ? "Python synthetic series" : "Illustrative series"}</span><span className="toolbar-divider" /> <span>USD</span></div>
        <div className="chart-actions">
          <div className="segmented-control" aria-label="Chart display style">
            {(["Area", "Line"] as const).map((choice) => <button key={choice} className={style === choice ? "selected" : ""} onClick={() => onStyleChange(choice)} aria-pressed={style === choice}>{choice === "Area" ? <LineChart size={14} /> : <span className="line-icon" />}<span>{choice}</span></button>)}
          </div>
          <button className="icon-button chart-expand" aria-label="Expand chart" onClick={onExpand}><Expand size={16} /></button>
        </div>
      </div>
      <div className="chart-legend"><span className="legend-symbol">{symbol}</span><span>{useRawValues ? "Python close history" : "Sample price path"}</span><span className="legend-value">{series.at(-1)?.toFixed(2) ?? "—"}</span><span className={positive ? "tone-up" : "tone-down"}>{positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{series.length > 1 ? `${positive ? "+" : ""}${(((series.at(-1)! - series[0]!) / series[0]!) * 100).toFixed(2)}%` : ""}</span></div>
      <div className="chart-plot">
        {dataState === "loading" ? <div className="chart-state chart-state-loading" role="status" aria-label="Loading illustrative chart data"><span className="loading-bar loading-bar-long" /><span className="loading-bar loading-bar-medium" /><span className="loading-line" /><span className="loading-line loading-line-short" /><span className="loading-caption">Loading sample price history…</span></div> : dataState === "unavailable" ? <div className="chart-state" role="status"><span className="chart-state-icon"><Database size={18} /></span><strong>No sample price history</strong><span>This response has no chart series for {symbol}. Choose another fixture ticker.</span></div> : dataState === "error" ? <div className="chart-state chart-state-error" role="alert"><span className="chart-state-icon"><AlertTriangle size={18} /></span><strong>Chart data could not load</strong><span>{useRawValues ? "The local Python chart request failed." : "Preview of a temporary provider error. No market request was made."}</span><button className="state-retry" onClick={onRetry}><RotateCw size={12} /> Retry {useRawValues ? "API request" : "preview"}</button></div> : dataState === "ready" && !series.length ? <div className="chart-state" role="status"><span className="chart-state-icon"><Database size={18} /></span><strong>No chart bars returned</strong><span>The local service returned no close values for {symbol} in this range.</span></div> : <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${symbol} ${interval} ${useRawValues ? "Python synthetic" : "illustrative"} chart, ${style.toLowerCase()} style`} preserveAspectRatio="none">
          <defs><linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={stroke} stopOpacity=".24" /><stop offset="100%" stopColor={stroke} stopOpacity="0" /></linearGradient></defs>
          {[0, 1, 2, 3, 4].map((row) => { const y = plot.top + row * ((plot.bottom - plot.top) / 4); return <g key={row}><line x1={plot.left} y1={y} x2={plot.right} y2={y} className="chart-grid" /><text x={plot.right + 12} y={y + 4} className="chart-axis">{(max - row * ((max - min) / 4)).toFixed(0)}</text></g>; })}
          {[0, 1, 2, 3, 4, 5].map((column) => { const x = plot.left + column * ((plot.right - plot.left) / 5); return <line key={column} x1={x} y1={plot.top} x2={x} y2={plot.bottom} className="chart-grid chart-grid-vertical" />; })}
          {style === "Area" && <path d={areaPath} fill={`url(#${gradientId})`} />}
          <path d={linePath} fill="none" stroke={stroke} strokeWidth="2.3" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          <line x1={last.x} y1={last.y} x2={plot.right} y2={last.y} stroke={stroke} strokeDasharray="4 5" opacity=".5" vectorEffect="non-scaling-stroke" />
          <circle cx={last.x} cy={last.y} r="4" fill={stroke} stroke="#0a100e" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          <text x={plot.left} y="295" className="chart-date">SAMPLE 01</text><text x={plot.left + 220} y="295" className="chart-date">SAMPLE 06</text><text x={plot.left + 440} y="295" className="chart-date">SAMPLE 12</text><text x={plot.left + 650} y="295" className="chart-date">SAMPLE 18</text>
        </svg>}
      </div>
      <div className="chart-footer"><span>{useRawValues ? "Python engine synthetic fixture · not live pricing" : "Illustrative fixture · not live pricing"}</span><span>{dataState === "ready" ? `Sample interval: ${interval}` : `Preview state: ${dataState}`}</span></div>
    </div>
  );
}
