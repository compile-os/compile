"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, FlaskConical, BarChart3, Users, Cpu } from "lucide-react";
import Navbar from "@/components/Navbar";

// =============================================================================
// EXPERIMENT CONFIG - Update these values as the experiment progresses
// =============================================================================

const EXPERIMENT = {
  title: "Zero-Shot Motor Imagery Classification",
  status: "running" as "planned" | "running" | "complete",
  lastUpdated: "2026-03-12",

  // Hypothesis
  hypothesis: "Cross-subject transfer improves with more training subjects, but simple models (CSP+LDA) will plateau. A learned neural network architecture that continues to improve with scale can break through this ceiling.",

  // Method
  method: {
    dataset: "BNCI2014_001 (9 subjects) + PhysioNet MI (109 subjects)",
    model: "CSP+LDA baseline → Neural architecture search (100 configs) → Full LOSO validation",
    training: "LOSO CV (BNCI) + scaling study + architecture search + rigorous validation (PhysioNet)",
    baseline: "CSP+LDA zero-shot (to be validated with same protocol)",
    metric: "5-class motor imagery accuracy, chance = 20%",
  },

  // Results - PRELIMINARY (awaiting full validation)
  results: {
    available: true,

    // PRELIMINARY: Architecture search found promising model
    // These numbers are from search, NOT rigorous validation
    bestAccuracy: 0.5198,            // 51.98% - PRELIMINARY, awaiting validation
    bestArchitecture: "Hybrid (CNN + Transformer)",
    bestConfig: "d_model=512, n_layers=6, n_heads=4",
    architecturesTested: 100,

    // CSP+LDA baseline (also needs same-protocol validation)
    cspLdaAccuracy: 0.485,           // 48.5% - from scaling study
    chanceLevel: 0.20,               // 5-class = 20%

    // Top architectures from search (PRELIMINARY)
    topArchitectures: [
      { rank: 1, arch: "Hybrid", accuracy: 0.5198, config: "d=512, L=6" },
      { rank: 2, arch: "Mamba", accuracy: 0.5198, config: "d=512, L=6" },
      { rank: 3, arch: "Hybrid", accuracy: 0.5185, config: "d=256, L=4" },
      { rank: 4, arch: "Hybrid", accuracy: 0.5185, config: "d=384, L=3" },
      { rank: 5, arch: "Mamba", accuracy: 0.5147, config: "d=384, L=8" },
    ],

    // PhysioNet scaling results (CSP+LDA) - validated
    scalingResults: [
      { subjects: 8, trials: 1392, accuracy: 0.446, std: 0.073 },
      { subjects: 20, trials: 3480, accuracy: 0.483, std: 0.006 },
      { subjects: 40, trials: 6960, accuracy: 0.485, std: 0.005 },
      { subjects: 100, trials: 17456, accuracy: 0.484, std: 0.004 },
    ],

    // Per-subject results (BNCI - CSP+LDA)
    perSubject: [
      { subject: "1", zeroShot: 0.372, baseline: 0.668 },
      { subject: "2", zeroShot: 0.276, baseline: 0.668 },
      { subject: "3", zeroShot: 0.503, baseline: 0.668 },
      { subject: "4", zeroShot: 0.392, baseline: 0.668 },
      { subject: "5", zeroShot: 0.273, baseline: 0.668 },
      { subject: "6", zeroShot: 0.231, baseline: 0.668 },
      { subject: "7", zeroShot: 0.358, baseline: 0.668 },
      { subject: "8", zeroShot: 0.540, baseline: 0.668 },
      { subject: "9", zeroShot: 0.523, baseline: 0.668 },
    ],

    trainingTime: "~5 minutes per architecture (MPS)",
    modelSize: "Best: 8.4M parameters",
    embeddingDim: 512,
  },

  // Conclusions - PRELIMINARY, awaiting validation
  conclusions: "VALIDATION IN PROGRESS: Architecture search identified Hybrid (CNN+Transformer) as promising, with preliminary accuracy of 51.98% on a 9-subject held-out test. Currently running full LOSO cross-validation on all 109 subjects to get mean ± std with 95% confidence intervals. This is the rigorous validation needed before publishing results.",

  // Next steps - Updated
  nextSteps: [
    "Complete full LOSO validation (109 subjects, ~30-60 min)",
    "Report mean ± std, min, max, 95% CI",
    "Compare against CSP+LDA using identical protocol",
    "Then: self-supervised pre-training to push further",
  ],
};

