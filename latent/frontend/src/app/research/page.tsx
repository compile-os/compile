"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
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

export default function ResearchPage() {
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
  const cardBg = isDark ? "bg-white/5" : "bg-gray-50";

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className={`${bg} ${text} transition-colors duration-300`}>
      <Navbar theme={theme} themeMode={mode} onToggleTheme={toggleTheme} />

      {/* Header */}
      <section className="pt-32 pb-16 md:pt-40 md:pb-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <Link href="/" className={`inline-flex items-center gap-2 text-sm ${textSubtle} hover:${text} transition mb-8`}>
            <ArrowLeft className="w-4 h-4" />
            Home
          </Link>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-light mb-6">Research</h1>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted}`}>
            33 results across fly and mouse connectomes. 26 neural architectures tested. 10-region composites validated. Recursive self-monitoring from a growth program.
          </p>
        </div>
      </section>

      {/* Open Questions — The Big Ones */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Open Questions</h2>
          <div className="space-y-6">
            {[
              "Is there a universal grammar of neural circuit design \u2014 a finite set of architectural primitives from which all brain computation can be composed?",
              "Can we design a brain that outperforms evolution \u2014 not just on one task, but across the full space of possible behaviors?",
              "What is the theoretical limit of biological computation? How many behaviors can a single connectome support before interference makes additional capabilities impossible?",
              "If we can design brains, can we design the process of designing brains \u2014 circuits that generate growth programs for other circuits?",
            ].map((question, i) => (
              <motion.div
                key={i}
                className="flex gap-4 items-start"
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <span className="text-purple-500 text-lg font-light mt-0.5">{String(i + 1).padStart(2, "0")}</span>
                <p className={`text-lg leading-relaxed ${textMuted}`}>{question}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* 1. The Question */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">The Question</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-8`}>
            A brain has 139,255 neurons and millions of connections. If you want to change a behavior —
            make the fly turn harder, escape faster, navigate better — which connections do you modify?
            And does the answer depend on <span className={text}>which behavior</span> you&apos;re targeting?
          </p>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted}`}>
            We tested this empirically. We systematically perturbed every inter-module connection
            in a complete fly brain and measured which ones matter for which behaviors.
            The answer: <span className={text}>the modifiability landscape is objective-dependent</span>.
            Each behavior sees a different evolvable surface on the same connectome.
          </p>
        </div>
      </motion.section>

      {/* 2. The Setup */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">The Setup</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-8`}>
            We started with the <span className={text}>FlyWire connectome</span> — the complete wiring
            diagram of an adult fruit fly brain. 139,255 neurons. 50 million synaptic connections.
            Published by the FlyWire consortium in September 2024.
          </p>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-8`}>
            We loaded this connectome into a leaky integrate-and-fire neural simulator. We defined a
            behavior — navigation toward food — as a fitness function that measures how well the
            simulated fly approaches a food source.
          </p>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-8`}>
            Then we ran a <span className={text}>complete deterministic edge sweep</span>. For each of
            the 2,450 inter-module edges, we applied two perturbations: amplification (2x) and
            attenuation (0.5x). We measured the fitness delta and classified each edge as frozen
            (fitness decreases), evolvable (fitness increases), or irrelevant (no significant change).
            Repeated for 4 behaviors: navigation, escape, turning, and arousal.
            <span className={textSubtle}> Caveat: edge classification is scale-dependent. At 1.5x perturbation,
            44% of edges match the 2x classification. At 5x, only 22% match. The qualitative pattern
            (turning is more frozen than escape) holds across scales, but the specific percentages are
            artifacts of the 2x/0.5x choice.</span>
          </p>
          <p className={`text-lg leading-relaxed ${textMuted}`}>
            In total: <span className={text}>2,450 inter-module edges tested deterministically per behavior</span> on{" "}
            <span className={text}>5 parallel EC2 instances</span>,{" "}
            <span className={text}>10-22 hours per complete sweep</span>.
          </p>
          <p className={`text-sm leading-relaxed ${textSubtle} mt-4`}>
            Note on circuit sizes: Results 1-21 use the full FlyWire connectome (139,255 neurons) or the gene-guided subset (8,158 neurons). Results 22-33 use generated connectomes at 3,000-28,000 neurons. Different results operate at different scales because the questions are different — the FlyWire results map a real brain, the architecture results test design principles.
          </p>
        </div>
      </motion.section>

      {/* 3. Hypothesis */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Hypothesis</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-10`}>
            If the connectome has objective-dependent modifiability, then:
          </p>
          <div className="space-y-6">
            {[
              "Each behavior should have a specific evolvable surface — not random sensitivity.",
              "Different behaviors should see DIFFERENT evolvable surfaces — not the same one.",
              "The evolvable connections should match known neuroscience — not arbitrary wiring.",
              "The evolvable surface should change shape under multi-objective pressure.",
            ].map((prediction, i) => (
              <motion.div
                key={i}
                className="flex gap-4 items-start"
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <span className="text-purple-500 text-lg font-light mt-0.5">{i + 1}.</span>
                <p className={`text-lg leading-relaxed ${text}`}>{prediction}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* 4. Results */}

      {/* Result 1: Three-Layer Architecture */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 1 — The Three-Layer Architecture Is Behavior-Dependent</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12`}>
            A complete deterministic sweep of all 2,450 inter-module edges reveals that the three-layer
            architecture exists for every behavior — but with radically different proportions.
          </p>

          <div className="space-y-8 mb-10">
            {[
              { name: "Turning", frozen: 91.1, evolvable: 3.9, irrelevant: 5, note: "most locked-down", color: "#22c55e" },
              { name: "Navigation", frozen: 92, evolvable: 3, irrelevant: 5, note: "bimodal: modules 0-24 frozen, 25-49 evolvable", color: "#06b6d4" },
              { name: "Arousal", frozen: 23, evolvable: 66.2, irrelevant: 10.8, note: "broadly plastic", color: "#f59e0b" },
              { name: "Escape", frozen: 8, evolvable: 88.5, irrelevant: 3.5, note: "most plastic", color: "#ef4444" },
            ].map((behavior, i) => (
              <motion.div
                key={behavior.name}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="flex items-baseline gap-3 mb-2">
                  <div className="w-2.5 h-2.5 rounded-full mt-1" style={{ backgroundColor: behavior.color }} />
                  <span className={`text-sm font-medium ${text}`}>{behavior.name}</span>
                  <span className={`text-xs ${textSubtle}`}>{behavior.note}</span>
                </div>
                <div className={`h-3 rounded-full ${isDark ? "bg-white/5" : "bg-gray-100"} overflow-hidden flex`}>
                  <motion.div
                    className={`h-full ${isDark ? "bg-gray-700" : "bg-gray-300"}`}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${behavior.frozen}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 1, delay: 0.3 + i * 0.1 }}
                  />
                  <motion.div
                    className="h-full bg-purple-600 shadow-[0_0_12px_rgba(168,85,247,0.5)]"
                    initial={{ width: 0 }}
                    whileInView={{ width: `${behavior.evolvable}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 1, delay: 0.5 + i * 0.1 }}
                  />
                  <motion.div
                    className={`h-full ${isDark ? "bg-gray-800" : "bg-gray-200"}`}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${behavior.irrelevant}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 1, delay: 0.7 + i * 0.1 }}
                  />
                </div>
                <div className="flex gap-4 mt-1">
                  <span className={`text-xs ${textSubtle}`}>{behavior.frozen}% frozen</span>
                  <span className="text-xs text-purple-400">{behavior.evolvable}% evolvable</span>
                  <span className={`text-xs ${textSubtle}`}>{behavior.irrelevant}% irrelevant</span>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="flex gap-6 mb-8">
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

          <p className={`text-lg leading-relaxed ${textMuted}`}>
            The three-layer architecture exists for every behavior, but with radically different proportions.{" "}
            <span className="text-purple-400">The evolvable surface is objective-dependent — each behavior sees a different brain.</span>
          </p>
        </div>
      </motion.section>

      {/* Result 2: Different Behaviors, Different Wires */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 2 — Different Behaviors, Different Wires</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Complete edge sweeps (2,450 edges each) reveal that each behavior uses a vastly different
            fraction of the connectome as its evolvable surface.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { name: "Navigation", edges: "73 evolvable", total: "of 2,450 tested", rate: "6%", desc: "Bimodal split at module 25. First half of connectome only.", color: "#06b6d4", borderColor: "border-cyan-500/30" },
              { name: "Escape", edges: "487 evolvable", total: "of 550 tested", rate: "89%", desc: "Most plastic behavior. Nearly every tested edge is modifiable.", color: "#ef4444", borderColor: "border-red-500/30" },
              { name: "Turning", edges: "95 evolvable", total: "of 2,450 tested", rate: "3.9%", desc: "Most selective. 91.1% frozen. Only a narrow interface controls turning.", color: "#22c55e", borderColor: "border-green-500/30" },
              { name: "Arousal", edges: "1,621 evolvable", total: "of 2,450 tested", rate: "66.2%", desc: "Broadly plastic. Global alertness uses most of the wiring.", color: "#f59e0b", borderColor: "border-amber-500/30" },
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
                    <div className="text-xl font-light">{behavior.edges}</div>
                    <div className={`text-xs ${textSubtle}`}>{behavior.total}</div>
                  </div>
                  <div>
                    <div className={`text-xs ${textSubtle} uppercase`}>Rate</div>
                    <div className="text-xl font-light text-purple-400">{behavior.rate}</div>
                  </div>
                </div>
                <p className={`text-sm ${textMuted}`}>{behavior.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="max-w-3xl mt-10">
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The same connectome looks 91% frozen to turning and 89% evolvable to escape.{" "}
              <span className="text-purple-400">The three-layer architecture is real, but the proportions are behavior-dependent — not a fixed property of the wiring.</span>
            </p>
          </div>
        </div>
      </motion.section>

      {/* Result 3: Biological Validation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 3 — Biological Validation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Evolution, running blind with zero biological labels, found the same neurons that
            experimental neuroscience identified through decades of optogenetics and calcium imaging.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            {[
              { behavior: "Turning", neuron: "DNa02", color: "#22c55e", borderColor: "border-green-500/30", desc: "Module 19, targeted by turning evolution, contains DNa02 — the experimentally proven turning neuron (Yang et al., Cell 2024)." },
              { behavior: "Escape", neuron: "LPLC2", color: "#ef4444", borderColor: "border-red-500/30", desc: "Module 11, targeted by escape evolution, has the highest LPLC2 concentration of any module — the proven looming detector." },
              { behavior: "Arousal", neuron: "Visual Sensory", color: "#f59e0b", borderColor: "border-amber-500/30", desc: "Module 5, targeted by arousal evolution, is 86% visual sensory neurons — photoreceptors and early visual processing." },
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

          <div className={`${cardBg} border ${border} rounded-xl p-5`}>
            <p className={`text-sm ${textMuted} leading-relaxed`}>
              <span className="text-purple-400 font-medium">Note:</span>{" "}
              Formal statistical enrichment is not significant because these cell types are distributed
              across many modules. The validation is qualitative: evolution consistently found the modules
              with the <span className={text}>highest concentrations</span> of the experimentally relevant
              cell types.
            </p>
          </div>
        </div>
      </motion.section>

      {/* Result 4: The Pipeline Works on Novel Behaviors */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 4 — The Pipeline Works on Novel Behaviors</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            To prove this isn&apos;t limited to the 4 behaviors we chose, we compiled two behaviors
            no fly has ever been evolved for.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <motion.div
              className={`${cardBg} border border-green-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "#22c55e" }} />
                <span className={`text-xs uppercase tracking-wider ${textSubtle}`}>Circles</span>
              </div>
              <div className="text-lg font-medium mb-3 text-green-400">Walk in circles — sustained rotation</div>
              <p className={`text-sm ${textMuted} mb-3`}>
                Evolution found <span className={text}>4 connections</span>, <span className={text}>3 completely novel</span>.
              </p>
              <div className="flex gap-6">
                <div>
                  <div className={`text-xs ${textSubtle} uppercase`}>Verification</div>
                  <div className="text-xl font-light text-green-400">+86%</div>
                  <div className={`text-xs ${textSubtle}`}>angular displacement</div>
                </div>
              </div>
            </motion.div>

            <motion.div
              className={`${cardBg} border border-amber-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "#f59e0b" }} />
                <span className={`text-xs uppercase tracking-wider ${textSubtle}`}>Rhythm</span>
              </div>
              <div className="text-lg font-medium mb-3 text-amber-400">Rhythmic walking — 2s walk, 1s stop</div>
              <p className={`text-sm ${textMuted} mb-3`}>
                Evolution found <span className={text}>5 connections</span>, <span className={text}>2 completely novel</span>,
                with connections to core timing modules never touched by simpler behaviors.
              </p>
            </motion.div>
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Evolution finds genuinely new wiring for genuinely new behaviors.{" "}
              <span className="text-purple-400 font-medium">5 completely novel connections</span> from
              arbitrary compilation. The evolvable surface scales with behavioral complexity.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 5: Izhikevich Conflict Resolution */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 5 — Izhikevich Conflict Resolution</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Switching from LIF to Izhikevich neurons resolved inter-behavior conflicts and demonstrated
            model-independent circuit design. The same edge (19 to 4) emerged as critical across both neural models.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "153%", label: "fitness improvement" },
              { value: "15", label: "mutations" },
              { value: "96%", label: "conflict coexistence" },
              { value: "19 to 4", label: "model-independent edge" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              When LIF neurons created conflicts between behaviors, Izhikevich neurons (which model richer spike dynamics)
              resolved them naturally. The edge from module 19 to module 4 emerged as critical in both models --{" "}
              <span className="text-purple-400 font-medium">suggesting the circuit design is a property of the wiring, not the neuron model</span>.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 6: Multi-Objective Evolution */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 6 — Multi-Objective Evolution Reveals Hidden Feedback Loops</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            When optimizing for navigation AND turning simultaneously, evolution found connections
            invisible to single-behavior optimization. Multi-objective pressure reveals hidden feedback loops
            that only become useful when the brain must balance multiple objectives.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <motion.div
              className={`${cardBg} border border-purple-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "#a855f7" }} />
                <span className={`text-xs uppercase tracking-wider ${textSubtle}`}>Edge 11 to 38</span>
              </div>
              <div className="text-lg font-medium mb-3 text-purple-400">aDN1 module / JO input hub</div>
              <p className={`text-sm ${textMuted} mb-3`}>
                <span className={text}>Frozen</span> for navigation alone. But when optimizing for both
                navigation and turning, this reciprocal feedback loop becomes evolvable — enabling
                multi-behavior switching.
              </p>
            </motion.div>

            <motion.div
              className={`${cardBg} border border-purple-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "#a855f7" }} />
                <span className={`text-xs uppercase tracking-wider ${textSubtle}`}>Edge 19 to 4</span>
              </div>
              <div className="text-lg font-medium mb-3 text-purple-400">Two DN hubs</div>
              <p className={`text-sm ${textMuted} mb-3`}>
                <span className={text}>Irrelevant</span> for navigation alone. But critical for
                dual-behavior competence — connecting two descending neuron hubs through a
                feedback loop.
              </p>
            </motion.div>
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Both discovered connections form <span className="text-purple-400 font-medium">reciprocal feedback loops</span>.
              They are invisible to single-behavior sweeps because they only become useful when the
              brain must balance multiple objectives simultaneously. The evolvable surface is not fixed —{" "}
              <span className="text-purple-400 font-medium">it expands under multi-objective pressure</span>.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 7: General-Purpose Biological Processor */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 7 — General-Purpose Biological Processor</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            A single subnetwork of 20,626 neurons supports 5 of 6 compiled behaviors. Essential hubs
            at modules 4 and 19 serve as convergence points for multi-behavior coordination.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "20,626", label: "neurons in processor" },
              { value: "5/6", label: "behaviors compiled" },
              { value: "4 & 19", label: "essential hub modules" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The fly brain contains a general-purpose biological processor -- a shared substrate that can be
              configured for different behaviors through targeted connection modifications.{" "}
              <span className="text-purple-400 font-medium">This is preliminary evidence that biological neural circuits
              have a programmable core, analogous to a general-purpose CPU</span>.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 8: Gene-Guided Circuit Extraction */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 8 — Gene-Guided Circuit Extraction</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Instead of selecting neurons by module ID (a clustering artifact), we selected by
            developmental hemilineage — the transcription factor identity that specifies each
            neuron during development. The result: a smaller, dramatically better circuit.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "8,158", label: "neurons (60% fewer)" },
              { value: "19x", label: "more active than module-selected" },
              { value: "19", label: "hemilineages specified" },
              { value: "5/6", label: "behaviors active" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Cell type specification is sufficient. A random selection of the same number of neurons
              produces zero activity across 5 trials (0 nav score vs gene-guided 834). The difference: gene-guided
              neurons form 13x more internal synapses because developmental lineage determines connectivity.{" "}
              <span className="text-purple-400 font-medium">This is the growth program: &quot;differentiate
              stem cells into these 19 neuron types in these proportions. The connectivity follows from identity.&quot;</span>{" "}
              That is how real brain development works — and it means
              the gap between circuit design and biological implementation is smaller than assumed.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 9: The First Growth Program */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 9 — The First Growth Program</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We reverse-compiled the gene-guided circuit to a developmental specification:
            19 cell types, 30 connection rules, spatial layout, and neurotransmitter profiles.
            The specification recovers 49% of individual neurons at 97.6% AUROC using a two-phase
            developmental program: first cell types, then connectivity — but the dominant predictor (common neighbors) is circular, requiring existing connectivity to compute. Implementable features alone (distance, NT compatibility, flow) achieve 7-9%. The real validation is behavioral: sequential activity-dependent growth produces functional circuits at physiological density (nav score 851 vs FlyWire 577) from specification alone. Growth order is critical — the developmental sequence is part of the specification. Mouse bundle growth produces DSI=0.28.
            The computational loop is closed.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            {[
              { title: "Cell Type Recipe", desc: "19 hemilineages. 14 cholinergic, 2 GABAergic, 2 dopaminergic. Proportions specified.", color: "border-cyan-500/30" },
              { title: "Connection Rules", desc: "30 hemilineage-to-hemilineage rules. Probability and weight per pair. Distance-dependent.", color: "border-purple-500/30" },
              { title: "Spatial Layout", desc: "3D positions for each hemilineage cluster. Centroids from FlyWire soma coordinates.", color: "border-amber-500/30" },
            ].map((card, i) => (
              <motion.div
                key={card.title}
                className={`${cardBg} border ${card.color} rounded-xl p-5`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className={`text-sm font-medium ${text} mb-2`}>{card.title}</div>
                <p className={`text-sm ${textMuted} leading-relaxed`}>{card.desc}</p>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The full stack: specify a cognitive capability, compile to a circuit, reverse-compile to a growth program.{" "}
              <span className="text-purple-400 font-medium">CRISPR edits the source code (DNA).
              Compile designs the compiled output (circuits). The developmental pipeline translates between them.</span>{" "}
              This is the foundation of synthetic neuroscience.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 10: Compositional Programming */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 10 — Compositional Programming</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Multi-objective evolution achieves +270% improvement over single-behavior optimization,
            with both navigation and escape preserved in the same circuit. Behaviors compose without interference.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "+270%", label: "multi-objective improvement" },
              { value: "Nav + Escape", label: "both preserved" },
              { value: "96%", label: "conflict coexistence" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Compositional programming means behaviors can be stacked on the same circuit without
              destructive interference.{" "}
              <span className="text-purple-400 font-medium">The evolvable surface expands under multi-objective
              pressure, enabling simultaneous optimization of competing behaviors.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 11: Cross-Species Validation (Mouse V1) */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 11 — Cross-Species Validation (Mouse V1)</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Applied the same methodology to the MICrONS mouse visual cortex connectome.
            The three-layer architecture transfers across species: 45% of connections are frozen,
            49% are evolvable. Design principles are not fly-specific.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "45%", label: "frozen in mouse V1" },
              { value: "49%", label: "evolvable in mouse V1" },
              { value: "2", label: "species validated" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The mouse visual cortex shows the same frozen/evolvable/irrelevant architecture as the fly brain.{" "}
              <span className="text-purple-400 font-medium">The modifiability landscape is a general property of
              neural circuits, not a species-specific artifact. The design principles transfer across brains.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 12: Predictive Validation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 12 — Predictive Validation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We pre-registered predictions before running experiments and tested them.
            For navigation: 5/5 predictions confirmed including an untargeted secondary effect
            (escape improved +58% as a side effect of navigation optimization).
            For working memory: 4/5 confirmed. The framework predicts which cell types matter
            and what secondary effects to expect.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "5/5", label: "navigation predictions" },
              { value: "4/5", label: "working memory predictions" },
              { value: "+58%", label: "untargeted escape improvement" },
              { value: "9/10", label: "total predictions confirmed" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              This breaks the circularity argument. Not &quot;optimize X, measure X.&quot; But &quot;optimize X, predict Y changes as side effect, verify Y.&quot;{" "}
              <span className="text-purple-400 font-medium">The framework has explanatory power, not just optimization power.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 13: Working Memory Compilation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 13 — Working Memory Compilation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We compiled working memory into the full 139,255-neuron brain using Izhikevich neurons.
            The brain maintains a navigation representation through 500 steps of silence via central
            complex attractor dynamics, then uses that memory to bias behavior when both stimuli are
            presented simultaneously.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "+29%", label: "fitness improvement" },
              { value: "3.8x", label: "navigation bias (choice phase)" },
              { value: "60,518", label: "CX persistence spikes" },
              { value: "6", label: "mutations" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Working memory compiles to the full brain using the same architecture that handles navigation
              and conflict resolution.{" "}
              <span className="text-purple-400 font-medium">The pipeline generalizes across cognitive capabilities,
              not just behaviors within a single capability.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 14: Shared Cognitive Backbone */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 14 — Shared Cognitive Backbone</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Working memory and conflict resolution converge on the same descending neuron hubs
            (modules 4 and 19) through different input paths. 10 out of 12 input hemilineages
            are shared. The cognitive backbone is a common developmental specification.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "4 & 19", label: "shared DN hubs" },
              { value: "83%", label: "hemilineage overlap" },
              { value: "15", label: "base hemilineages" },
              { value: "2-4", label: "per-capability additions" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              One growth program builds the cognitive backbone for all capabilities. Different capabilities
              are programmed by activating different input paths to the shared hubs.{" "}
              <span className="text-purple-400 font-medium">The growth program is modular: 15 base hemilineages
              plus 2-4 capability-specific plugins.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 15: Full Pipeline on Mouse Cortex */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 15 — Full Pipeline on Mouse Cortex</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We ran the complete synthetic neuroscience pipeline (Steps 1-5) on MICrONS mouse visual cortex.
            Orientation selectivity was compiled through directed evolution on 18,522 neurons across 9 cell-type
            modules. The same hub-and-spoke architecture emerged: mouse L5 layers serve as deep integrators
            (analogous to fly module 4), L2/3 layers serve as output relays (analogous to fly module 19).
            SST interneurons emerge as a cortex-specific inhibitory hub with no fly analogue.
            Mouse cortex is less modular — 95% of neurons needed vs the fly{`'`}s 12%. Evolution{`'`}s improvement
            was modest at +16.7% for orientation selectivity.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "5/6", label: "shared architectural features" },
              { value: "18,522", label: "mouse neurons" },
              { value: "5", label: "hub modules identified" },
              { value: "17", label: "frozen base edges" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          {/* Fly vs Mouse comparison table */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <motion.div
              className={`${cardBg} border ${border} rounded-xl p-5`}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <div className="text-sm font-medium text-purple-400 mb-4">Fly</div>
              <div className="space-y-3">
                {[
                  { label: "Neurons", value: "8,158" },
                  { label: "Modules", value: "19 hemilineages" },
                  { label: "Hubs", value: "2 hub modules (4, 19)" },
                  { label: "Base edges", value: "15 base platform edges" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between">
                    <span className={`text-sm ${textSubtle}`}>{row.label}</span>
                    <span className={`text-sm ${textMuted}`}>{row.value}</span>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div
              className={`${cardBg} border ${border} rounded-xl p-5`}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <div className="text-sm font-medium text-purple-400 mb-4">Mouse</div>
              <div className="space-y-3">
                {[
                  { label: "Neurons", value: "18,522" },
                  { label: "Modules", value: "9 cell-type layers" },
                  { label: "Hubs", value: "5 hub modules (V1_L2/3, V1_L5, HVA_L2/3, HVA_L5, SST)" },
                  { label: "Base edges", value: "17 base platform edges" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between">
                    <span className={`text-sm ${textSubtle}`}>{row.label}</span>
                    <span className={`text-sm ${textMuted}`}>{row.value}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The hub-and-spoke architecture with frozen base connections is conserved across 600 million years
              of evolution. The architecture is species-general. The implementation differs. Mouse adds SST
              inhibitory hubs as a cortex-specific innovation.{" "}
              <span className="text-purple-400 font-medium">One species is a demo. Two species is a method.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 16: Attention */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 16 — Attention (Compiled Weakly)</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We attempted to compile attention -- selective enhancement of one stimulus over another.
            It compiled weakly. 3 mutations produced laterality of 0.32 in final evaluation (peak 0.41 during evolution) with only 17% backbone overlap.
            Attention uses different circuits from working memory and conflict resolution.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "3", label: "mutations" },
              { value: "0.32", label: "final laterality (peak 0.41)" },
              { value: "17%", label: "backbone overlap" },
              { value: "weak", label: "compilation strength" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className={`text-2xl font-light ${stat.value === "weak" ? "text-yellow-400" : "text-purple-400"} mb-1`}>{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Attention is the first capability that compiled weakly. The 17% backbone overlap means
              it uses fundamentally different circuits from working memory and conflict resolution (which share 83%).{" "}
              <span className="text-purple-400 font-medium">This reveals two growth program families:
              state maintenance (WM + CR) and selective gating (attention). Not all cognition uses the same wiring.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 17: Distraction Control (Negative Result) */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 17 — Distraction Control (Negative Result)</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            We tested whether distraction resistance was a product of the 6 working memory mutations.
            The uncompiled brain shows 4.7x navigation bias through distraction — virtually identical
            to the compiled brain{"'"}s 4.9x. Distraction resistance is a property of the Izhikevich neuron
            dynamics on this connectome, not the compiled circuit. This finding was retracted after a
            control experiment.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "4.7x", label: "uncompiled brain" },
              { value: "4.9x", label: "compiled brain" },
              { value: "0.2x", label: "difference (not significant)" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Negative results matter. The control experiment disproved our initial claim.{" "}
              <span className="text-purple-400 font-medium">The working memory circuit improves navigation
              bias in the choice phase (3.8x compiled vs lower uncompiled), but distraction resistance
              specifically is not a product of evolution.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 18: Mouse Direction Selectivity */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 18 — Mouse Direction Selectivity</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Compiled direction selectivity on mouse V1 with 33 evolvable cell-type pairs. DSI=1.86.
            The evolution discovered a VIP-to-SST disinhibition circuit that matches experimental
            neuroscience -- VIP interneurons inhibit SST interneurons, releasing excitatory cells
            from inhibition in a direction-selective manner. Note: mouse required 5-20x perturbation scales vs fly{`'`}s 2x, suggesting denser cortical connectivity requires stronger perturbations.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "33", label: "evolvable cell-type pairs" },
              { value: "1.86", label: "direction selectivity index" },
              { value: "VIP-SST", label: "disinhibition validated" },
              { value: "mouse", label: "species" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-4 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-green-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The VIP-to-SST disinhibition circuit is one of the most well-characterized motifs in
              mouse cortex.{" "}
              <span className="text-purple-400 font-medium">Evolution discovered it independently from the
              connectome alone -- the same zero-label biological validation we achieved in the fly,
              now replicated in a mammalian brain.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 19: Bundle Growth Produces Functional Circuits */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 19 — Sequential Activity-Dependent Growth</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Sequential activity-dependent growth breaks through: growing connections one hemilineage at a time, with each wave biased toward currently-active neurons, produces nav score 851 at 1.45% density — beating the real FlyWire circuit (577) and random wiring (459). Growth ORDER is critical: random order produces 0. The developmental sequence is part of the growth program. The original pure bundle model scored 10.5, below random (12.0). Sequential growth resolves this gap. The score exceeding FlyWire (851 vs 577) may partly reflect Izhikevich dynamics favoring activity-dependent wiring, not necessarily biological superiority — this is one navigation test, not comprehensive validation.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "851", label: "sequential growth nav score" },
              { value: "1.45%", label: "physiological density" },
              { value: "577", label: "real brain (FlyWire)" },
              { value: "0", label: "random growth order" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Sequential activity-dependent growth demonstrates that growth order is a critical variable. Growing hemilineages in size order with activity-dependent bias produces functional circuits at physiological density.{" "}
              <span className="text-purple-400 font-medium">Step 6 is demonstrated — the developmental sequence is part of the specification.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 20: Gain Robustness */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 20 — Gain Robustness</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Both working memory and conflict resolution compile successfully at gains from 4x through 8x,
            with 7x producing the best results. The compiled circuits are not artifacts of a single gain
            setting -- they are robust to changes in synaptic amplification.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "4x-8x", label: "gain range" },
              { value: "7x", label: "optimal gain" },
              { value: "WM + CR", label: "both compile" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The 8x gain amplification was a concern in our limitations. Gain robustness addresses
              this directly.{" "}
              <span className="text-purple-400 font-medium">The circuit designs hold across a 2x range of
              synaptic gain, ruling out gain-specific artifacts. The architecture, not the gain, determines function.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 21: Growth Program Families */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 21 — Growth Program Families</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Two distinct growth program families emerged. State maintenance (working memory + conflict
            resolution) shares 83% of the backbone -- 15 base hemilineages plus 2-4 plugins per capability.
            Selective gating (attention) has only 17% overlap and uses different circuits entirely.
            Not all cognition runs on the same hardware.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <motion.div
              className={`${cardBg} border border-purple-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="text-sm font-medium text-purple-400 mb-3">State Maintenance</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Members</span>
                  <span className={`text-sm ${textMuted}`}>Working Memory + Conflict Resolution</span>
                </div>
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Backbone overlap</span>
                  <span className="text-sm text-purple-400">83%</span>
                </div>
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Architecture</span>
                  <span className={`text-sm ${textMuted}`}>15 base + 2-4 plugins</span>
                </div>
              </div>
            </motion.div>

            <motion.div
              className={`${cardBg} border border-yellow-500/30 rounded-xl p-5`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <div className="text-sm font-medium text-yellow-400 mb-3">Selective Gating</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Members</span>
                  <span className={`text-sm ${textMuted}`}>Attention</span>
                </div>
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Backbone overlap</span>
                  <span className="text-sm text-yellow-400">17%</span>
                </div>
                <div className="flex justify-between">
                  <span className={`text-sm ${textSubtle}`}>Architecture</span>
                  <span className={`text-sm ${textMuted}`}>Separate circuitry</span>
                </div>
              </div>
            </motion.div>
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              The brain has at least two distinct families of growth programs for cognitive capabilities.{" "}
              <span className="text-purple-400 font-medium">State maintenance capabilities share circuitry
              and can be built from a common developmental base. Selective gating capabilities use different
              circuits entirely -- the growth programs are genuinely different, not variations on a theme.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 22: Architecture Catalog */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 22 — Architecture Catalog: 26 Architectures Tested</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            26 neural circuit architectures generated from developmental specs and tested across 5 behavioral tasks: navigation, escape, turning, conflict resolution, and working memory. Each architecture was generated from its growth program specification (cell types, proportions, connection rules, growth order) using the sequential activity-dependent growth model — the same pipeline validated on the FlyWire connectome (Result 19). This is a different experiment from Results 1-21, which analyzed the biological FlyWire connectome directly. Here, we generate new connectomes from scratch and test whether different architectural designs produce different behavioral capabilities.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "26", label: "architectures tested" },
              { value: "5", label: "behavioral tasks" },
              { value: "509", label: "cellular automaton (top)" },
              { value: "351", label: "spiking state machine" },
              { value: "285", label: "winner-take-all" },
              { value: "#1→#15", label: "flat distributed w/ depression" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Architecture selection matters — different architectures are optimal for different task classes.{" "}
              <span className="text-purple-400 font-medium">The ranking inverts when synaptic depression is added: flat distributed drops from #1 to #15, scoring 0 on working memory.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 23: Hub Architecture Is Not Optimal */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 23 — Hub Architecture Is Not Optimal</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Surgically modified the FlyWire connectome&apos;s hub-and-spoke architecture to test whether it&apos;s necessary. Note: this is a separate experiment from Results 1-21 (which validated hub-and-spoke as conserved across species) and Result 22 (which generated architectures from specs). Here we ask: is the biological hub-and-spoke optimal for designed circuits, or just what evolution landed on? Finding: the biological hub-and-spoke is so tightly gated that evolution at small perturbation scales cannot break through — it&apos;s optimized for behavioral control, not evolvability. Alternative architectures evolve more easily, which is why the architecture catalog (Result 22) outperforms the biological reference on several tasks.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "0", label: "biological baseline (hubs 4,19)" },
              { value: "112", label: "flat (no hubs)" },
              { value: "276", label: "swapped hubs (12,37)" },
              { value: "257", label: "more hubs (6 instead of 2)" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Biological baseline stuck at 0 navigation fitness with 0 accepted mutations.{" "}
              <span className="text-purple-400 font-medium">Architecture IS a design variable.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 24: Synaptic Depression Changes Everything */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 24 — Synaptic Depression Changes Everything</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Without synaptic depression, <span className={text}>flat distributed dominates all tasks</span> through brute-force reverberation. With biologically calibrated depression (U=0.2, tau=800ms from Markram et al. 1998), the ranking inverts completely.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "0", label: "flat distributed WM (w/ depression)" },
              { value: "288", label: "cellular automaton WM" },
              { value: "#1", label: "WTA at fast recovery (tau=200ms)" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Flat distributed scores 0 on working memory — broad connectivity spreads activity everywhere and depression eliminates it. Cellular automaton scores 288 — tight local loops (3-6 neurons) sustain activity even with depression.{" "}
              <span className="text-purple-400 font-medium">The depression parameter determines which architectures work for which tasks.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 25: Composites Work */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 25 — Composites Work</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Generated a composite circuit: <span className={text}>cellular automaton region</span> (persistence) + <span className={text}>winner-take-all region</span> (competition) with interface connections. The composite matches or slightly exceeds each component on its designed task without degrading the other.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "98-106", label: "composite navigation" },
              { value: "10-13", label: "composite conflict resolution" },
              { value: "288-296", label: "composite working memory" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              <span className="text-purple-400 font-medium">Composite architectures are viable.</span> CA alone: nav=100, WM=288. WTA alone: CR=11.7. The composite preserves each component&apos;s strength.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 26: Minimum Viable Circuit Size */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 26 — Minimum Viable Circuit Size</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Cellular automaton at <span className={text}>1,000 neurons</span>: nav=0.67, WM=1.0 — dead. At <span className={text}>3,000 neurons</span>: nav=100, WM=288 — fully functional. The minimum viable circuit is approximately 3,000 neurons.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "1,000", label: "neurons (dead)" },
              { value: "0.67", label: "nav at 1K" },
              { value: "3,000", label: "neurons (functional)" },
              { value: "288", label: "WM at 3K" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Below 3,000 neurons, the circuit cannot generate enough recurrent activity to produce meaningful behavior.{" "}
              <span className="text-purple-400 font-medium">This sets the target for wet lab organoid size.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 27: Reservoir Shows Real Adaptation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 27 — Reservoir Shows Real Adaptation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Tested <span className={text}>habituation</span> (decreased response to repeated stimulus) and <span className={text}>novelty detection</span> (increased response to new stimulus) across 5 architectures. Reservoir and reward-modulated architectures show genuine selective adaptation.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {[
              { value: "5→0", label: "reservoir sugar habituation" },
              { value: "5→17", label: "reservoir lc4 novelty (3.4x)" },
              { value: "18→12", label: "reward-mod sugar habituation" },
              { value: "4→24", label: "reward-mod lc4 novelty (6x)" },
              { value: "✗", label: "cellular automaton (non-selective)" },
              { value: "5th", label: "computational dimension" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Cellular automaton habituates but shows no novelty — depression kills everything non-selectively.{" "}
              <span className="text-purple-400 font-medium">The fifth computational dimension (adaptation) is real.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 28: Growth Stimulation Protocol Doesn't Matter */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 28 — Growth Stimulation Protocol Doesn&apos;t Matter</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Grew cellular automaton and winner-take-all with <span className={text}>structured navigation-pattern stimulation</span> vs <span className={text}>random spontaneous activity</span> during development. Both produced identical evolved fitness.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "100", label: "CA nav (structured)" },
              { value: "100", label: "CA nav (random)" },
              { value: "64", label: "WTA nav (structured)" },
              { value: "65", label: "WTA nav (random)" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Architecture topology determines function regardless of the growth stimulation protocol.{" "}
              <span className="text-purple-400 font-medium">For grid and competitive architectures, the developmental environment doesn&apos;t shape the final circuit — the architecture spec alone is sufficient.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 29: Proper Rhythm Validation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 29 — Proper Rhythm Validation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Rewrote the rhythm fitness function to measure <span className={text}>true alternation</span> — consecutive time bins must alternate between high and low activity. Tested ring/CPG, oscillatory, cellular automaton, spiking state machine, and winner-take-all.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-8">
            {[
              { value: "5.44", label: "cellular automaton" },
              { value: "0.41", label: "ring/CPG" },
              { value: "0", label: "oscillatory" },
              { value: "—", label: "spiking state machine" },
              { value: "—", label: "winner-take-all" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Cellular automaton scored highest — grid local loops produce natural reverberation cycles. Ring/CPG scored weak but nonzero from reciprocal inhibition. Oscillatory scored 0 — needs Izhikevich-specific dynamics to produce real oscillations at this scale with LIF-equivalent neurons.{" "}
              <span className="text-purple-400 font-medium">Rhythm is the weakest computational dimension but is present in architectures with strong local recurrence.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 30: Simultaneous Multi-Behavior Compilation */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 30 — Simultaneous Multi-Behavior Compilation</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Tested whether circuits can <span className={text}>navigate, resolve conflicts, AND maintain working memory simultaneously</span> on the same circuit. Fitness is the geometric mean of normalized nav + conflict + arousal.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "84.68", label: "CA combined fitness" },
              { value: "73.69", label: "WTA combined fitness" },
              { value: "98-106", label: "composite navigation" },
              { value: "288-296", label: "composite working memory" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Both architectures function as integrated circuits — they don&apos;t need separate modes for separate behaviors. No degradation from simultaneous operation.{" "}
              <span className="text-purple-400 font-medium">Cellular automaton and winner-take-all can compile multiple behaviors at once.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 31: Self-Prediction */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 31 — Self-Prediction: A Circuit That Models Itself</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Fed each circuit its own DN output from the previous timestep as additional sensory input. Measured correlation between <span className={text}>predicted (output at t-1)</span> and <span className={text}>actual (output at t)</span> activity.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-1 gap-4 mb-8">
            {[
              { value: "85%", label: "reservoir self-prediction accuracy" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Reservoir computing achieved 85% self-prediction accuracy — echo state networks are designed for temporal prediction and they deliver.{" "}
              <span className="text-purple-400 font-medium">Self-prediction is a compilable behavior: the circuit learns to model its own dynamics through evolution.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 32: Recursive Self-Monitoring (3-Tier) */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 32 — Recursive Self-Monitoring (3-Tier)</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Built <span className={text}>3-tier composite circuits</span>: Tier 1 (cellular automaton) navigates. Tier 2 (reservoir) predicts Tier 1&apos;s output. Tier 3 (reservoir) predicts Tier 2&apos;s output. Tested across 10 seeds with 200 generations.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { value: "23.6%", label: "Tier 2 mean accuracy" },
              { value: "8/10", label: "Tier 2 seeds > 2%" },
              { value: "12.3%", label: "Tier 3 mean accuracy" },
              { value: "40%", label: "Tier 3 peak (seed 4)" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className={`${cardBg} border ${border} rounded-xl p-5 text-center`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="text-2xl font-light text-purple-400 mb-1">{stat.value}</div>
                <div className={`text-xs ${textSubtle} uppercase`}>{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="rounded-xl p-6"
            style={{ background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(139, 92, 246, 0.08))" }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              A circuit that models its own self-model. Recursive self-monitoring from a growth program. Three spatial regions, three cell type populations, defined interface connections. Growable.{" "}
              <span className="text-purple-400 font-medium">The signal is consistent across seeds — this is not noise.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Result 33: Composite Scaling — 10 Regions, 28K Neurons */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Result 33 — Composites Scale to 10 Regions</h2>
          <p className={`text-xl sm:text-2xl leading-relaxed ${textMuted} mb-12 max-w-3xl`}>
            Generated composite circuits with 2, 4, 6, 8, and 10 architectural regions. Each region is a different architecture
            (cellular automaton, winner-take-all, reservoir, spiking state machine, etc.) connected by interface neurons.
            <span className={text}> Navigation score holds at 97-99 regardless of composite size.</span> No degradation from 6K to 28K neurons.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
            {[
              { regions: "2", neurons: "5,996", score: "98" },
              { regions: "4", neurons: "11,328", score: "98" },
              { regions: "6", neurons: "16,770", score: "97" },
              { regions: "8", neurons: "22,101", score: "98" },
              { regions: "10", neurons: "28,091", score: "99" },
            ].map((item) => (
              <div key={item.regions} className={`${cardBg} rounded-xl p-4 text-center border ${border}`}>
                <p className="text-2xl font-light text-purple-400">{item.regions}</p>
                <p className={`text-xs ${textSubtle} mt-1`}>regions</p>
                <p className={`text-lg font-medium mt-2`}>{item.neurons}</p>
                <p className={`text-xs ${textSubtle}`}>neurons</p>
                <p className={`text-lg font-medium mt-2 text-green-400`}>{item.score}</p>
                <p className={`text-xs ${textSubtle}`}>nav score</p>
              </div>
            ))}
          </div>
          <motion.div
            className={`${cardBg} rounded-xl p-6 border ${border}`}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <p className={`text-lg leading-relaxed ${textMuted}`}>
              Grow time scales linearly (11s for 28K neurons). Evolve time: 105s for 10 regions. The 8-region composite
              has a nonzero baseline (89) — the merged circuit navigates without any evolution. The platform can generate
              composites with 10+ architectural regions, each specialized for a different computational dimension, integrated
              through interface connections, at a scale compatible with current organoid technology (28K neurons vs 1-3M cells
              in typical organoids).{" "}
              <span className="text-purple-400 font-medium">Architecture complexity has no ceiling at this scale.</span>
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* 6. Methods */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-3xl mx-auto px-4 sm:px-8 md:ml-8 lg:ml-16">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-8">Methods</h2>

          <div className="space-y-4">
            {[
              { label: "Connectome", value: "FlyWire FAFB v783" },
              { label: "Neurons", value: "139,255" },
              { label: "Synapses", value: "15,091,983 (thresholded, 24% of full dataset)" },
              { label: "Model", value: "LIF + Izhikevich (PyTorch), 0.1ms timestep, 8x gain amplification" },
              { label: "Modules", value: "50 modules from FlyWire cell type annotations" },
              { label: "Edge sweep", value: "2,450 inter-module edges per behavior, deterministic sweep, 2x amplify + 0.5x attenuate, classify by fitness delta" },
              { label: "Fitness", value: "Spike-based DN neuron group activity (300\u20131000 steps)" },
              { label: "Compute", value: "5 parallel EC2 instances, 10\u201322 hours per complete sweep" },
            ].map((method, i) => (
              <motion.div
                key={method.label}
                className={`flex flex-col sm:flex-row sm:gap-4 py-3 border-b ${border}`}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
              >
                <span className={`text-sm font-medium min-w-[160px] ${text}`}>{method.label}</span>
                <span className={`text-sm ${textMuted}`}>{method.value}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* 6. Limitations */}
      <motion.section
        className="py-16 md:py-24"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-8">
          <h2 className="text-sm uppercase tracking-widest text-purple-500 mb-4">Limitations &amp; Caveats</h2>
          <p className={`text-lg leading-relaxed ${textSubtle} mb-12`}>
            What we know we don&apos;t know.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            {[
              {
                title: "One Fly Brain, One Mouse Region",
                desc: "All fly results from a single female Drosophila (FlyWire FAFB v783). Mouse results from one cubic millimeter of V1 (MICrONS). Mitigation: 5/6 architectural features conserved cross-species. But individual variation (~30% of cell types) could change specific evolvable edges.",
              },
              {
                title: "Neuron Model Simplification",
                desc: "We use LIF for speed-class behaviors (navigation, escape, turning) and Izhikevich for persistence/competition-class behaviors (working memory, conflict resolution). Note: earlier results (1-21) used the terms 'reactive' and 'cognitive' — the current framework classifies behaviors by computational requirement (speed, persistence, competition, rhythm, gating, adaptation) rather than a binary split. Both neuron models omit dendritic computation, neuromodulation, gap junctions, and neuropeptides. Mitigation: edge 19\u20134 appeared in both models (model-independent). CX neuron type assignment as intrinsically bursting is assumed, not experimentally validated.",
              },
              {
                title: "Missing Connections",
                desc: "Our connectome uses a synapse count threshold \u2014 only 24% of total FlyWire connections. The missing 76% are weak connections (1\u20135 synapses) that may be functionally important for fine-grained behavior.",
              },
              {
                title: "No Gap Junctions",
                desc: "FlyWire captures chemical synapses only. The fly brain has extensive electrical synapses (~20\u201330% of connectivity) not represented in our model.",
              },
              {
                title: "Gain Amplification (Addressed)",
                desc: "We use 8x gain for signal propagation. Both working memory and conflict resolution compile at every gain from 4x through 8x with the same key edges. 7x actually produced the best results. The gain choice is not special, but it does affect absolute fitness values.",
              },
              {
                title: "Edge Classification Is Scale-Dependent",
                desc: "Edges classified at 2x/0.5x perturbation. A control experiment showed only 44% of edges match classification at 1.5x, and 22% at 5x. The qualitative pattern (turning more frozen than escape) holds across scales, but specific percentages are artifacts of the 2x/0.5x choice.",
              },
              {
                title: "Growth Program Gap (Addressed)",
                desc: "The original pure bundle growth model scored below random (10.5 vs 12.0). Sequential activity-dependent growth resolves this: growing connections one hemilineage at a time, biased by activity, produces functional circuits at physiological density (nav 851 at 1.45%). Growth order (not just cell type identity) is part of the specification. This is demonstrated on one navigation test — comprehensive validation across behaviors remains future work.",
              },
              {
                title: "Cognitive Claims Are Modest",
                desc: "Working memory is the simplest form: maintenance across a gap. Conflict resolution is attractor competition. Attention compiled weakly (laterality 0.32). Distraction resistance was tested and disproven (negative result). Real cognition is vastly more complex.",
              },
            ].map((card, i) => (
              <motion.div
                key={card.title}
                className={`${cardBg} border ${border} rounded-xl p-5`}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.07 }}
              >
                <div className={`text-sm font-medium ${text} mb-2`}>{card.title}</div>
                <p className={`text-sm ${textMuted} leading-relaxed`}>{card.desc}</p>
              </motion.div>
            ))}
          </div>

          <motion.p
            className={`text-sm ${textSubtle} leading-relaxed max-w-3xl`}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.6 }}
          >
            A note on model dependence: a complete deterministic sweep of all 2,450 inter-module edges
            reveals that frozen/evolvable classification is strongly behavior-dependent. Turning freezes
            91% of edges while escape makes 89% evolvable. The three-layer architecture exists for every
            behavior but with different proportions — suggesting it reflects how each behavior uses
            the connectome&apos;s topology, not a fixed property of the wiring. A more realistic neural model
            would sharpen the exact percentages and scale factors, but the architectural discovery is
            about which connections matter for which behaviors — and that&apos;s determined by the wiring
            diagram, not by how individual neurons spike. As connectome data and neural models improve,
            the same methodology will produce sharper results on the same architecture.
          </motion.p>
        </div>
      </motion.section>

      {/* Open Questions moved to top of page */}

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
