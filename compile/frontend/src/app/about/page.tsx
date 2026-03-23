"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Navbar from "@/components/Navbar";

// Theme hook (matches home page pattern)
type ThemeMode = "dark" | "light" | "system";

function useTheme() {
  const [mode, setMode] = useState<ThemeMode>("system");
  const [systemPrefersDark, setSystemPrefersDark] = useState(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemPrefersDark(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setSystemPrefersDark(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("themeMode") as ThemeMode | null;
    if (stored) setMode(stored);
  }, []);

  const theme: "dark" | "light" = mode === "system" ? (systemPrefersDark ? "dark" : "light") : mode;

  const toggleTheme = () => {
    const nextMode: ThemeMode = mode === "dark" ? "light" : mode === "light" ? "system" : "dark";
    setMode(nextMode);
    localStorage.setItem("themeMode", nextMode);
  };

  return { theme, mode, toggleTheme };
}

const discoveries = [
  {
    title: "Directed Evolution on Connectomes",
    description:
      "We run directed evolution on complete connectomes -- the full wiring diagrams of biological brains. 2,450 inter-module edges tested deterministically per behavior, using 2x amplify and 0.5x attenuate perturbations.",
  },
  {
    title: "Behavior-Dependent Modifiability",
    description:
      "The evolvable surface is objective-dependent. Turning freezes 91.1% of connections. Escape makes 88.5% evolvable. Arousal opens 66.2%. The same wiring looks different to each behavior.",
  },
  {
    title: "Gene-Guided Processor and Growth Programs",
    description:
      "22 results across 2 species. 8,158 neurons selected by developmental hemilineage, 19x more active than module-selected (random control: 0/0/0/0/0). Two growth program families: state maintenance (83% hemilineage overlap, 15 base + 2-4 plugins) and selective gating (17% overlap, different circuits). Sequential activity-dependent growth produces functional circuits at physiological density (nav score 851 vs FlyWire 577) from specification alone. Mouse growth produces DSI=0.28.",
  },
  {
    title: "Zero-Label Biological Validation",
    description:
      "Our method independently recovered DNa02 (turning), LPLC2 (escape), and visual sensory modules (arousal) with zero biological labels. Evolution found what decades of experiments confirmed.",
  },
];

export default function AboutPage() {
  const [mounted, setMounted] = useState(false);
  const { theme, mode, toggleTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = theme === "dark";
  const bg = isDark ? "bg-black" : "bg-white";
  const text = isDark ? "text-white" : "text-gray-900";
  const textMuted = isDark ? "text-gray-400" : "text-gray-600";
  const textSubtle = isDark ? "text-gray-500" : "text-gray-400";
  const border = isDark ? "border-white/10" : "border-gray-200";
  const cardBg = isDark ? "bg-white/[0.02]" : "bg-gray-50";

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${bg} ${text} transition-colors duration-300`}>
      <Navbar theme={theme} themeMode={mode} onToggleTheme={toggleTheme} />

      {/* Hero */}
      <section className="pt-24 sm:pt-32 pb-12 sm:pb-16 px-4 sm:px-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Link
              href="/"
              className={`inline-flex items-center gap-2 ${textMuted} hover:${text} transition mb-8`}
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </Link>

            <h1 className="text-4xl sm:text-5xl md:text-7xl font-light mb-6">About</h1>
            <p className={`text-lg sm:text-xl ${textMuted} leading-relaxed max-w-3xl`}>
              We design biological brains. Specify a cognitive capability. Get the circuit architecture, growth program, and validation data.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Mission */}
      <section className={`py-12 sm:py-16 px-4 sm:px-8 border-y ${border} ${cardBg}`}>
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-6">Our Mission</h2>
            <p className={`text-xl sm:text-2xl md:text-3xl ${textMuted} leading-relaxed`}>
              We design biological brains.{" "}
              <span className={text}>The full stack:</span>{" "}
              specify a cognitive capability, compile it to a circuit,
              reverse-compile to a <span className="text-purple-400">growth program</span>.
              Cross-species validated on fly and mouse connectomes.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Values */}
      <section className="py-12 sm:py-20 px-4 sm:px-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-6 sm:mb-8">Our Values</h2>
            <p className={`text-lg sm:text-xl ${textMuted} leading-relaxed mb-8`}>
              We design biological brains. That sentence carries weight we do not take lightly. These values exist because the technology we are building demands them.
            </p>
            <div className="space-y-6">
              {[
                {
                  name: "Take the hardest questions seriously before they arrive",
                  detail: "Can a designed biological circuit experience something? We do not know. But by the time the answer is yes, it is too late to start thinking about it. We think about consciousness, suffering, and moral status now — while the work is computational — so that the frameworks exist before the technology forces them.",
                },
                {
                  name: "What we will not build matters more than what we will",
                  detail: "Every circuit we design comes with bounded behavioral specifications. What the circuit should not do is defined before what it should do. The power to design a brain is the power to constrain one. We treat that constraint as the primary responsibility, not a secondary concern.",
                },
                {
                  name: "Biology is irreversible",
                  detail: "Software can be rolled back. A living circuit cannot. When this work moves from simulation to tissue, every decision becomes permanent in a way that digital systems never are. We build the culture of irreversibility now, in simulation, so that it is instinct when the stakes are real.",
                },
                {
                  name: "Honesty is not optional at these stakes",
                  detail: "We retract claims that fail controls. We report negative results. We publish our limitations alongside our results. When you are building something this consequential, the cost of a false positive is not a bad paper — it is a designed system that should not exist. Credibility is the only foundation that holds.",
                },
                {
                  name: "Open by default",
                  detail: "This field exists because others shared their work openly. We build on open science and contribute back to it. Scrutiny is not a threat — it is the mechanism that keeps this work safe. If a result or a design cannot survive open review, it should not ship.",
                },
                {
                  name: "This technology must serve people who need it",
                  detail: "Brain repair. Precision psychiatry. Understanding neurological disease at the circuit level. The purpose of designing biological brains is to help the people whose brains are not working. That is the use case that justifies the risk, and it is the use case we optimize for.",
                },
              ].map((value, i) => (
                <motion.div
                  key={value.name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + 0.05 * i }}
                  className={`pl-5 border-l-2 ${isDark ? "border-purple-500/40" : "border-purple-400/60"}`}
                >
                  <h3 className={`text-base sm:text-lg font-medium mb-1 ${text}`}>{value.name}</h3>
                  <p className={`text-sm ${textMuted} leading-relaxed`}>{value.detail}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* What We Do */}
      <section className={`py-12 sm:py-20 px-4 sm:px-8 border-t ${border}`}>
        <div className="max-w-6xl mx-auto">
          <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-8 sm:mb-12">What We Do</h2>

          <div className="grid sm:grid-cols-2 gap-4 sm:gap-6">
            {discoveries.map((item, i) => (
              <motion.div
                key={item.title}
                className={`p-4 sm:p-6 rounded-xl border ${border} ${bg} hover:border-purple-500/30 transition`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i }}
              >
                <h3 className="text-base sm:text-lg font-medium mb-2">{item.title}</h3>
                <p className={`${textMuted} text-sm leading-relaxed`}>{item.description}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-8">
            <Link
              href="/research"
              className="inline-flex items-center gap-2 text-purple-400 hover:text-purple-300 transition"
            >
              View all experiments →
            </Link>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className={`py-12 sm:py-20 px-4 sm:px-8 border-t ${border} ${cardBg}`}>
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-6">The Team</h2>
            <p className={`text-xl sm:text-2xl ${textMuted} leading-relaxed`}>
              Founded by <span className={text}>Mohamed El Tahawy</span>. CS from NYU, math minor.
              Previously at Microsoft and Snap. Built Blockframe (66K users) and AppsAI ($300K revenue).
              Now designing biological brains with autonomous AI research agents on AWS.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Vision */}
      <section className="py-12 sm:py-20 px-4 sm:px-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-6">The Vision</h2>
            <p className={`text-xl sm:text-2xl md:text-3xl ${textMuted} leading-relaxed mb-6`}>
              FlyWire mapped the brain. Eon brought it to life. Cortical Labs proved neurons on chips can learn. Neuralink proved machines can talk to brains.{" "}
              <span className={text}>Compile designs the circuits.</span>
            </p>
            <p className={`text-xl sm:text-2xl ${textMuted} leading-relaxed`}>
              Every brain — <span className={text}>fly, mouse, human</span> — has a
              modifiability landscape. 22 results across 2 species. Hub-and-spoke architecture conserved across 600 million years of divergence.
              Sequential activity-dependent growth produces circuits that outperform the real brain from specification alone. The computational loop is closed.
            </p>
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className={`py-12 sm:py-20 px-4 sm:px-8 border-t ${border} ${isDark ? "bg-gradient-to-t from-purple-950/20 to-transparent" : ""}`}>
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-light mb-4">Explore the Research</h2>
          <p className={`${textMuted} mb-8`}>
            22 results across 2 species. All experiments, controls, and methodology — published.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {/* <Link
              href="/careers"
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-6 py-3 rounded-lg transition"
            >
              View Open Roles
            </Link> */}
            <Link
              href="/research"
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-6 py-3 rounded-lg transition"
            >
              View Research
            </Link>
            <a
              href="mailto:founders@compile.now"
              className={`inline-flex items-center gap-2 border ${border} hover:border-purple-500/40 ${textMuted} hover:${text} px-6 py-3 rounded-lg transition`}
            >
              founders@compile.now
            </a>
          </div>
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
              <Link href="/about" className={`hover:${text} transition`}>About</Link>
              {/* <Link href="/careers" className={`hover:${text} transition`}>Careers</Link> */}
              <a href="mailto:founders@compile.now" className={`hover:${text} transition`}>founders@compile.now</a>
            </div>
            <div className={`text-sm ${textSubtle}`}>&copy; 2026 Compile. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
