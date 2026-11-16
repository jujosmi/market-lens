import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, X } from "lucide-react";

type Props = {
  title: string;
  subtitle?: string;
  preview: ReactNode;
  children: ReactNode;
  className?: string;
  label?: string;
  onOpen?: () => void;
};

/** Accessible modal expansion pattern adapted from Aceternity's Expandable Card Standard. */
export function ExpandableResearchCard({ title, subtitle, preview, children, className = "", label, onOpen }: Props) {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();
  const reduced = useReducedMotion();

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ));
      if (!focusable.length) return;
      const first = focusable[0]!;
      const last = focusable.at(-1)!;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      window.requestAnimationFrame(() => {
        if (triggerRef.current?.isConnected) triggerRef.current.focus();
        else previousFocus?.focus();
      });
    };
  }, [open]);

  return <>
    <button ref={triggerRef} type="button" className={`expandable-trigger ${className}`} aria-haspopup="dialog" aria-label={label ?? `Expand ${title}`} onClick={() => { onOpen?.(); setOpen(true); }}>
      <span className="expandable-trigger-copy"><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}{preview}</span>
      <span className="expandable-trigger-mark" aria-hidden="true"><ArrowUpRight size={15} /></span>
    </button>
    {createPortal(<AnimatePresence>
      {open && <motion.div className="expandable-overlay" initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
        <motion.section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} className="expandable-dialog" initial={reduced ? false : { opacity: 0, y: 12, scale: 0.985 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={reduced ? undefined : { opacity: 0, y: 8, scale: 0.99 }} transition={{ duration: reduced ? 0 : 0.2 }}>
          <header className="expandable-dialog-head"><div><span className="section-kicker">SIMULATED RESEARCH DETAIL</span><h2 id={titleId}>{title}</h2>{subtitle && <p id={descriptionId}>{subtitle}</p>}{!subtitle && <p id={descriptionId}>Illustrative prototype information; not verified market data.</p>}</div><button ref={closeRef} type="button" className="icon-button" aria-label={`Close ${title} details`} onClick={() => setOpen(false)}><X size={18} /></button></header>
          <div className="expandable-dialog-body">{children}</div>
        </motion.section>
      </motion.div>}
    </AnimatePresence>, document.body)}
  </>;
}
