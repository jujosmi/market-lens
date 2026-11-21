import { useEffect, useRef, useState } from "react";

type TradingViewWidgetProps = {
  scriptUrl: string;
  tagName: string;
  attributes: Record<string, string>;
  providerUrl: string;
  providerLinkLabel: string;
  className?: string;
  height: number;
  label: string;
};

type LoadState = "loading" | "ready" | "error";
const moduleLoads = new Map<string, Promise<void>>();
const MODULE_TIMEOUT_MS = 12_000;

function loadWidgetModule(scriptUrl: string, tagName: string): Promise<void> {
  if (customElements.get(tagName)) return Promise.resolve();
  let load = moduleLoads.get(scriptUrl);
  if (!load) {
    load = new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(`script[type="module"][src="${scriptUrl}"]`);
      const script = existing ?? document.createElement("script");
      let timeout = 0;
      const cleanup = () => {
        window.clearTimeout(timeout);
        script.removeEventListener("load", onLoad);
        script.removeEventListener("error", onError);
      };
      const onLoad = () => { cleanup(); resolve(); };
      const onError = () => { cleanup(); script.remove(); reject(new Error("TradingView widget module request failed.")); };
      script.addEventListener("load", onLoad, { once: true });
      script.addEventListener("error", onError, { once: true });
      timeout = window.setTimeout(() => {
        cleanup();
        script.remove();
        reject(new Error("TradingView widget module timed out."));
      }, MODULE_TIMEOUT_MS);
      if (!existing) {
        script.type = "module";
        script.src = scriptUrl;
        script.async = true;
        script.dataset.tradingviewWidget = "true";
        document.head.append(script);
      }
    }).catch((error: unknown) => {
      moduleLoads.delete(scriptUrl);
      throw error;
    });
    moduleLoads.set(scriptUrl, load);
  }
  return load.then(async () => {
    if (customElements.get(tagName)) return;
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error("TradingView widget custom element was not registered.")), MODULE_TIMEOUT_MS);
      customElements.whenDefined(tagName).then(() => { window.clearTimeout(timeout); resolve(); });
    });
  }).catch((error: unknown) => {
    moduleLoads.delete(scriptUrl);
    if (!customElements.get(tagName)) document.querySelector<HTMLScriptElement>(`script[type="module"][src="${scriptUrl}"]`)?.remove();
    throw error;
  });
}

/** Loads a TradingView-owned Web Component. Jujosmi never reads its rendered data. */
export function TradingViewWidget({ scriptUrl, tagName, attributes, providerUrl, providerLinkLabel, className = "", height, label }: TradingViewWidgetProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [retry, setRetry] = useState(0);
  const attributeKey = JSON.stringify(attributes);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let active = true;
    setState("loading");
    const widget = document.createElement(tagName);
    for (const [name, value] of Object.entries(JSON.parse(attributeKey) as Record<string, string>)) widget.setAttribute(name, value);
    widget.setAttribute("aria-label", label);
    host.replaceChildren(widget);
    loadWidgetModule(scriptUrl, tagName).then(() => {
      if (active) setState("ready");
    }).catch(() => {
      if (active) setState("error");
    });
    return () => {
      active = false;
      widget.remove();
    };
  }, [attributeKey, label, retry, scriptUrl, tagName]);

  return <section className={`tradingview-widget-shell ${className}`} aria-label={label}>
    <div ref={hostRef} className="tradingview-web-component" style={{ height }} />
    <p className="tradingview-widget-status" role={state === "error" ? "alert" : "status"}>
      {state === "loading" ? "Connecting to TradingView…" : state === "error" ? "TradingView’s widget script could not be loaded. Check network or content-security restrictions, then retry or open the provider page." : "TradingView widget module loaded. If its hosted content is blank or blocked, open the provider page below."}
    </p>
    <div className="tradingview-widget-actions">
      {state === "error" && <button type="button" className="quiet-button" onClick={() => setRetry((value) => value + 1)}>Retry widget</button>}
      <a className="research-provider-link" href={providerUrl} target="_blank" rel="noopener noreferrer nofollow">{providerLinkLabel}</a>
      <span>Provided by TradingView · this is a standalone provider assessment, not a Jujosmi calculation.</span>
    </div>
  </section>;
}
