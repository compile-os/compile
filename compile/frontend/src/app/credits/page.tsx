"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink } from "lucide-react";
import Navbar from "@/components/Navbar";

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

const CREDITS = [
  {
    name: "FlyWire Consortium",
    role: "Connectome Data",
    description:
      "The complete wiring diagram of the adult Drosophila brain — 139,255 neurons and 50+ million synaptic connections. Published September 2024. The foundation of everything we built.",
    url: "https://flywire.ai",
    papers: [
      "Dorkenwald et al., \"Neuronal wiring diagram of an adult brain,\" Nature 2024",
      "Schlegel et al., \"Whole-brain annotation and multi-connectome cell typing,\" Nature 2024",
    ],
    color: "#06b6d4",
  },
  {
    name: "Eon Systems",
    role: "Embodied Brain Simulation",
    description:
      "Connected the FlyWire connectome to a physics-simulated body, achieving 91% behavioral accuracy. Their LIF neural model and NeuroMechFly integration made it possible to simulate fly behavior from the connectome alone.",
    url: "https://eon.systems",
    papers: [
      "Shiu et al., \"A leaky integrate-and-fire computational model based on the connectome of the entire adult Drosophila brain,\" bioRxiv 2023",
    ],
    color: "#a855f7",
  },
  {
    name: "Virtual Fly Brain",
    role: "3D Brain Template & Annotations",
    description:
      "The JRC2018 brain template and neuropil domain meshes used for our 3D visualization. An interactive atlas of the Drosophila nervous system maintained by an international consortium.",
    url: "https://virtualflybrain.org",
    papers: [
      "Matentzoglu et al., \"Virtual Fly Brain — An interactive atlas of the Drosophila nervous system,\" Frontiers in Physiology 2023",
    ],
    color: "#22c55e",
  },
  {
    name: "DeepMind & Janelia — FlyBody",
    role: "Anatomical Fly Body Model",
    description:
      "The anatomically-detailed Drosophila body model for MuJoCo physics simulation. 85 mesh files covering every body segment, leg, wing, and antenna. Used in our 3D Body visualization.",
    url: "https://github.com/TuragaLab/flybody",
    papers: [
      "Vaxenburg et al., \"Whole-body simulation of realistic fruit fly locomotion with deep reinforcement learning,\" Nature 2025",
    ],
    color: "#f59e0b",
  },
  {
    name: "Brian2 Simulator",
    role: "Reference Neural Model",
    description:
      "The Brian2 spiking neural network simulator, used for cross-validation of our PyTorch LIF results. Confirms our findings are model-independent.",
    url: "https://brian2.readthedocs.io",
    papers: [
      "Stimberg et al., \"Brian 2, an intuitive and efficient neural simulator,\" eLife 2019",
    ],
    color: "#ef4444",
  },
  {
    name: "FlyWire Cell Type Annotations",
    role: "Biological Classification",
    description:
      "Cell type classifications, neurotransmitter predictions, neuropil assignments, and coordinates for all 139K neurons. The biological labels that validated our computational findings.",
    url: "https://codex.flywire.ai",
    papers: [
      "Dorkenwald et al., \"FlyWire: online community for whole-brain connectomics,\" Nature Methods 2022",
    ],
    color: "#8b5cf6",
  },
  {
    name: "MICrONS (Allen Institute)",
    role: "Mouse Visual Cortex Connectome",
    description:
      "The MICrONS dataset provides a cubic millimeter of mouse visual cortex at synaptic resolution. Used for our cross-species validation (Result 11): 45% frozen, 49% evolvable -- confirming the three-layer architecture transfers to mammals.",
    url: "https://www.microns-explorer.org",
    papers: [
      "MICrONS Consortium, \"Functional connectomics spanning multiple areas of mouse visual cortex,\" bioRxiv 2021",
    ],
    color: "#3b82f6",
  },
  {
    name: "Cortical Labs",
    role: "Biological Computing Pioneer",
    description:
      "Proved that biological neurons on a chip can learn to play Pong. Their DishBrain work demonstrated that in-vitro neural cultures exhibit goal-directed behavior -- a foundational proof that biological computation is programmable.",
    url: "https://corticallabs.com",
    papers: [
      "Kagan et al., \"In vitro neurons learn and exhibit sentience when embodied in a simulated game-world,\" Neuron 2022",
    ],
    color: "#ec4899",
  },
  {
    name: "Experimental Neuroscience",
    role: "Ground Truth Validation",
    description:
      "Our results were validated against decades of experimental work identifying specific neurons and their behavioral roles. We particularly acknowledge:",
    url: null,
    papers: [
      "Yang et al., \"Fine-grained descending control of steering in walking Drosophila,\" Cell 2024 — DNa02 for turning",
      "Ache et al., \"Neural Basis for Looming Size and Velocity Encoding in the GF Escape Pathway,\" Current Biology 2019 — LPLC2 for escape",
      "Namiki et al., \"Descending networks transform command signals into population motor control,\" Nature 2024",
      "Hulse et al., \"A connectome of the Drosophila central complex,\" eLife 2021",
    ],
    color: "#10b981",
  },
];