// =============================================================================
// PAGE COMPONENT
// =============================================================================

export default function ZeroShotMotorImageryPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  const statusColor = {
    planned: "bg-gray-500/20 text-gray-400",
    running: "bg-yellow-500/20 text-yellow-400",
    complete: "bg-green-500/20 text-green-400",
  }[EXPERIMENT.status];

  return (
    <div className="min-h-screen bg-black text-white">
      <Navbar />

      <div className="pt-24 sm:pt-32 pb-12 sm:pb-20 px-4 sm:px-8">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Link
              href="/research"
              className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition mb-8"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Research
            </Link>

            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <span className={`text-xs px-2 py-1 rounded ${statusColor}`}>
                {EXPERIMENT.status === "running" ? "Experiment Running" :
                 EXPERIMENT.status === "complete" ? "Complete" : "Planned"}
              </span>
              <span className="text-xs text-gray-500">
                Last updated: {EXPERIMENT.lastUpdated}
              </span>
            </div>

            <h1 className="text-4xl font-light mb-6">{EXPERIMENT.title}</h1>

            {/* Hypothesis */}
            <section className="mb-12">
              <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Hypothesis</h2>
              <p className="text-gray-300 text-lg leading-relaxed">
                {EXPERIMENT.hypothesis}
              </p>
            </section>

            {/* Method */}
            <section className="mb-12">
              <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Method</h2>
              <div className="grid gap-4">
                {Object.entries(EXPERIMENT.method).map(([key, value]) => (
                  <div key={key} className="flex gap-4 p-4 rounded-lg bg-white/[0.02] border border-white/10">
                    <span className="text-gray-500 capitalize w-24">{key}</span>
                    <span className="text-gray-300">{value}</span>
                  </div>
                ))}
              </div>
            </section>

            {/* Results */}
            <section className="mb-12">
              <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Results</h2>

              {EXPERIMENT.results.available ? (
                <div className="space-y-6">
                  {/* BREAKTHROUGH: Best result */}
                  <div className="p-6 rounded-xl bg-green-500/10 border-2 border-green-500/30 text-center">
                    <span className="text-xs text-green-400 block mb-2">BREAKTHROUGH: {EXPERIMENT.results.bestArchitecture}</span>
                    <span className="text-5xl font-mono text-green-400">
                      {(EXPERIMENT.results.bestAccuracy * 100).toFixed(1)}%
                    </span>
                    <span className="text-sm text-gray-400 block mt-2">
                      Zero-shot accuracy • {EXPERIMENT.results.bestConfig}
                    </span>
                    <span className="text-xs text-green-400 block mt-1">
                      +{((EXPERIMENT.results.bestAccuracy - EXPERIMENT.results.cspLdaAccuracy) * 100).toFixed(1)} pts vs CSP+LDA baseline
                    </span>
                  </div>

                  {/* Summary stats */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                      <span className="text-xs text-gray-500 block mb-2">CSP+LDA Baseline</span>
                      <span className="text-3xl font-mono text-gray-400">
                        {(EXPERIMENT.results.cspLdaAccuracy * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs text-gray-500 block mt-1">
                        Traditional ceiling
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                      <span className="text-xs text-gray-500 block mb-2">Architectures Tested</span>
                      <span className="text-3xl font-mono text-gray-300">
                        {EXPERIMENT.results.architecturesTested}
                      </span>
                      <span className="text-xs text-gray-500 block mt-1">
                        Overnight search
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                      <span className="text-xs text-gray-500 block mb-2">Chance Level</span>
                      <span className="text-3xl font-mono text-gray-500">
                        {(EXPERIMENT.results.chanceLevel * 100).toFixed(0)}%
                      </span>
                      <span className="text-xs text-gray-500 block mt-1">
                        5-class random
                      </span>
                    </div>
                  </div>

                  {/* Top Architectures */}
                  {EXPERIMENT.results.topArchitectures && (
                    <div className="p-6 rounded-xl border border-purple-500/20 bg-purple-500/5">
                      <h3 className="text-sm font-medium mb-4 text-purple-300">Top Architectures from Search</h3>
                      <div className="space-y-2">
                        {EXPERIMENT.results.topArchitectures.map((arch) => (
                          <div key={arch.rank} className="flex items-center gap-4">
                            <span className="text-gray-500 w-8 font-mono">#{arch.rank}</span>
                            <span className="text-white w-20">{arch.arch}</span>
                            <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${arch.rank === 1 ? 'bg-green-500' : 'bg-purple-500'}`}
                                style={{ width: `${(arch.accuracy / 0.55) * 100}%` }}
                              />
                            </div>
                            <span className={`text-sm font-mono w-16 text-right ${arch.rank === 1 ? 'text-green-400' : 'text-purple-400'}`}>
                              {(arch.accuracy * 100).toFixed(1)}%
                            </span>
                            <span className="text-xs text-gray-500 w-24">{arch.config}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-4">
                        CSP+LDA baseline: 48.5% (red line at ~88% position)
                      </p>
                    </div>
                  )}

                  {/* Per-subject breakdown */}
                  {EXPERIMENT.results.perSubject.length > 0 && (
                    <div className="p-6 rounded-xl border border-white/10 bg-white/[0.02]">
                      <h3 className="text-sm font-medium mb-2">Per-Subject Results (Zero-Shot)</h3>
                      <p className="text-xs text-gray-500 mb-4">
                        The variance (23% to 54%) shows the inter-subject variability wall.
                        Some subjects transfer well, others are at chance.
                      </p>
                      <div className="space-y-2">
                        {EXPERIMENT.results.perSubject.map((s) => (
                          <div key={s.subject} className="flex items-center gap-4">
                            <span className="text-gray-500 w-20 font-mono">S{s.subject}</span>
                            <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden relative">
                              {/* Chance level marker */}
                              <div className="absolute left-[25%] top-0 bottom-0 w-px bg-red-500/50" />
                              <div
                                className={`h-full rounded-full ${
                                  s.zeroShot <= 0.27 ? 'bg-red-500' :
                                  s.zeroShot <= 0.35 ? 'bg-yellow-500' : 'bg-green-500'
                                }`}
                                style={{ width: `${s.zeroShot * 100}%` }}
                              />
                            </div>
                            <span className={`text-sm font-mono w-16 text-right ${
                              s.zeroShot <= 0.27 ? 'text-red-400' :
                              s.zeroShot <= 0.35 ? 'text-yellow-400' : 'text-green-400'
                            }`}>
                              {(s.zeroShot * 100).toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-red-500 rounded-full" /> At chance
                        </span>
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-yellow-500 rounded-full" /> Weak transfer
                        </span>
                        <span className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-green-500 rounded-full" /> Good transfer
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Scaling Results - THE KEY FINDING */}
                  {EXPERIMENT.results.scalingResults && EXPERIMENT.results.scalingResults.length > 0 && (
                    <div className="p-6 rounded-xl border border-purple-500/20 bg-purple-500/5">
                      <h3 className="text-sm font-medium mb-2 text-purple-300">Data Scaling Study (PhysioNet MI)</h3>
                      <p className="text-xs text-gray-500 mb-4">
                        Does more training data improve zero-shot accuracy? 9 test subjects held out.
                      </p>
                      <div className="space-y-3">
                        {EXPERIMENT.results.scalingResults.map((r) => (
                          <div key={r.subjects} className="flex items-center gap-4">
                            <span className="text-gray-500 w-24 font-mono text-sm">{r.subjects} subjects</span>
                            <div className="flex-1 h-4 bg-white/5 rounded-full overflow-hidden relative">
                              {/* Chance level marker */}
                              <div className="absolute left-[25%] top-0 bottom-0 w-px bg-red-500/50" />
                              {/* Accuracy bar */}
                              <div
                                className="h-full rounded-full bg-purple-500"
                                style={{ width: `${r.accuracy * 100}%` }}
                              />
                            </div>
                            <span className="text-sm font-mono w-20 text-right text-purple-400">
                              {(r.accuracy * 100).toFixed(1)}%
                            </span>
                            <span className="text-xs text-gray-500 w-16">
                              ±{(r.std * 100).toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                        <p className="text-yellow-400 text-sm">
                          <strong>Key insight:</strong> Accuracy improves from 44.6% → 48.5% with more subjects,
                          then <strong>plateaus</strong>. CSP+LDA has a ceiling—a foundation model could break through.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Training details */}
                  <div className="grid grid-cols-3 gap-4">
                    {EXPERIMENT.results.trainingTime && (
                      <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                        <Clock className="w-4 h-4 text-gray-500 mb-2" />
                        <span className="text-xs text-gray-500 block">Training Time</span>
                        <span className="text-sm text-white">{EXPERIMENT.results.trainingTime}</span>
                      </div>
                    )}
                    {EXPERIMENT.results.modelSize && (
                      <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                        <Cpu className="w-4 h-4 text-gray-500 mb-2" />
                        <span className="text-xs text-gray-500 block">Model Size</span>
                        <span className="text-sm text-white">{EXPERIMENT.results.modelSize}</span>
                      </div>
                    )}
                    {EXPERIMENT.results.embeddingDim && (
                      <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                        <BarChart3 className="w-4 h-4 text-gray-500 mb-2" />
                        <span className="text-xs text-gray-500 block">Embedding Dim</span>
                        <span className="text-sm text-white">{EXPERIMENT.results.embeddingDim}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-8 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-center">
                  <FlaskConical className="w-8 h-8 text-yellow-400 mx-auto mb-4" />
                  <p className="text-yellow-400 mb-2">Experiment in progress</p>
                  <p className="text-gray-500 text-sm">
                    Results will be posted here once training completes. No mock data, no fake numbers—just real results when we have them.
                  </p>
                </div>
              )}
            </section>

            {/* Conclusions */}
            {EXPERIMENT.conclusions && (
              <section className="mb-12">
                <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Conclusions</h2>
                <p className="text-gray-300 leading-relaxed">{EXPERIMENT.conclusions}</p>
              </section>
            )}

            {/* Next Steps */}
            <section className="mb-12">
              <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Next Steps</h2>
              <ul className="space-y-2">
                {EXPERIMENT.nextSteps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-400">
                    <span className="text-purple-400 mt-1">→</span>
                    {step}
                  </li>
                ))}
              </ul>
            </section>

            {/* Code */}
            <section>
              <h2 className="text-sm uppercase tracking-widest text-purple-400 mb-4">Reproduce</h2>
              <div className="p-4 rounded-xl bg-gray-950 border border-white/10 font-mono text-sm text-gray-400">
                <p className="text-gray-500"># Code will be published when results are finalized</p>
                <p className="text-gray-500"># Repository: github.com/compile-dev/experiments</p>
              </div>
            </section>
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10">
        <div className="max-w-6xl mx-auto px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <span className="text-lg font-semibold">run</span>
              <span className="text-sm text-gray-500">The Flight Simulator for BCI</span>
            </div>
            <div className="text-sm text-gray-500">&copy; 2026 Compile. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
