import { useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type PropsWithChildren } from "react";
import { motion, useReducedMotion } from "motion/react";

type Props = PropsWithChildren<{ className?: string; spotlight?: boolean; label?: string }>;

export function SpotlightCard({ children, className = "", spotlight = true, label }: Props) {
  const [point, setPoint] = useState({ x: 50, y: 35 });
  const reduceMotion = useReducedMotion();

  function trackPointer(event: ReactPointerEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    setPoint({ x: ((event.clientX - rect.left) / rect.width) * 100, y: ((event.clientY - rect.top) / rect.height) * 100 });
  }

  const style = {
    "--spot-x": `${point.x}%`,
    "--spot-y": `${point.y}%`,
  } as CSSProperties;

  return (
    <motion.section
      aria-label={label}
      className={`spotlight-card ${className}`}
      onPointerMove={spotlight && !reduceMotion ? trackPointer : undefined}
      style={style}
      whileHover={reduceMotion ? undefined : { y: -1 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      {children}
    </motion.section>
  );
}
