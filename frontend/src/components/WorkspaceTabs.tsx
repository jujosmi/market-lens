import { useRef, type KeyboardEvent } from "react";
import { motion, useReducedMotion } from "motion/react";

type Props<T extends string> = {
  label: string;
  items: readonly T[];
  value: T;
  onChange: (value: T) => void;
};

// Original, semantic implementation of a moving active tab surface.
export function WorkspaceTabs<T extends string>({ label, items, value, onChange }: Props<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const reduced = useReducedMotion();

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (event.key === "ArrowRight" ? 1 : items.length - 1)) % items.length;
    const target = items[next];
    if (target !== undefined) {
      onChange(target);
      refs.current[next]?.focus();
    }
  }

  return <div className="workspace-tabs" role="tablist" aria-label={label}>{items.map((item, index) => <button key={item} ref={(node) => { refs.current[index] = node; }} type="button" role="tab" aria-selected={value === item} tabIndex={value === item ? 0 : -1} className={value === item ? "tab-active" : ""} onClick={() => onChange(item)} onKeyDown={(event) => handleKeyDown(event, index)}><span>{item}</span>{value === item && <motion.i className="workspace-tab-indicator" layoutId="workspace-tab-indicator" transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 460, damping: 38 }} />}</button>)}</div>;
}
