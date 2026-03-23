"use client";

import { useRef, useEffect, useState, useMemo, ReactNode } from "react";
import { motion, useScroll, useSpring, useMotionValue, useTransform, animate } from "framer-motion";
import { Sun, Moon, Monitor } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";

// ============================================================================
// ANIMATED NUMBER COUNTER
// ============================================================================

function AnimatedNumber({
  value,
  prefix = "",
  suffix = "",
  duration = 1.5,
  className = "",
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  className?: string;
}) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const controls = animate(0, value, {
            duration,
            ease: "easeOut",
            onUpdate: (v) => setDisplay(Math.round(v)),
          });
          return () => controls.stop();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [value, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}{display.toLocaleString()}{suffix}
    </span>
  );
}

// ============================================================================
// NEURAL NETWORK ANIMATION (Hero background)
// ============================================================================

interface Neuron {
  id: number;
  x: number;
  y: number;
  radius: number;
  pulseDelay: number;
  connections: number[];
}

interface Signal {
  from: number;
  to: number;
  delay: number;
  speed: number;
}

function generateNetwork(nodeCount: number, width: number, height: number, seed: number): Neuron[] {
  const neurons: Neuron[] = [];
  const random = (i: number) => {
    const x = Math.sin(seed + i * 9999) * 10000;
    return x - Math.floor(x);
  };

  for (let i = 0; i < nodeCount; i++) {
    const cluster = Math.floor(i / (nodeCount / 4));
    const clusterCenterX = width * (0.2 + (cluster % 2) * 0.6);
    const clusterCenterY = height * (0.3 + Math.floor(cluster / 2) * 0.4);
    const angle = random(i) * Math.PI * 2;
    const distance = random(i + 100) * 120 + 30;

    neurons.push({
      id: i,
      x: clusterCenterX + Math.cos(angle) * distance,
      y: clusterCenterY + Math.sin(angle) * distance,
      radius: 2 + random(i + 200) * 3,
      pulseDelay: random(i + 300) * 60,
      connections: [],
    });
  }

  for (let i = 0; i < neurons.length; i++) {
    const connectionCount = Math.floor(random(i + 400) * 3) + 1;
    for (let j = 0; j < connectionCount; j++) {
      const targetIndex = Math.floor(random(i * 10 + j) * neurons.length);
      if (targetIndex !== i && !neurons[i].connections.includes(targetIndex)) {
        const dx = neurons[targetIndex].x - neurons[i].x;
        const dy = neurons[targetIndex].y - neurons[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 200) {
          neurons[i].connections.push(targetIndex);
        }
      }
    }
  }

  return neurons;
}

function generateSignals(neurons: Neuron[], count: number, seed: number): Signal[] {
  const signals: Signal[] = [];
  const random = (i: number) => {
    const x = Math.sin(seed + i * 7777) * 10000;
    return x - Math.floor(x);
  };

  let signalIndex = 0;
  for (let i = 0; i < neurons.length && signalIndex < count; i++) {
    for (const conn of neurons[i].connections) {
      if (signalIndex >= count) break;
      signals.push({
        from: i,
        to: conn,
        delay: random(signalIndex) * 120,
        speed: 0.5 + random(signalIndex + 1000) * 1,
      });
      signalIndex++;
    }
  }
  return signals;
}

