import { ArrowRight, LineChart, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { BackgroundGradientAnimation } from "./ui/background-gradient-animation";
import { HoverBorderGradient } from "./ui/hover-border-gradient";

export function LandingPage({ onEnter }: { onEnter: () => void }) {
  const reduced = useReducedMotion();
  return <main className="landing-page">
    <BackgroundGradientAnimation
      gradientBackgroundStart="rgb(5, 9, 15)"
      gradientBackgroundEnd="rgb(7, 15, 23)"
      firstColor="21, 76, 143"
      secondColor="14, 92, 67"
      thirdColor="22, 50, 84"
      fourthColor="8, 93, 67"
      fifthColor="20, 60, 105"
      pointerColor="13, 100, 75"
      size="72%"
      interactive={false}
      containerClassName={`landing-gradient ${reduced ? "gradient-reduced" : ""}`}
      className="landing-foreground"
    >
      <motion.div className="landing-content" initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduced ? 0 : 0.38, ease: "easeOut" }}>
        <a className="landing-brand-mark" href="https://jujosmi.com" aria-label="Visit Jujosmi.com"><img src="/jujosmi-logo-simple-shadow.png" alt="" /></a>
        <span className="landing-eyebrow"><i /> PROFESSIONAL INTELLIGENCE, SIMPLIFIED</span>
        <h1>Jujosmi <span>Trade</span></h1>
        <p className="landing-subtitle">Market Intelligence. Refined.</p>
        <p className="landing-description">A clearer workspace for exploring markets, researching companies, and keeping your watchlist close.</p>
        <HoverBorderGradient onClick={onEnter} containerClassName="landing-enter-wrap" className="landing-enter-button" duration={reduced ? 0 : 1.2} aria-label="Enter Jujosmi Trade">
          <span>Enter Jujosmi Trade <ArrowRight size={17} /></span>
        </HoverBorderGradient>
        <div className="landing-capabilities"><span><LineChart size={15} /> Four research workspaces</span><span><ShieldCheck size={15} /> Demonstration prototype</span></div>
        <p className="landing-disclosure">Prototype experience · all financial values are illustrative samples</p>
      </motion.div>
    </BackgroundGradientAnimation>
  </main>;
}
