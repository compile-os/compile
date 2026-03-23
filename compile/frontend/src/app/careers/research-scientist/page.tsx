"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Navbar from "@/components/Navbar";
import ApplicationForm from "@/components/ApplicationForm";

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

export default function ResearchScientistPage() {
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

      <section className="pt-24 sm:pt-32 pb-6 sm:pb-8 px-4 sm:px-8">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Link
              href="/careers"
              className={`inline-flex items-center gap-2 ${textMuted} hover:${text} transition mb-8`}
            >
              <ArrowLeft className="w-4 h-4" />
              Careers
            </Link>

            <h1 className="text-3xl sm:text-4xl md:text-5xl font-light mb-4">Research Scientist</h1>
            <p className={textSubtle}>
              Full-time · New York · On-site
            </p>
          </motion.div>
        </div>
      </section>

      <section className="py-6 sm:py-8 px-4 sm:px-8">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className={`prose ${isDark ? "prose-invert" : ""} prose-gray max-w-none`}
          >
            <div className={`${isDark ? "text-gray-300" : "text-gray-700"} leading-relaxed space-y-6`}>
              <p>
                We design biological brains. Compile maps the modifiability landscape of complete connectomes, extracts gene-guided circuits,
                reverse-compiles to growth programs, and grows functional circuits from specification alone. 22 results across 2 species. 9/10 predictions confirmed. The computational loop is closed.
              </p>

              <p>
                We are looking for a research scientist to design growth programs that produce functional circuits,
                validate across species, and extend the circuit library to new connectomes and cognitive capabilities.
              </p>

              <h2 className={`text-xl font-medium ${text} mt-10 mb-4`}>What You Will Do</h2>
              <ul className={`list-disc list-outside ml-5 space-y-2 ${textMuted}`}>
                <li>Run deterministic edge sweeps on complete connectomes (FlyWire, BANC, MICrONS)</li>
                <li>Design and validate sequential activity-dependent growth programs across species</li>
                <li>Work with Izhikevich and LIF neuron models to compile cognitive capabilities</li>
                <li>Extend the growth program family taxonomy (state maintenance backbone, selective gating, plugins)</li>
                <li>Validate circuit designs against experimental neuroscience (DNa02, LPLC2, VIP→SST disinhibition)</li>
              </ul>

              <h2 className={`text-xl font-medium ${text} mt-10 mb-4`}>What We Look For</h2>
              <p className={textMuted}>You are a strong fit if you:</p>
              <ul className={`list-disc list-outside ml-5 space-y-2 ${textMuted}`}>
                <li>Have a PhD in neuroscience, computational neuroscience, or related field (or equivalent experience)</li>
                <li>Have deep understanding of connectomics, developmental neurobiology, or spiking neural networks</li>
                <li>Can bridge the gap between computational models and biological circuit design</li>
                <li>Are comfortable with ambiguity and can define research directions</li>
              </ul>

              <h2 className={`text-xl font-medium ${text} mt-10 mb-4`}>Nice to Have</h2>
              <ul className={`list-disc list-outside ml-5 space-y-2 ${textMuted}`}>
                <li>Experience with connectome datasets (FlyWire, BANC, MANC, MICrONS)</li>
                <li>Familiarity with Izhikevich or LIF neuron models and growth simulation</li>
                <li>Experience with directed evolution or genetic algorithms on neural systems</li>
                <li>Publications in computational neuroscience, developmental neurobiology, or related fields</li>
              </ul>
            </div>
          </motion.div>
        </div>
      </section>

      <section className={`py-8 sm:py-12 px-4 sm:px-8 border-t ${border}`}>
        <div className="max-w-3xl mx-auto">
          <ApplicationForm roleTitle="Research Scientist" />
        </div>
      </section>

      <footer className={`py-12 border-t ${border}`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4 sm:gap-6">
              <span className="text-lg font-semibold">compile</span>
              <span className={`text-sm ${textSubtle}`}>Synthetic neuroscience</span>
            </div>
            <div className={`flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-sm ${textSubtle}`}>
              <Link href="/research" className={`hover:${text} transition`}>Research</Link>
              <Link href="/docs" className={`hover:${text} transition`}>Docs</Link>
              <Link href="/playground" className={`hover:${text} transition`}>Playground</Link>
              <Link href="/about" className={`hover:${text} transition`}>About</Link>
              <Link href="/careers" className={`hover:${text} transition`}>Careers</Link>
            </div>
            <div className={`text-sm ${textSubtle}`}>&copy; 2026 Compile. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