function NeuralNetworkAnimation({
  width = 500,
  height = 400,
}: {
  width?: number;
  height?: number;
}) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFrame((f) => f + 1);
    }, 16.67);
    return () => clearInterval(interval);
  }, []);

  const neurons = useMemo(() => generateNetwork(40, width, height, 12345), [width, height]);
  const signals = useMemo(() => generateSignals(neurons, 60, 54321), [neurons]);

  const loopDuration = 180;
  const loopFrame = frame % loopDuration;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="w-full h-full"
    >
      <defs>
        <filter id="neuronGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="strongGlow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="8" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id="neuronGradient">
          <stop offset="0%" stopColor="#c084fc" />
          <stop offset="70%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#a855f7" stopOpacity="0.5" />
        </radialGradient>
      </defs>

      <g opacity={0.6}>
        {neurons.map((neuron) =>
          neuron.connections.map((targetId) => {
            const target = neurons[targetId];
            return (
              <line
                key={`${neuron.id}-${targetId}`}
                x1={neuron.x}
                y1={neuron.y}
                x2={target.x}
                y2={target.y}
                stroke="#a855f7"
                strokeWidth="0.5"
                opacity="0.3"
              />
            );
          })
        )}
      </g>

      <g>
        {signals.map((signal, index) => {
          const fromNeuron = neurons[signal.from];
          const toNeuron = neurons[signal.to];
          const signalFrame = (loopFrame - signal.delay + loopDuration) % loopDuration;
          const signalProgress = Math.min(1, Math.max(0, signalFrame / (loopDuration * signal.speed)));

          if (signalProgress <= 0 || signalProgress >= 1) return null;

          const x = fromNeuron.x + (toNeuron.x - fromNeuron.x) * signalProgress;
          const y = fromNeuron.y + (toNeuron.y - fromNeuron.y) * signalProgress;
          const pulseOpacity = Math.sin(signalProgress * Math.PI);

          return (
            <circle
              key={`signal-${index}`}
              cx={x}
              cy={y}
              r={3}
              fill="#c084fc"
              opacity={pulseOpacity * 0.9}
              filter="url(#strongGlow)"
            />
          );
        })}
      </g>

      <g>
        {neurons.map((neuron) => {
          const pulseFrame = (loopFrame + neuron.pulseDelay) % 90;
          const pulse =
            1 +
            (pulseFrame < 30
              ? (pulseFrame / 30) * 0.3
              : pulseFrame < 60
              ? (1 - (pulseFrame - 30) / 30) * 0.3
              : 0);
          const glowOpacity =
            0.4 +
            (pulseFrame < 30
              ? (pulseFrame / 30) * 0.4
              : pulseFrame < 60
              ? (1 - (pulseFrame - 30) / 30) * 0.4
              : 0);

          return (
            <g key={neuron.id}>
              <circle
                cx={neuron.x}
                cy={neuron.y}
                r={neuron.radius * pulse * 2}
                fill="#a855f7"
                opacity={glowOpacity * 0.3}
                filter="url(#neuronGlow)"
              />
              <circle
                cx={neuron.x}
                cy={neuron.y}
                r={neuron.radius * pulse}
                fill="url(#neuronGradient)"
                filter="url(#neuronGlow)"
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// ============================================================================
// ORGANIC BLOB BACKGROUND
// ============================================================================

function OrganicBlobs({ className = "" }: { className?: string }) {
  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}>
      <div
        className="absolute w-[600px] h-[600px] rounded-full opacity-[0.07]"
        style={{
          background: "radial-gradient(circle, #a855f7 0%, transparent 70%)",
          top: "-10%",
          right: "-10%",
          animation: "blobFloat1 20s ease-in-out infinite",
        }}
      />
      <div
        className="absolute w-[500px] h-[500px] rounded-full opacity-[0.05]"
        style={{
          background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)",
          bottom: "-15%",
          left: "-10%",
          animation: "blobFloat2 25s ease-in-out infinite",
        }}
      />
      <div
        className="absolute w-[400px] h-[400px] rounded-full opacity-[0.04]"
        style={{
          background: "radial-gradient(circle, #c084fc 0%, transparent 70%)",
          top: "40%",
          left: "50%",
          animation: "blobFloat3 18s ease-in-out infinite",
        }}
      />
      <style jsx>{`
        @keyframes blobFloat1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(-30px, 20px) scale(1.05); }
          66% { transform: translate(20px, -15px) scale(0.95); }
        }
        @keyframes blobFloat2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(25px, -20px) scale(1.08); }
          66% { transform: translate(-15px, 25px) scale(0.92); }
        }
        @keyframes blobFloat3 {
          0%, 100% { transform: translate(-50%, 0) scale(1); }
          50% { transform: translate(-50%, -20px) scale(1.1); }
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// GLASSMORPHIC CARD
// ============================================================================

function GlassCard({
  children,
  className = "",
  glow = false,
  isDark = true,
}: {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  isDark?: boolean;
}) {
  return (
    <div
      className={`relative rounded-2xl border ${
        isDark ? "bg-white/[0.03] border-white/[0.08]" : "bg-gray-50/80 border-gray-200"
      } backdrop-blur-sm ${glow ? (isDark ? "shadow-[0_0_30px_rgba(168,85,247,0.1)]" : "shadow-lg") : ""} ${className}`}
    >
      {children}
    </div>
  );
}

// ============================================================================
// PIPELINE STEP ANIMATION
// ============================================================================

function PipelineStepper({ isDark }: { isDark: boolean }) {
  const steps = [
    {
      num: "01",
      title: "Choose Architecture",
      desc: "26 validated architectures. Pick the one that matches your behavior.",
      icon: (
        <svg viewBox="0 0 40 40" className="w-10 h-10">
          <circle cx="20" cy="12" r="4" fill="#a855f7" opacity="0.8" />
          <circle cx="10" cy="28" r="4" fill="#a855f7" opacity="0.5" />
          <circle cx="30" cy="28" r="4" fill="#a855f7" opacity="0.5" />
          <line x1="20" y1="16" x2="10" y2="24" stroke="#a855f7" strokeWidth="1" opacity="0.4" />
          <line x1="20" y1="16" x2="30" y2="24" stroke="#a855f7" strokeWidth="1" opacity="0.4" />
        </svg>
      ),
    },
    {
      num: "02",
      title: "Define Behaviors",
      desc: "Specify what the circuit should do. Working memory. Escape. Navigation.",
      icon: (
        <svg viewBox="0 0 40 40" className="w-10 h-10">
          <rect x="6" y="10" width="28" height="20" rx="3" fill="none" stroke="#a855f7" strokeWidth="1.5" opacity="0.6" />
          <line x1="12" y1="18" x2="28" y2="18" stroke="#a855f7" strokeWidth="1" opacity="0.4" />
          <line x1="12" y1="23" x2="22" y2="23" stroke="#a855f7" strokeWidth="1" opacity="0.4" />
        </svg>
      ),
    },
    {
      num: "03",
      title: "Compile Circuit",
      desc: "Evolution designs the wiring. 28K neurons. Biologically calibrated.",
      icon: (
        <svg viewBox="0 0 40 40" className="w-10 h-10">
          <path d="M8 20 L16 12 L24 20 L32 12" fill="none" stroke="#a855f7" strokeWidth="1.5" opacity="0.6" />
          <path d="M8 28 L16 20 L24 28 L32 20" fill="none" stroke="#c084fc" strokeWidth="1.5" opacity="0.4" />
        </svg>
      ),
    },
    {
      num: "04",
      title: "Growth Program",
      desc: "Output: which cell types, in what order, with what connections. Hand to a stem cell lab.",
      icon: (
        <svg viewBox="0 0 40 40" className="w-10 h-10">
          <circle cx="20" cy="20" r="12" fill="none" stroke="#a855f7" strokeWidth="1.5" opacity="0.4" />
          <circle cx="20" cy="20" r="6" fill="#a855f7" opacity="0.3" />
          <circle cx="20" cy="20" r="2" fill="#c084fc" />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {steps.map((step, i) => (
        <motion.div
          key={step.num}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.15, duration: 0.6 }}
        >
          <GlassCard isDark={isDark} className="p-6 h-full">
            <div className="flex items-center gap-3 mb-4">
              {step.icon}
              <span className="text-purple-500 text-xs font-mono tracking-wider">{step.num}</span>
            </div>
            <h3 className="text-lg font-medium mb-2">{step.title}</h3>
            <p className={`text-sm ${isDark ? "text-gray-400" : "text-gray-600"}`}>{step.desc}</p>
          </GlassCard>
          {i < steps.length - 1 && (
            <div className="hidden lg:flex justify-center mt-4 mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" className="text-purple-500/30 rotate-0">
                <path d="M5 12h14M12 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================================
// PULSE LINE DIVIDER
// ============================================================================

function PulseDivider() {
  return (
    <div className="flex justify-center py-16">
      <div className="relative w-full max-w-md h-[2px]">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
        <div
          className="absolute top-0 h-full w-20 bg-gradient-to-r from-transparent via-purple-400/60 to-transparent"
          style={{ animation: "pulseSweep 3s ease-in-out infinite" }}
        />
        <style jsx>{`
          @keyframes pulseSweep {
            0% { left: -20%; }
            100% { left: 100%; }
          }
        `}</style>
      </div>
    </div>
  );
}

// ============================================================================
// SECTION PROGRESS HOOK
// ============================================================================

function useSectionProgress(
  ref: React.RefObject<HTMLElement | null>,
  range: [number, number] = [0.1, 0.7],
  mounted: boolean = true
) {
  const [progress, setProgress] = useState(0);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!mounted) return;

    const timeoutId = setTimeout(() => {
      const handleScroll = () => {
        const el = ref.current;
        if (!el) return;

        const rect = el.getBoundingClientRect();
        const windowHeight = window.innerHeight;

        const start = windowHeight;
        const end = -rect.height;
        const current = rect.top;

        const rawProgress = 1 - (current - end) / (start - end);
        const clampedProgress = Math.max(0, Math.min(1, rawProgress));

        const rangeProgress = (clampedProgress - range[0]) / (range[1] - range[0]);
        setProgress(Math.max(0, Math.min(1, rangeProgress)));
      };

      handleScroll();
      window.addEventListener("scroll", handleScroll, { passive: true });
      window.addEventListener("resize", handleScroll, { passive: true });

      cleanupRef.current = () => {
        window.removeEventListener("scroll", handleScroll);
        window.removeEventListener("resize", handleScroll);
      };
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
    };
  }, [mounted, range[0], range[1]]);

  return progress;
}

// ============================================================================
// MAIN DECK PAGE
// ============================================================================

export default function PitchDeck() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  type ThemeMode = "dark" | "light" | "system";
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");
  const [systemPrefersDark, setSystemPrefersDark] = useState(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemPrefersDark(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setSystemPrefersDark(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const isDark = themeMode === "system" ? systemPrefersDark : themeMode === "dark";

  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  const tractionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("themeMode") as ThemeMode | null;
    if (stored) setThemeMode(stored);
  }, []);

  const toggleTheme = () => {
    const nextMode: ThemeMode =
      themeMode === "dark" ? "light" : themeMode === "light" ? "system" : "dark";
    setThemeMode(nextMode);
    localStorage.setItem("themeMode", nextMode);
  };

  const bg = isDark ? "bg-black" : "bg-white";
  const text = isDark ? "text-white" : "text-gray-900";
  const textMuted = isDark ? "text-gray-400" : "text-gray-600";
  const textSubtle = isDark ? "text-gray-500" : "text-gray-400";
  const cardBg = isDark ? "bg-white/5" : "bg-gray-50";
  const border = isDark ? "border-white/10" : "border-gray-200";

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`${bg} ${text} transition-colors duration-300 overflow-x-hidden`}
    >
      {/* Progress bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 h-0.5 bg-purple-600 origin-left z-50"
        style={{ scaleX: smoothProgress }}
      />

      {/* Back to home */}
      <Link
        href="/"
        className={`fixed top-4 left-4 sm:top-6 sm:left-6 z-50 px-3 py-2 rounded-full ${cardBg} border ${border} hover:bg-purple-500/20 transition-colors text-sm font-medium ${textMuted} flex items-center gap-1.5`}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        compile
      </Link>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className={`fixed top-4 right-4 sm:top-6 sm:right-6 z-50 p-2.5 rounded-full ${cardBg} border ${border} hover:bg-purple-500/20 transition-colors`}
        title={`Theme: ${themeMode}`}
      >
        {themeMode === "dark" ? (
          <Sun className="w-4 h-4" />
        ) : themeMode === "light" ? (
          <Moon className="w-4 h-4" />
        ) : (
          <Monitor className="w-4 h-4" />
        )}
      </button>

      {/* ================================================================ */}
      {/* SLIDE 1: HERO                                                    */}
      {/* ================================================================ */}
      <section className="relative min-h-screen flex items-center justify-center z-10">
        <div className="absolute inset-0 opacity-25">
          <NeuralNetworkAnimation width={1920} height={1080} />
        </div>
        <OrganicBlobs />

        <div className="relative w-full px-6 sm:px-12 py-20">
          <div className="max-w-5xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: "easeOut" }}
            >
              <div className="text-5xl sm:text-7xl lg:text-9xl font-extralight tracking-tight mb-8">
                compile
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              <p className="text-2xl sm:text-4xl lg:text-5xl font-light leading-tight mb-8">
                We design biological brains.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.8 }}
            >
              <p className={`text-base sm:text-lg ${textSubtle} uppercase tracking-[0.2em]`}>
                Seed Round | March 2026 | compile.now
              </p>
            </motion.div>
          </div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={textSubtle}>
            <path d="M12 5v14M5 12l7 7 7-7" />
          </svg>
        </motion.div>
      </section>

      {/* ================================================================ */}
      {/* SLIDE 2: PROBLEM                                                 */}
      {/* ================================================================ */}
      <section className="relative min-h-screen flex items-center py-20">
        <OrganicBlobs />
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">The Problem</div>
              <h2 className="text-3xl sm:text-5xl lg:text-6xl font-light leading-tight mb-6">
                1 in 3 people will develop<br />a brain disease.
              </h2>
              <p className={`text-xl sm:text-2xl ${textMuted} max-w-3xl`}>
                <span className="text-purple-400 font-medium">$280B market.</span> Zero tools to design the circuits that break.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <GlassCard isDark={isDark} className="p-8 sm:p-12 max-w-3xl">
                <p className={`text-lg sm:text-xl ${textMuted} leading-relaxed`}>
                  Drug development takes <span className={text}>15 years</span> with a{" "}
                  <span className={text}>95% failure rate</span>.
                </p>
                <p className={`text-lg sm:text-xl ${textMuted} leading-relaxed mt-4`}>
                  Why? We screen molecules against diseases we don't understand,
                  in brains we can't design.
                </p>
              </GlassCard>
            </motion.div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 3: SOLUTION                                                */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">The Solution</div>
              <h2 className="text-3xl sm:text-5xl lg:text-6xl font-light leading-tight mb-6">
                Design a brain circuit<br />the way you design a chip.
              </h2>
              <p className={`text-lg sm:text-xl ${textMuted} max-w-2xl mx-auto`}>
                Specify behaviors. Choose architecture. Compile onto a connectome.
                Generate a growth program. Hand to a stem cell lab.
              </p>
            </motion.div>

            <PipelineStepper isDark={isDark} />
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 4: TRACTION                                                */}
      {/* ================================================================ */}
      <section ref={tractionRef} className="relative py-24 sm:py-32">
        <OrganicBlobs />
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Traction</div>
              <h2 className="text-3xl sm:text-5xl lg:text-6xl font-light">
                It already works.
              </h2>
            </motion.div>

            <div className="grid grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 mb-16">
              {[
                { value: 26, suffix: "", label: "Architectures validated", sub: "From cellular automaton to reservoir computing" },
                { value: 33, suffix: "", label: "Research results", sub: "Across 2 species, 7 computational dimensions" },
                { value: 10, suffix: "", label: "Composite regions", sub: "28K neurons, zero degradation" },
                { value: 28, suffix: "K", label: "Neurons compiled", sub: "At physiological density" },
                { value: 85, suffix: "%", label: "Self-prediction accuracy", sub: "Recursive monitoring at 3 tiers" },
                { value: 2, suffix: "", label: "Species validated", sub: "Fly and mouse connectomes" },
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.6 }}
                >
                  <GlassCard isDark={isDark} glow className="p-6 sm:p-8 text-center h-full">
                    <div className="text-3xl sm:text-4xl lg:text-5xl font-light text-purple-400 mb-2">
                      <AnimatedNumber value={stat.value} suffix={stat.suffix} />
                    </div>
                    <div className="font-medium text-sm sm:text-base mb-1">{stat.label}</div>
                    <p className={`${textSubtle} text-xs sm:text-sm`}>{stat.sub}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 }}
            >
              <GlassCard isDark={isDark} className="p-6 sm:p-8 text-center max-w-3xl mx-auto">
                <p className={`text-base sm:text-lg ${textMuted}`}>
                  Architecture determines function. Different architectures for different tasks.{" "}
                  <span className="text-purple-400">
                    The ranking inverts with synaptic dynamics — proving architecture selection matters.
                  </span>
                </p>
              </GlassCard>
            </motion.div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 5: HOW IT WORKS                                            */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">How It Works</div>
              <h2 className="text-3xl sm:text-5xl font-light mb-6">
                From specification to tissue.
              </h2>
            </motion.div>

            <div className="space-y-8 max-w-3xl mx-auto">
              {[
                {
                  step: "1",
                  title: "Choose an architecture",
                  detail: "26 biologically calibrated architectures. Each tested across 7 computational dimensions. Pick the one that fits your behavior.",
                },
                {
                  step: "2",
                  title: "Define target behaviors",
                  detail: "Working memory, escape response, navigation, conflict resolution. The platform maps behaviors to circuit requirements.",
                },
                {
                  step: "3",
                  title: "Compile the circuit",
                  detail: "Evolutionary optimization designs the wiring on a real connectome. 28K neurons at physiological density. Output: a complete circuit specification.",
                },
                {
                  step: "4",
                  title: "Generate a growth program",
                  detail: "Reverse-compile to cell types, connection rules, and growth order. Sequential activity-dependent growth. Hand the recipe to a stem cell lab.",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.step}
                  initial={{ opacity: 0, x: -30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15, duration: 0.6 }}
                  className="flex gap-6 items-start"
                >
                  <div className="flex-shrink-0 w-12 h-12 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                    <span className="text-purple-400 font-mono text-lg">{item.step}</span>
                  </div>
                  <div>
                    <h3 className="text-xl font-medium mb-2">{item.title}</h3>
                    <p className={`${textMuted} text-sm sm:text-base`}>{item.detail}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 6: MARKET                                                  */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <OrganicBlobs />
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Market</div>
              <h2 className="text-3xl sm:text-5xl font-light">
                Three markets. One platform.
              </h2>
            </motion.div>

            <div className="grid sm:grid-cols-3 gap-6 sm:gap-8">
              {[
                {
                  market: "Pharma R&D",
                  size: "$80B/yr",
                  desc: "Disease modeling on designed circuits. Test drugs on brain tissue you actually understand. Replace animal models with purpose-built neural circuits.",
                },
                {
                  market: "Biotech / Organoid",
                  size: "$2B+",
                  desc: "Growth programs as product. Stem cell labs need circuit blueprints. We provide the design layer they are missing.",
                },
                {
                  market: "Research Institutions",
                  size: "Platform access",
                  desc: "Circuit design for neuroscience labs. Thousands of researchers studying brain circuits with no tool to design them.",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.market}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15, duration: 0.6 }}
                >
                  <GlassCard isDark={isDark} glow className="p-8 h-full">
                    <div className="text-3xl sm:text-4xl font-light text-purple-400 mb-3">
                      {item.size}
                    </div>
                    <h3 className="text-lg font-medium mb-3">{item.market}</h3>
                    <p className={`${textMuted} text-sm`}>{item.desc}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 7: BUSINESS MODEL                                          */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Business Model</div>
              <h2 className="text-3xl sm:text-5xl font-light">
                How we make money.
              </h2>
            </motion.div>

            <div className="grid sm:grid-cols-3 gap-6 sm:gap-8">
              {[
                {
                  title: "Platform SaaS",
                  tag: "Now",
                  desc: "Researchers design circuits on our platform. Architecture selection, behavioral compilation, growth program generation. Subscription access.",
                },
                {
                  title: "Growth Program Licensing",
                  tag: "Near-term",
                  desc: "Pharma and biotech license validated growth programs. Each program is a recipe for a specific neural circuit. Per-program licensing.",
                },
                {
                  title: "Wet Lab Services",
                  tag: "Future",
                  desc: "End-to-end circuit design and growth. From specification to validated organoid. Premium service tier for pharma partners.",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.15, duration: 0.6 }}
                >
                  <GlassCard isDark={isDark} className="p-8 h-full">
                    <div className="text-purple-500 text-xs uppercase tracking-wider mb-4">{item.tag}</div>
                    <h3 className="text-xl font-medium mb-3">{item.title}</h3>
                    <p className={`${textMuted} text-sm`}>{item.desc}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 8: DEFENSIBILITY                                           */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <OrganicBlobs />
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Defensibility</div>
              <h2 className="text-3xl sm:text-5xl font-light mb-6">
                Why this compounds.
              </h2>
              <p className={`text-lg ${textMuted} max-w-2xl mx-auto`}>
                The circuit library and growth programs — not the software — are the moat.
              </p>
            </motion.div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  icon: "01",
                  title: "Open Source Platform",
                  desc: "Community builds on top. Network effects from researcher adoption. The platform is the funnel, not the defensibility.",
                },
                {
                  icon: "02",
                  title: "33 Validated Results",
                  desc: "Years of computational head start. Each result calibrated against real connectome data. Replication takes time.",
                },
                {
                  icon: "03",
                  title: "26 Calibrated Architectures",
                  desc: "Across 7 computational dimensions. Each architecture tested for multiple behaviors. The catalog grows with every experiment.",
                },
                {
                  icon: "04",
                  title: "Cross-Species Conservation",
                  desc: "Hub-and-spoke architecture conserved from fly to mouse. This is fundamental biology, not engineering convention.",
                },
                {
                  icon: "05",
                  title: "Growth Program IP",
                  desc: "The recipes for growing specific circuits. Sequential growth order matters — random order produces zero function. The recipes are the product.",
                },
                {
                  icon: "06",
                  title: "AI Accelerates Us",
                  desc: "Better AI makes Compile faster. But the output is knowledge about biological tissue. AI cannot replace wet lab validation.",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.5 }}
                >
                  <GlassCard isDark={isDark} className="p-6 h-full">
                    <span className="text-purple-500/60 text-xs font-mono">{item.icon}</span>
                    <h3 className="text-base font-medium mt-2 mb-2">{item.title}</h3>
                    <p className={`${textMuted} text-sm`}>{item.desc}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 9: THE ASK                                                 */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">The Ask</div>
              <h2 className="text-4xl sm:text-6xl lg:text-7xl font-light">
                $1.5M seed.
              </h2>
            </motion.div>

            {/* Allocation grid */}
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-16">
              {[
                { amount: "$150K", label: "Wet Lab POC", detail: "Stem cell culture, MEA recordings, first connectivity validation." },
                { amount: "$300K", label: "Behavioral Validation", detail: "Closed-loop electrophysiology. Stimulate input, measure behavior." },
                { amount: "$400K", label: "Team (2 hires)", detail: "One computational scientist. One wet lab coordinator." },
                { amount: "$200K", label: "Compute", detail: "Architecture validation, simulation at scale, platform hosting." },
                { amount: "$200K", label: "Operations", detail: "18 months runway. Office, legal, IP filing." },
                { amount: "$250K", label: "Buffer", detail: "Biology rarely works on the first try. Budget for iteration." },
              ].map((item, i) => (
                <motion.div
                  key={item.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                >
                  <GlassCard isDark={isDark} className="p-5 sm:p-6 h-full">
                    <div className="text-2xl sm:text-3xl font-light text-purple-400 mb-1">{item.amount}</div>
                    <div className="text-sm font-medium mb-2">{item.label}</div>
                    <p className={`${textSubtle} text-xs`}>{item.detail}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>

            {/* Milestones */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <GlassCard isDark={isDark} glow className="p-6 sm:p-8">
                <h3 className="text-lg font-medium mb-6 text-center">Milestones</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[
                    { time: "Month 0-3", milestone: "Wet lab partnership. First organoids growing from simplest growth program." },
                    { time: "Month 3-6", milestone: "Connectivity validation. Do cell types connect as predicted?" },
                    { time: "Month 6-12", milestone: "Behavioral validation. Does the organoid produce predicted electrical patterns?" },
                    { time: "Month 12-18", milestone: "Second gen growth programs with wet lab feedback." },
                    { time: "Month 18-24", milestone: "Composite organoid. Multi-region with two architectural regions." },
                    { time: "Month 24+", milestone: "Platform generates growth programs. First paying customers." },
                  ].map((item) => (
                    <div key={item.time}>
                      <div className="text-purple-400 text-sm font-mono mb-1">{item.time}</div>
                      <p className={`${textMuted} text-sm`}>{item.milestone}</p>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 10: RISKS                                                  */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Honest Risks</div>
              <h2 className="text-3xl sm:text-5xl font-light">
                What could go wrong.
              </h2>
            </motion.div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  title: "Simulation-to-biology gap",
                  desc: "The fundamental risk. Computational predictions may not translate to biological reality. $150K gets the first data point.",
                },
                {
                  title: "Growth programs are hypotheses",
                  desc: "Every growth program is a recipe that biology will refine. We expect iteration. The value is the systematic framework.",
                },
                {
                  title: "Evolution finds fitness, not biology",
                  desc: "Circularity risk: evolution rewards what we measure. Mitigated by 9/10 predictions confirmed against experimental neuroscience.",
                },
                {
                  title: "Replication needed",
                  desc: "Results from one simulation framework. Independent replication by other labs is needed and planned.",
                },
                {
                  title: "Cognitive claims are grounded",
                  desc: "Working memory, conflict resolution, self-prediction. Each backed by specific experimental data. Not consciousness. Not AGI.",
                },
                {
                  title: "$150K answers the big question",
                  desc: "The wet lab POC is the de-risking experiment. If cell types connect as predicted, everything else follows. If not, we know early.",
                },
              ].map((risk, i) => (
                <motion.div
                  key={risk.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                >
                  <GlassCard isDark={isDark} className="p-6 h-full">
                    <h3 className="text-sm font-medium mb-2">{risk.title}</h3>
                    <p className={`${textMuted} text-sm`}>{risk.desc}</p>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 11: TEAM                                                   */}
      {/* ================================================================ */}
      <section className="relative py-24 sm:py-32">
        <div className="w-full px-6 sm:px-12">
          <div className="max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <div className="text-purple-500 text-xs uppercase tracking-[0.3em] mb-8">Team</div>
              <h2 className="text-3xl sm:text-5xl font-light">
                Builder who ships.
              </h2>
            </motion.div>

            <div className="max-w-lg mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <GlassCard isDark={isDark} glow className="p-8">
                  <h3 className="text-2xl font-medium mb-1">Mohamed El Tahawy</h3>
                  <div className="text-purple-400 text-sm mb-6">Founder</div>

                  <div className="space-y-4">
                    <div>
                      <div className={`text-sm font-medium mb-1 ${textSubtle}`}>Background</div>
                      <p className={`${textMuted} text-sm`}>
                        CS from NYU, math minor. Microsoft, Snap production systems.
                      </p>
                    </div>
                    <div>
                      <div className={`text-sm font-medium mb-1 ${textSubtle}`}>Track Record</div>
                      <p className={`${textMuted} text-sm`}>
                        Blockframe: 66K users, solo build. AppsAI: $300K revenue.
                      </p>
                    </div>
                    <div>
                      <div className={`text-sm font-medium mb-1 ${textSubtle}`}>This Project</div>
                      <p className={`${textMuted} text-sm`}>
                        One sprint: 33 results across 2 species. 3 cognitive capabilities, 8 reactive behaviors,
                        growth programs, cross-species validation. Honest about what is partial: attention is weak,
                        distraction control retracted.
                      </p>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      <PulseDivider />

      {/* ================================================================ */}
      {/* SLIDE 12: CLOSING                                                */}
      {/* ================================================================ */}
      <section className="relative min-h-[70vh] flex items-center py-24">
        <OrganicBlobs />
        <div className="absolute inset-0 opacity-10">
          <NeuralNetworkAnimation width={1920} height={1080} />
        </div>

        <div className="relative w-full px-6 sm:px-12">
          <div className="max-w-4xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 1 }}
            >
              <p className={`text-lg sm:text-xl ${textMuted} mb-8`}>
                Whoever designs biological neural circuits first owns the most fundamental
                abstraction layer in computing.
              </p>

              <h2 className="text-3xl sm:text-5xl lg:text-6xl font-light leading-tight mb-12">
                We design biological brains.
              </h2>

              <a
                href="mailto:founders@compile.now"
                className="inline-flex items-center gap-3 bg-purple-600 hover:bg-purple-500 text-white px-10 py-5 rounded-xl text-lg font-medium transition-all hover:scale-105 shadow-lg shadow-purple-600/20"
              >
                Let's talk
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </a>

              <p className={`${textSubtle} text-sm mt-8`}>compile.now</p>
            </motion.div>
          </div>
        </div>
      </section>

      <div className="h-8" />

      {/* Footer */}
      <footer className={`py-8 border-t ${border}`}>
        <div className="max-w-4xl mx-auto px-6 sm:px-12 text-center">
          <div className={`text-sm ${textSubtle}`}>&copy; 2026 Compile. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}