export default function CreditsPage() {
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
  const cardBg = isDark ? "bg-white/[0.03]" : "bg-gray-50";

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

      {/* Header */}
      <section className="pt-32 pb-8 px-4 sm:px-8 max-w-4xl mx-auto">
        <Link href="/" className={`inline-flex items-center gap-2 text-sm ${textMuted} hover:${text} transition mb-8`}>
          <ArrowLeft className="w-4 h-4" /> Home
        </Link>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">Credits</h1>
        <p className={`${textMuted} text-lg max-w-2xl leading-relaxed`}>
          Compile is built on the work of thousands of scientists. The connectome data,
          simulation tools, body models, and experimental validations that made this
          possible are all open science. We stand on their shoulders.
        </p>
      </section>

      {/* Credits */}
      <section className="px-4 sm:px-8 max-w-4xl mx-auto pb-20">
        <div className="space-y-6">
          {CREDITS.map((credit, i) => (
            <motion.div
              key={credit.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className={`${cardBg} border ${border} rounded-xl p-6`}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: credit.color }} />
                    <h3 className="text-lg font-medium">{credit.name}</h3>
                  </div>
                  <div className={`text-sm ${textSubtle} ml-[22px]`}>{credit.role}</div>
                </div>
                {credit.url && (
                  <a
                    href={credit.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-1 text-xs ${textSubtle} hover:text-purple-400 transition`}
                  >
                    Visit <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              <p className={`text-sm ${textMuted} leading-relaxed mb-4 ml-[22px]`}>
                {credit.description}
              </p>

              <div className="ml-[22px] space-y-1.5">
                {credit.papers.map((paper, j) => (
                  <div key={j} className={`text-xs ${textSubtle} leading-relaxed pl-3 border-l-2`} style={{ borderColor: credit.color + '40' }}>
                    {paper}
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footer note */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className={`mt-12 text-sm ${textSubtle} leading-relaxed max-w-2xl`}
        >
          All connectome data used in this project is publicly available under open licenses.
          Our evolution engine, analysis pipeline, and platform code will be open-sourced.
          If we&apos;ve missed anyone or cited incorrectly, please contact us at{" "}
          <a href="mailto:founders@compile.now" className="text-purple-400 hover:underline">
            founders@compile.now
          </a>.
        </motion.div>
      </section>

      {/* Footer */}
      <footer className={`py-12 border-t ${border}`}>
        <div className="max-w-4xl mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <svg viewBox="0 0 44 40" className="w-7 h-7" aria-hidden="true"><line x1="12" y1="20" x2="32" y2="20" stroke="#9333EA" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="20" r="5" fill="#7C3AED"/><circle cx="32" cy="20" r="5" fill="#A855F7"/></svg>
              <span className="text-lg font-semibold">compile</span>
              <span className={`text-sm ${textSubtle}`}>Synthetic neuroscience</span>
            </div>
            <div className={`text-sm ${textSubtle}`}>&copy; 2026 Compile. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
