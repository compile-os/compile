"use client";

import { useRef, useEffect, useState } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform, useSpring } from "framer-motion";
import { ArrowRight, ArrowDown } from "lucide-react";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";

// Dynamically import heavy components (client-only)
const HeroSection = dynamic(() => import("@/components/HeroSection"), { ssr: false });
const Brain3D = dynamic(() => import("@/components/Brain3D"), { ssr: false });

// Theme context with system support
type ThemeMode = "dark" | "light" | "system";

function useTheme() {
  const [mode, setMode] = useState<ThemeMode>("system");
  const [systemPrefersDark, setSystemPrefersDark] = useState(true);

  // Detect system preference
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemPrefersDark(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setSystemPrefersDark(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  // Load saved theme mode
  useEffect(() => {
    const stored = localStorage.getItem("themeMode") as ThemeMode | null;
    if (stored) setMode(stored);
  }, []);

  // Resolve the actual theme
  const theme: "dark" | "light" = mode === "system" ? (systemPrefersDark ? "dark" : "light") : mode;

  const toggleTheme = () => {
    // Cycle: dark -> light -> system -> dark
    const nextMode: ThemeMode = mode === "dark" ? "light" : mode === "light" ? "system" : "dark";
    setMode(nextMode);
    localStorage.setItem("themeMode", nextMode);
  };

  return { theme, mode, toggleTheme };
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const { theme, mode, toggleTheme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  // Parallax transforms
  const heroScale = useTransform(smoothProgress, [0, 0.3], [1, 0.95]);
  const heroOpacity = useTransform(smoothProgress, [0, 0.25], [1, 0]);
  const section1Y = useTransform(smoothProgress, [0.05, 0.25], [100, 0]);
  const section1Opacity = useTransform(smoothProgress, [0.05, 0.2], [0, 1]);
  const section2Y = useTransform(smoothProgress, [0.2, 0.4], [80, 0]);
  const section3Y = useTransform(smoothProgress, [0.35, 0.55], [80, 0]);

  // Brain parallax transforms
  const brainY = useTransform(smoothProgress, [0.1, 0.5], [200, -100]);
  const brainScale = useTransform(smoothProgress, [0.1, 0.35], [0.8, 1]);
  const brainOpacity = useTransform(smoothProgress, [0.1, 0.2, 0.45, 0.55], [0, 1, 1, 0]);
  const brainRotateY = useTransform(smoothProgress, [0.1, 0.5], [0, 45]);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = theme === "dark";
  const bg = isDark ? "bg-black" : "bg-white";
  const text = isDark ? "text-white" : "text-gray-900";
  const textMuted = isDark ? "text-gray-400" : "text-gray-600";
  const textSubtle = isDark ? "text-gray-500" : "text-gray-400";
  const border = isDark ? "border-white/10" : "border-gray-200";
  const cardBg = isDark ? "bg-white/5" : "bg-gray-50";

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`${bg} ${text} transition-colors duration-300`}>
      <Navbar theme={theme} themeMode={mode} onToggleTheme={toggleTheme} />

      {/* Hero - Full viewport */}
      <motion.section
        style={{ scale: heroScale, opacity: heroOpacity }}
        className="relative h-screen flex items-center justify-center overflow-hidden"
      >
        {/* Hero animation - works in both modes */}
        <div className="absolute inset-0">
          <HeroSection isDark={isDark} />
        </div>

        {/* Gradient fade */}
        <div className={`absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t ${isDark ? "from-black" : "from-white"} to-transparent`} />

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <ArrowDown className={`w-4 h-4 ${textSubtle}`} />
        </motion.div>
      </motion.section>

      {/* 3D Brain parallax element - only on desktop, floats on the right side */}
      <motion.div
        style={{
          y: brainY,
          scale: brainScale,
          opacity: brainOpacity,
        }}
        className="hidden md:block fixed right-0 top-1/2 -translate-y-1/2 w-[45vw] h-[70vh] pointer-events-auto z-10"
      >
        <Brain3D
          showNetwork={true}
          autoRotate={true}
          regionOpacity={0.5}
          floatIntensity={0.4}
          enableZoom={false}
        />
      </motion.div>

      {/* Hero text overlay */}
      <motion.section
        style={{ y: section1Y, opacity: section1Opacity }}
        className="relative py-16 md:py-32"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-8 md:max-w-2xl md:ml-8 lg:ml-16">
          <h1 className={`text-4xl sm:text-5xl md:text-7xl font-bold leading-tight ${text} mb-4`}>
            We design biological brains.
          </h1>
          <p className={`text-xl sm:text-2xl ${textMuted}`}>
            Compile is synthetic neuroscience. All results computational — wet lab validation next.
          </p>
        </div>
      </motion.section>

      {/* The Discovery */}
      <motion.section
        className="relative py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-8 md:max-w-3xl md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">What We Did</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-6`}>
            We reverse-engineered a fly brain. 139,255 neurons. We found which connections
            control which behaviors — and that the answer changes depending on what you optimize for.
          </p>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-6`}>
            Then we redesigned it. We compiled working memory, conflict resolution, and 8 reactive
            behaviors into the same connectome. We extracted the minimum circuit: 8,158 neurons
            specified by 19 developmental cell types.{" "}
            <span className={text}>The design principles transfer to mouse cortex.</span>
          </p>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted}`}>
            The missing piece: a{" "}
            <span className="text-purple-500">growth program</span> — the recipe that tells a stem cell
            lab which cell types to grow, in what proportions, so the right connectivity emerges.
            We produced the first one. Sequential activity-dependent growth — growing connections one hemilineage at a time, biased by neural activity — produces circuits that beat the real brain on navigation. Validating it in tissue is next.
          </p>
        </div>
      </motion.section>

      {/* Stats */}
      <section className="py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-8 md:max-w-3xl md:ml-8 lg:ml-16">
          <motion.div
            className="grid grid-cols-2 gap-6 sm:gap-8"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            {[
              { value: "22+1", label: "results (1 partial)", highlight: true },
              { value: "2", label: "cognitive capabilities" },
              { value: "1", label: "partial (attention)" },
              { value: "2", label: "species validated" },
            ].map((stat) => (
              <div key={stat.label} className="text-left">
                <div className={`text-3xl sm:text-4xl md:text-6xl font-extralight mb-2 ${(stat as any).highlight ? 'text-green-400' : ''}`}>{stat.value}</div>
                <div className={`text-xs sm:text-sm ${textSubtle} uppercase tracking-wider`}>{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Three-Layer Architecture */}
      <motion.section
        className="relative py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-8 md:max-w-3xl md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Results</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12`}>
            The connectome has three layers — but the proportions depend on the behavior.{" "}
            <span className={text}>Each behavior sees the same 2,450 connections differently.</span>
          </p>

          <div className="space-y-10">
            {/* Turning - most locked down */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <div className="flex items-baseline gap-3 mb-3">
                <span className={`text-sm font-medium ${text}`}>Turning</span>
                <span className={`text-xs ${textSubtle}`}>most locked-down</span>
              </div>
              <div className={`h-3 rounded-full ${isDark ? "bg-white/5" : "bg-gray-100"} overflow-hidden flex`}>
                <motion.div
                  className={`h-full ${isDark ? "bg-gray-700" : "bg-gray-300"}`}
                  initial={{ width: 0 }}
                  whileInView={{ width: "91%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.3 }}
                />
                <motion.div
                  className="h-full bg-purple-600 shadow-[0_0_12px_rgba(168,85,247,0.5)]"
                  initial={{ width: 0 }}
                  whileInView={{ width: "4%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.5 }}
                />
                <motion.div
                  className={`h-full ${isDark ? "bg-gray-800" : "bg-gray-200"}`}
                  initial={{ width: 0 }}
                  whileInView={{ width: "5%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.7 }}
                />
              </div>
              <div className="flex gap-4 mt-2">
                <span className={`text-xs ${textSubtle}`}>91% frozen</span>
                <span className="text-xs text-purple-400">4% evolvable</span>
                <span className={`text-xs ${textSubtle}`}>5% irrelevant</span>
              </div>
            </motion.div>

            {/* Escape - most plastic */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15 }}
            >
              <div className="flex items-baseline gap-3 mb-3">
                <span className={`text-sm font-medium ${text}`}>Escape</span>
                <span className={`text-xs ${textSubtle}`}>most plastic</span>
              </div>
              <div className={`h-3 rounded-full ${isDark ? "bg-white/5" : "bg-gray-100"} overflow-hidden flex`}>
                <motion.div
                  className={`h-full ${isDark ? "bg-gray-700" : "bg-gray-300"}`}
                  initial={{ width: 0 }}
                  whileInView={{ width: "8%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.45 }}
                />
                <motion.div
                  className="h-full bg-purple-600 shadow-[0_0_12px_rgba(168,85,247,0.5)]"
                  initial={{ width: 0 }}
                  whileInView={{ width: "89%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.65 }}
                />
                <motion.div
                  className={`h-full ${isDark ? "bg-gray-800" : "bg-gray-200"}`}
                  initial={{ width: 0 }}
                  whileInView={{ width: "3%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.85 }}
                />
              </div>
              <div className="flex gap-4 mt-2">
                <span className={`text-xs ${textSubtle}`}>8% frozen</span>
                <span className="text-xs text-purple-400">89% evolvable</span>
                <span className={`text-xs ${textSubtle}`}>4% irrelevant</span>
              </div>
            </motion.div>
          </div>

          <div className="flex gap-6 mt-6">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-2 rounded-sm ${isDark ? "bg-gray-700" : "bg-gray-300"}`} />
              <span className={`text-xs ${textSubtle}`}>Frozen</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-2 rounded-sm bg-purple-600" />
              <span className={`text-xs ${textSubtle}`}>Evolvable</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-2 rounded-sm ${isDark ? "bg-gray-800" : "bg-gray-200"}`} />
              <span className={`text-xs ${textSubtle}`}>Irrelevant</span>
            </div>
          </div>
        </div>
      </motion.section>

      {/* Different Behaviors, Different Wires */}
      <motion.section
        className="relative py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Different Behaviors, Different Wires</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12`}>
            Each behavior uses a completely different set of connections.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { name: "Navigation", pairs: "73 / 2,450", improvement: "3% evolvable", desc: "Bimodal split at module 25. Modules 0-24 frozen, 25-49 evolvable.", color: "#06b6d4", borderColor: "border-cyan-500/30" },
              { name: "Escape", pairs: "487 / 550", improvement: "88.5% evolvable", desc: "Most plastic behavior. Nearly every tested edge is modifiable.", color: "#ef4444", borderColor: "border-red-500/30" },
              { name: "Turning", pairs: "95 / 2,450", improvement: "3.9% evolvable", desc: "Most selective. 91.1% frozen. Only a narrow interface controls direction.", color: "#22c55e", borderColor: "border-green-500/30" },
              { name: "Arousal", pairs: "1,621 / 2,450", improvement: "66.2% evolvable", desc: "Global alertness modulation through broad sensory gating.", color: "#f59e0b", borderColor: "border-amber-500/30" },
            ].map((behavior, i) => (
              <motion.div
                key={behavior.name}
                className={`${cardBg} border ${behavior.borderColor} rounded-xl p-5`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: behavior.color }} />
                  <span className="font-medium">{behavior.name}</span>
                </div>
                <div className="flex gap-6 mb-3">
                  <div>
                    <div className={`text-xs ${textSubtle} uppercase`}>Evolvable Edges</div>
                    <div className="text-xl font-light">{behavior.pairs}</div>
                  </div>
                  <div>
                    <div className={`text-xs ${textSubtle} uppercase`}>Rate</div>
                    <div className="text-xl font-light text-purple-400">{behavior.improvement}</div>
                  </div>
                </div>
                <p className={`text-sm ${textMuted}`}>{behavior.desc}</p>
              </motion.div>
            ))}
          </div>

          {/* Callouts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            <motion.div
              className={`${cardBg} border ${border} rounded-xl p-5`}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 }}
            >
              <div className="text-sm font-medium text-purple-400 mb-2">Behavior-Dependent</div>
              <p className={`text-sm ${textMuted}`}>
                The same connectome looks 91% frozen to turning and 89% evolvable to escape. The architecture is not fixed — each behavior sees the wiring differently.
              </p>
            </motion.div>
            <motion.div
              className={`${cardBg} border ${border} rounded-xl p-5`}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 }}
            >
              <div className="text-sm font-medium text-purple-400 mb-2">Complete Edge Sweep</div>
              <p className={`text-sm ${textMuted}`}>
                All 2,450 inter-module edges tested deterministically per behavior. Not sampling — every connection classified.
              </p>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* How It Works - split layout with original SVG animation */}
      <motion.section style={{ y: section2Y }} className="py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-6">The Pipeline</h2>
            <p className={`text-xl ${textMuted} mb-4 max-w-2xl`}>
              Specify behaviors. The system designs the architecture. Compile, validate, grow. 26 architectures tested across 5 tasks. Composites validated to 28,000 neurons.
            </p>
            <p className={`text-lg ${textSubtle} mb-12 max-w-2xl`}>
              Steps 1-6 demonstrated computationally. Step 7 awaits wet lab.
            </p>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
              {/* Left side - Steps 1-4 */}
              <div className="space-y-8">
                {[
                  {
                    step: "01",
                    title: "Specify behaviors",
                    desc: "Describe what the brain should do. Navigation, working memory, conflict resolution. Each behavior tagged by computational requirement: speed, persistence, competition, rhythm, gating, adaptation.",
                    status: "demonstrated",
                  },
                  {
                    step: "02",
                    title: "Design architecture",
                    desc: "The system recommends an architecture — or a composite of multiple architectures — based on which computational properties the behaviors require. 26 architectures validated. Composites combine regions with interface connections.",
                    status: "demonstrated",
                  },
                  {
                    step: "03",
                    title: "Compile",
                    desc: "Generate a connectome from the architecture spec. Run directed evolution to find the wiring changes. The system discovers which connections matter for each behavior on the chosen architecture.",
                    status: "demonstrated",
                  },
                  {
                    step: "04",
                    title: "Validate",
                    desc: "Regression test against all existing behaviors. Measure interference. Classify capability family. Persistence test determines if behavior is reactive or cognitive. 9/10 predictions confirmed across species.",
                    status: "demonstrated",
                  },
                ].map((item, i) => (
                  <motion.div
                    key={item.step}
                    className="flex flex-col gap-3"
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                  >
                    <div className="flex items-baseline gap-4">
                      <span className={`text-3xl font-extralight ${textSubtle}`}>{item.step}</span>
                      <h3 className="text-xl font-medium">{item.title}</h3>
                    </div>
                    <p className={`text-lg ${textMuted} leading-relaxed ml-12`}>{item.desc}</p>
                  </motion.div>
                ))}
              </div>

              {/* Right side - Steps 5-7 */}
              <div className="space-y-8">
                {[
                  {
                    step: "05",
                    title: "Growth program",
                    desc: "Reverse-compile the circuit into a developmental recipe. Cell types, proportions, connection rules, spatial layout, growth order. The spec you hand to a stem cell lab. Minimum viable: 3,000 neurons per region.",
                    status: "demonstrated",
                  },
                  {
                    step: "06",
                    title: "Grow",
                    desc: "Sequential activity-dependent growth produces functional circuits from specification alone. Nav score 851 vs real brain 577. Composites validated to 28,000 neurons across 10 regions with no degradation. Stimulation during growth doesn't matter — architecture determines function.",
                    status: "demonstrated",
                  },
                  {
                    step: "07",
                    title: "Build in tissue",
                    desc: "Hand the growth program to a stem cell lab. The architecture spec defines cell types, proportions, connection rules, and growth order. Current organoids grow 1-3M neurons. The smallest viable circuit needs 3,000.",
                    status: "awaiting",
                  },
                ].map((item, i) => (
                  <motion.div
                    key={item.step}
                    className="flex flex-col gap-3"
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                  >
                    <div className="flex items-baseline gap-4">
                      <span className={`text-3xl font-extralight ${(item.status === 'awaiting' || item.status === 'partial') ? 'text-gray-600' : textSubtle}`}>{item.step}</span>
                      <h3 className={`text-xl font-medium ${(item.status === 'awaiting' || item.status === 'partial') ? 'text-gray-500' : ''}`}>{item.title}</h3>
                      {item.status === 'awaiting' && (
                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${isDark ? 'bg-white/5 text-gray-500' : 'bg-gray-100 text-gray-400'}`}>
                          awaiting wet lab
                        </span>
                      )}
                      {item.status === 'partial' && (
                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${isDark ? 'bg-yellow-500/10 text-yellow-500' : 'bg-yellow-50 text-yellow-600'}`}>
                          partial
                        </span>
                      )}
                    </div>
                    <p className={`text-lg ${(item.status === 'awaiting' || item.status === 'partial') ? 'text-gray-600' : textMuted} leading-relaxed ml-12`}>{item.desc}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* Built on remarkable work */}
      <motion.section style={{ y: section3Y }} className="py-16 md:py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Built on remarkable work</h2>
            <div className="space-y-4">
              <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted}`}>
                <span className={text}>FlyWire</span> mapped the brain.
              </p>
              <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted}`}>
                <span className={text}>Eon</span> brought it to life.
              </p>
              <p className={`text-xl sm:text-2xl leading-relaxed text-purple-500`}>
                Compile designs what comes next.
              </p>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* Validated by Biology */}
      <section className="py-16 md:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-4">Biology confirmed it</h2>
            <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12`}>
              Evolution rediscovered what neuroscience already knew — with zero biological labels.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              {[
                { behavior: "Turning", neuron: "DNa02", color: "#22c55e", borderColor: "border-green-500/30", desc: "Descending neuron controlling asymmetric leg movements. Identified by evolution as the dominant turning actuator." },
                { behavior: "Escape", neuron: "LPLC2", color: "#ef4444", borderColor: "border-red-500/30", desc: "Lobula plate columnar neuron detecting looming stimuli. Evolution found it as the escape trigger — matching known collision-avoidance circuits." },
                { behavior: "Arousal", neuron: "Visual Sensory", color: "#f59e0b", borderColor: "border-amber-500/30", desc: "Photoreceptor and early visual processing modules. Emerged as the arousal interface through evolution alone." },
              ].map((v, i) => (
                <motion.div
                  key={v.behavior}
                  className={`${cardBg} border ${v.borderColor} rounded-xl p-5`}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: v.color }} />
                    <span className={`text-xs uppercase tracking-wider ${textSubtle}`}>{v.behavior}</span>
                  </div>
                  <div className="text-lg font-medium mb-2" style={{ color: v.color }}>{v.neuron}</div>
                  <p className={`text-sm ${textMuted} leading-relaxed`}>{v.desc}</p>
                </motion.div>
              ))}
            </div>

            <p className={`text-lg ${textMuted} leading-relaxed`}>
              Our method identified <span className={text}>DNa02</span> as the key turning neuron, <span className={text}>LPLC2</span> as the escape trigger, and <span className={text}>visual sensory modules</span> as the arousal interface — matching decades of experimental neuroscience.{" "}
              <span className="text-purple-500">No biological labels were used. Evolution recovered ground truth on its own.</span>
            </p>
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 md:py-32 relative">
        <div className={`absolute inset-0 ${isDark ? "bg-gradient-to-t from-purple-950/20 to-transparent" : ""}`} />
        <div className="max-w-4xl mx-auto px-4 sm:px-8 text-center relative">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-light mb-6">
              We design biological brains.
            </h2>
            <p className={`text-xl ${textMuted} mb-10 max-w-xl mx-auto`}>
              Synthetic neuroscience starts now.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/research"
                className="group flex items-center gap-3 bg-purple-600 hover:bg-purple-500 text-white px-8 py-4 rounded-xl text-lg font-medium transition"
              >
                Read the research
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/deck"
                className={`px-8 py-4 text-lg ${textMuted} hover:${text} transition`}
              >
                View the deck
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className={`py-12 border-t ${border}`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3 sm:gap-4">
              <svg viewBox="0 0 44 40" className="w-7 h-7" aria-hidden="true"><line x1="12" y1="20" x2="32" y2="20" stroke="#9333EA" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="20" r="5" fill="#7C3AED"/><circle cx="32" cy="20" r="5" fill="#A855F7"/></svg>
              <span className="text-lg font-semibold">compile</span>
              <span className={`text-sm ${textSubtle}`}>Synthetic neuroscience</span>
            </div>
            <div className={`flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-sm ${textSubtle}`}>
              <Link href="/research" className={`hover:${text} transition`}>Research</Link>
              <Link href="/docs" className={`hover:${text} transition`}>Docs</Link>
              <Link href="/playground" className={`hover:${text} transition`}>Playground</Link>
              <Link href="/catalog" className={`hover:${text} transition`}>Catalog</Link>
              <Link href="/about" className={`hover:${text} transition`}>About</Link>
              <Link href="/deck" className={`hover:${text} transition`}>Deck</Link>
              <a href="https://github.com/compile-os" target="_blank" rel="noopener noreferrer" className={`hover:${text} transition`}>GitHub</a>
            </div>
            <div className={`text-sm ${textSubtle}`}>&copy; 2026 Compile. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
