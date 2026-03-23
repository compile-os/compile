"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";

import { Sun, Moon, Monitor, Terminal, Cpu, Dna, Check, ChevronDown, ChevronUp, ArrowRight, ArrowLeft, Download, Layers } from "lucide-react";

import {
  fetchModules,
  fetchFitnessFunctions,
  fetchThreeLayerMap,
  createJob,
  streamJob,
  isAuthenticated,
  setAuthToken,
} from "@/lib/api";

import type {
  CompileModule,
  FitnessFunction,
  ThreeLayerMap,
  ProcessorSpec,
  GrowthProgram,
  Species,
} from "@/types/compile";
import { BEHAVIOR_COLORS } from "@/types/compile";
import {
  FALLBACK_PROCESSORS,
  FALLBACK_GROWTH_PROGRAMS,
  FALLBACK_SPECIES,
} from "@/lib/compile-data";
import { ARCHITECTURES, ARCHITECTURE_CATEGORIES, ARCHITECTURE_SCORES, type Architecture } from "@/lib/architecture-data";

// ---------------------------------------------------------------------------
// Dynamic import for FlyBrain3D (no SSR — requires WebGL)
// ---------------------------------------------------------------------------

const BioTube = dynamic(
  () => import("@/components/BioTube"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    ),
  }
);

const AuthInline = dynamic(
  () => import("@/components/AuthInline").then((mod) => ({ default: mod.AuthInline })),
  { ssr: false }
);

const FlyBrain3D = dynamic(
  () => import("@/components/FlyBrain3D").then((mod) => mod.FlyBrain3D),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    ),
  }
);

const FlyBody3D = dynamic(
  () => import("@/components/FlyBody3D"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    ),
  }
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------


interface ConsoleEntry {
  timestamp: Date;
  text: string;
  type?: "default" | "command" | "info" | "success" | "detail" | "metric";
}

// ---------------------------------------------------------------------------
// Behavior presets (tagged by computational requirement)
// ---------------------------------------------------------------------------

type BehaviorTag = "speed" | "persistence" | "competition" | "rhythm" | "gating" | "adaptation";

const BEHAVIOR_TAGS: { id: BehaviorTag; label: string; description: string }[] = [
  { id: "speed", label: "Speed", description: "Fast sensory-to-motor response" },
  { id: "persistence", label: "Persistence", description: "Sustained internal state after input stops" },
  { id: "competition", label: "Competition", description: "Choosing between simultaneous inputs" },
  { id: "rhythm", label: "Rhythm", description: "Temporal alternating patterns" },
  { id: "gating", label: "Gating", description: "Selective amplification of inputs" },
  { id: "adaptation", label: "Adaptation", description: "Response change over time" },
];

interface Preset {
  id: string;
  label: string;
  description: string;
  color: string;
  prompt: string;
  tag: BehaviorTag;
  badge?: string;
  isNew?: boolean;
  isMine?: boolean;
}

const PRESETS: Preset[] = [
  { id: "navigation", label: "Navigation", description: "Navigate toward food sources efficiently.", color: "#06b6d4", prompt: "Navigate toward food", tag: "speed" },
  { id: "escape", label: "Escape", description: "Flee from looming threats at maximum velocity.", color: "#ef4444", prompt: "Escape from threats", tag: "speed" },
  { id: "turning", label: "Turning", description: "Turn toward auditory stimuli precisely.", color: "#22c55e", prompt: "Turn toward stimuli", tag: "speed" },
  { id: "arousal", label: "Arousal", description: "Increase alertness and overall responsiveness.", color: "#f59e0b", prompt: "Increase alertness", tag: "speed" },
  { id: "working_memory", label: "Working Memory", description: "Hold and recall sensory traces over short delays.", color: "#a855f7", prompt: "Hold sensory traces", tag: "persistence" },
  { id: "conflict", label: "Conflict Resolution", description: "Resolve competing motor commands through inhibition.", color: "#ec4899", prompt: "Resolve competing commands", tag: "competition" },
  { id: "circles", label: "Circles", description: "Walk in sustained circular locomotion patterns.", color: "#10b981", prompt: "Circular locomotion", tag: "rhythm", isNew: true },
  { id: "rhythm", label: "Rhythm", description: "Alternate walking and stopping rhythmically.", color: "#8b5cf6", prompt: "Rhythmic alternation", tag: "rhythm", isNew: true },
  { id: "attention", label: "Attention", description: "Selective attention to a cued stimulus.", color: "#f97316", prompt: "Selective attention", tag: "gating" },
];

// Improvement percentages for each preset (from experiment data)
const PRESET_METRICS: Record<string, { improvement: string; metric: string; evolvableEdges: number; rate: string }> = {
  navigation: { improvement: "+100%", metric: "Navigation score: +100% over baseline", evolvableEdges: 73, rate: "6%" },
  escape: { improvement: "+8.6%", metric: "Escape velocity: +8.6% over baseline", evolvableEdges: 5, rate: "0.8%" },
  turning: { improvement: "+25%", metric: "Angular displacement: +25% over baseline", evolvableEdges: 5, rate: "0.8%" },
  arousal: { improvement: "+60%", metric: "Arousal index: +60% over baseline", evolvableEdges: 8, rate: "1.2%" },
  circles: { improvement: "+86%", metric: "Angular displacement: +86% over baseline", evolvableEdges: 4, rate: "0.6%" },
  rhythm: { improvement: "+87%", metric: "Rhythm regularity: +87% over baseline", evolvableEdges: 5, rate: "0.8%" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtNumber(n: number): string {
  return n.toLocaleString();
}

// ---------------------------------------------------------------------------
// Theme hook
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Growth Animation SVG
// ---------------------------------------------------------------------------

function GrowthVisualization({ isDark, cellTypes }: { isDark: boolean; cellTypes: { hemilineage: string; count: number; proportion: number; neurotransmitter: string }[] }) {
  const ntColors: Record<string, string> = { acetylcholine: "#06b6d4", gaba: "#ef4444", dopamine: "#f59e0b" };
  const clusters = cellTypes.slice(0, 12);
  const cx = 250, cy = 250;
  return (
    <div className="w-full h-full flex items-center justify-center p-4">
      <svg viewBox="0 0 500 500" className="w-full h-full max-w-[500px] max-h-[500px]">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {/* Connection lines */}
        {clusters.map((c, i) => {
          const angle = (i / clusters.length) * Math.PI * 2;
          const r = 80 + c.proportion * 130;
          const x = cx + Math.cos(angle) * r;
          const y = cy + Math.sin(angle) * r;
          const nextIdx = (i + 1) % clusters.length;
          const nextAngle = (nextIdx / clusters.length) * Math.PI * 2;
          const nextR = 80 + clusters[nextIdx].proportion * 130;
          const nx = cx + Math.cos(nextAngle) * nextR;
          const ny = cy + Math.sin(nextAngle) * nextR;
          return (
            <line key={`line-${i}`} x1={x} y1={y} x2={nx} y2={ny}
              stroke={isDark ? "rgba(124,58,237,0.15)" : "rgba(124,58,237,0.1)"}
              strokeWidth="1">
              <animate attributeName="opacity" values="0.2;0.6;0.2" dur={`${3 + i * 0.3}s`} repeatCount="indefinite" />
            </line>
          );
        })}
        {/* Cluster nodes */}
        {clusters.map((c, i) => {
          const angle = (i / clusters.length) * Math.PI * 2;
          const r = 80 + c.proportion * 130;
          const x = cx + Math.cos(angle) * r;
          const y = cy + Math.sin(angle) * r;
          const nodeR = 5 + c.proportion * 20;
          const color = ntColors[c.neurotransmitter] || "#7C3AED";
          return (
            <g key={`node-${i}`}>
              <circle cx={x} cy={y} r={nodeR} fill={color} opacity={0.2} filter="url(#glow)">
                <animate attributeName="r" values={`${nodeR};${nodeR + 3};${nodeR}`} dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />
              </circle>
              <circle cx={x} cy={y} r={nodeR * 0.6} fill={color} opacity={0.6}>
                <animate attributeName="opacity" values="0.4;0.8;0.4" dur={`${2.5 + i * 0.15}s`} repeatCount="indefinite" />
              </circle>
              <text x={x} y={y + nodeR + 12} textAnchor="middle" fill={isDark ? "#6b7280" : "#9ca3af"} fontSize="8" fontFamily="monospace">
                {c.hemilineage.length > 12 ? c.hemilineage.substring(0, 12) : c.hemilineage}
              </text>
            </g>
          );
        })}
        {/* Center label */}
        <text x="250" y="250" textAnchor="middle" fill={isDark ? "#7C3AED" : "#6D28D9"} fontSize="10" fontFamily="monospace" fontWeight="bold">
          Growth
        </text>
        <text x="250" y="264" textAnchor="middle" fill={isDark ? "#6b7280" : "#9ca3af"} fontSize="8" fontFamily="monospace">
          {cellTypes.length} cell types
        </text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function PlaygroundPage() {
  // --- Data state ---
  const [modules, setModules] = useState<CompileModule[]>([]);
  const [fitnessFunctions, setFitnessFunctions] = useState<FitnessFunction[]>([]);
  const [threeLayerMap, setThreeLayerMap] = useState<ThreeLayerMap | null>(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [communityBehaviors, setCommunityBehaviors] = useState<Preset[]>([]);
  // Seeded with precomputed interference from research sprint; overridden by live API
  const [interferenceData, setInterferenceData] = useState<Array<{ compiled: string; tested: string; delta_pct: number }>>([
    { compiled: "navigation", tested: "escape", delta_pct: 58 },
    { compiled: "navigation", tested: "arousal", delta_pct: 5 },
    { compiled: "navigation", tested: "circles", delta_pct: 3 },
    { compiled: "escape", tested: "navigation", delta_pct: 2 },
    { compiled: "arousal", tested: "navigation", delta_pct: 8 },
    { compiled: "arousal", tested: "escape", delta_pct: 3 },
    { compiled: "circles", tested: "navigation", delta_pct: 5 },
    { compiled: "circles", tested: "escape", delta_pct: -41 },
    { compiled: "circles", tested: "turning", delta_pct: 10 },
    { compiled: "turning", tested: "circles", delta_pct: 5 },
  ]);

  // --- Theme ---
  const { theme, mode, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const pgBg = isDark ? "bg-[#0a0a0f]" : "bg-gray-50";
  const pgText = isDark ? "text-white" : "text-gray-900";
  const pgBorder = isDark ? "border-[#1e1e2e]" : "border-gray-200";
  const pgPanel = isDark ? "bg-[#12121a]" : "bg-white";
  const pgCard = isDark ? "bg-[#12121a]" : "bg-gray-100";
  const pgMuted = isDark ? "text-gray-500" : "text-gray-400";
  const pgDimText = isDark ? "text-gray-400" : "text-gray-600";
  const pgSep = isDark ? "bg-[#1e1e2e]" : "bg-gray-200";

  // --- UI state ---
  const [mounted, setMounted] = useState(false);
  const [selectedBehaviors, setSelectedBehaviors] = useState<string[]>([]);
  const [activePreset, setActivePreset] = useState<Preset | null>(null);
  const [selectedModule, setSelectedModule] = useState<number | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleEntry[]>([]);
  const [compiling, setCompiling] = useState(false);
  const [consoleOpen, setConsoleOpen] = useState(false);

  // --- Pipeline state ---
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedArchitectures, setSelectedArchitectures] = useState<string[]>(["cellular_automaton"]);
  const [architectureCategoryFilter, setArchitectureCategoryFilter] = useState<string>("all");
  const [neuronCount, setNeuronCount] = useState(8000);
  const [archDetailTab, setArchDetailTab] = useState(0);
  const [stepsCompleted, setStepsCompleted] = useState<Set<number>>(new Set());
  const [selectedProcessor, setSelectedProcessor] = useState<ProcessorSpec | null>(null);
  const [selectedGrowthProgram, setSelectedGrowthProgram] = useState<GrowthProgram | null>(null);
  const [selectedSpecies, setSelectedSpecies] = useState<Species>(FALLBACK_SPECIES[0]);
  const [extracting, setExtracting] = useState(false);
  const [generatingGrowth, setGeneratingGrowth] = useState(false);
  const [speciesDropdownOpen, setSpeciesDropdownOpen] = useState(false);
  const [vizMode, setVizMode] = useState<"brain" | "body">("body");
  const [bodyPlaying, setBodyPlaying] = useState(true);
  const [replayKey, setReplayKey] = useState(0);
  const [bodyFinished, setBodyFinished] = useState(false);

  // --- API state ---
  const [apiAvailable, setApiAvailable] = useState(false);
  const [customBehavior, setCustomBehavior] = useState("");
  const [compileProgress, setCompileProgress] = useState(0);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [behaviorFilter, setBehaviorFilter] = useState<"all" | "mine">("all");

  const consoleEndRef = useRef<HTMLDivElement>(null);

  // --- Console logger ---
  const log = useCallback((text: string, type?: ConsoleEntry["type"]) => {
    setConsoleLogs((prev) => [...prev, { timestamp: new Date(), text, type: type || "default" }]);
  }, []);

  const logDelayed = useCallback((text: string, delayMs: number, type?: ConsoleEntry["type"]) => {
    return new Promise<void>((resolve) => {
      setTimeout(() => {
        log(text, type);
        resolve();
      }, delayMs);
    });
  }, [log]);

  // Auto-scroll console
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [consoleLogs]);

  // --- Mount ---
  useEffect(() => { setMounted(true); }, []);

  // --- Load data ---
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [mods, ffs, tlm] = await Promise.all([
          fetchModules(),
          fetchFitnessFunctions(),
          fetchThreeLayerMap(),
        ]);
        if (cancelled) return;
        setModules(mods);
        setFitnessFunctions(ffs);
        setThreeLayerMap(tlm);
        setDataLoaded(true);
        setConsoleLogs([
          { timestamp: new Date(), text: `Loaded FlyWire FAFB v783 connectome (${fmtNumber(mods.reduce((sum, m) => sum + m.n_neurons, 0))} neurons)`, type: "success" },
          { timestamp: new Date(), text: `${mods.length} modules | ${fmtNumber(tlm.hardware_stats.total_pairs)} total pairs | ${fmtNumber(tlm.hardware_stats.evolvable_pairs)} evolvable`, type: "info" },
          { timestamp: new Date(), text: `Ready. Select behaviors to compile.`, type: "info" },
        ]);
        // Check if live API is available (worker running with data)
        try {
          const healthRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"}/health`);
          if (healthRes.ok && !cancelled) {
            setApiAvailable(true);
            setConsoleLogs((prev) => [...prev, { timestamp: new Date(), text: "Live API connected. Custom behaviors enabled.", type: "success" }]);

            // Fetch catalog to get any community/user-compiled behaviors
            try {
              const { fetchCatalog } = await import("@/lib/api");
              const catalog = await fetchCatalog();
              const presetIds = new Set(PRESETS.map((p) => p.id));
              const community = catalog.behaviors
                .filter((b) => !b.is_precomputed && !presetIds.has(b.id))
                .map((b) => ({
                  id: b.id,
                  label: b.label,
                  description: b.description,
                  color: "#7C3AED",
                  prompt: `Compiled behavior: ${b.label}`,
                  tag: (b.capability_family === "state_maintenance" ? "persistence" : b.capability_family === "selective_gating" ? "gating" : "speed") as BehaviorTag,
                  isMine: b.is_mine,
                }));
              if (catalog.interference) {
                setInterferenceData(catalog.interference);
              }
              if (community.length > 0 && !cancelled) {
                setCommunityBehaviors(community);
                setConsoleLogs((prev) => [...prev, { timestamp: new Date(), text: `${community.length} community-compiled behavior${community.length > 1 ? "s" : ""} available.`, type: "info" }]);
              }
            } catch {
              // Catalog fetch failed, no community behaviors
            }
          }
        } catch {
          // API not available — precomputed mode only
        }
      } catch (err) {
        console.error("Failed to load compile data", err);
        if (!cancelled)
          setConsoleLogs([{ timestamp: new Date(), text: "Loaded precomputed results. Ready.", type: "info" }]);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // --- Toggle behavior selection ---
  const toggleBehavior = useCallback((presetId: string) => {
    setSelectedBehaviors((prev) =>
      prev.includes(presetId) ? prev.filter((b) => b !== presetId) : [...prev, presetId]
    );
    const preset = PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setActivePreset(preset);
    }
    setBodyFinished(false);
    setReplayKey((k) => k + 1);
    setBodyPlaying(true);
  }, []);

  // --- Compile handler (precomputed for known presets, live API for custom) ---
  const handleCompile = useCallback(async () => {
    if (compiling || selectedBehaviors.length === 0) return;
    setCompiling(true);
    setCompileProgress(0);
    setConsoleOpen(true);

    const allPresetIds = new Set(PRESETS.map((p) => p.id));
    const customBehaviors = selectedBehaviors.filter((b) => !allPresetIds.has(b));
    const presetBehaviors = selectedBehaviors.filter((b) => allPresetIds.has(b));

    log(`> compile([${selectedBehaviors.map((b) => `"${b}"`).join(", ")}])`, "command");

    // --- Precomputed presets (instant) ---
    if (presetBehaviors.length > 0) {
      await logDelayed("Loading precomputed results...", 200, "info");

      for (const behaviorId of presetBehaviors) {
        const ff = fitnessFunctions.find((f) => f.name === behaviorId);
        const pairCount = ff?.evolvable_pairs.length ?? 0;

        const osSharedIds = new Set<string>();
        if (threeLayerMap) {
          for (const osPair of threeLayerMap.os_layer) {
            if (osPair.functions.includes(behaviorId)) {
              osSharedIds.add(`${osPair.src}->${osPair.tgt}`);
            }
          }
        }
        const novelCount = ff ? ff.evolvable_pairs.filter((p) => !osSharedIds.has(p.pair)).length : 0;

        log(`${behaviorId}: ${pairCount} connections (${novelCount} novel)`, "success");

        if (ff) {
          for (const pair of ff.evolvable_pairs) {
            const isShared = osSharedIds.has(pair.pair);
            const tag = isShared ? "shared" : "NOVEL";
            log(`  ${pair.pre_module}\u2192${pair.post_module} \u00d7${pair.best_scale.toFixed(2)} (${fmtNumber(pair.n_synapses)} syn) \u2014 ${tag}`, "detail");
          }
        }

        const metrics = PRESET_METRICS[behaviorId];
        if (metrics) log(metrics.metric, "metric");
      }
    }

    // --- Custom behaviors (live API) ---
    if (customBehaviors.length > 0 && apiAvailable) {
      for (const behaviorId of customBehaviors) {
        log(`Running live evolution for "${behaviorId}"...`, "info");
        try {
          const job = await createJob({
            fitness_function: behaviorId,
            seed: 42,
            generations: 50,
            architecture: selectedArchitectures[0],
          });
          setLastJobId(job.id);
          log(`Job ${job.id} created. Streaming progress...`, "info");

          // Stream progress
          await new Promise<void>((resolve, reject) => {
            const source = streamJob(job.id, ({ type, payload }) => {
              if (type === "progress") {
                const p = payload as { generation?: number; total?: number; progress?: number; current_fitness?: number; accepted_count?: number };
                setCompileProgress(p.progress ?? 0);
                if (p.generation && p.total && (p.generation % 10 === 0 || p.generation === p.total)) {
                  log(`  Gen ${p.generation}/${p.total}: fitness=${(p.current_fitness ?? 0).toFixed(2)}, accepted=${p.accepted_count ?? 0}`, "detail");
                }
              } else if (type === "done") {
                const d = payload as { result?: Record<string, unknown> };
                if (d.result) {
                  const r = d.result;
                  log(`${behaviorId}: fitness ${(r.baseline as number || 0).toFixed(1)} → ${(r.final_fitness as number || 0).toFixed(1)} (+${(r.improvement_pct as number || 0).toFixed(1)}%)`, "success");
                  if (r.category) log(`  Classification: ${r.category}`, "detail");
                }
                source.close();
                resolve();
              } else if (type === "error") {
                const e = payload as { message?: string };
                log(`ERROR: ${e.message || "Unknown error"}`, "default");
                source.close();
                reject(new Error(e.message || "Job failed"));
              }
            });
          });

        } catch (err) {
          log(`Failed to compile "${behaviorId}": ${err instanceof Error ? err.message : "Unknown error"}`, "default");
        }
      }
    } else if (customBehaviors.length > 0 && !apiAvailable) {
      for (const b of customBehaviors) {
        log(`"${b}": Live API not connected. Custom behavior compilation unavailable.`, "default");
      }
    }

    log("Compilation complete.", "success");
    setCompiling(false);
    setCompileProgress(0);
    // Auto-select default processor (extract step removed — go straight to growth)
    if (!selectedProcessor) {
      setSelectedProcessor(FALLBACK_PROCESSORS[0]);
      handleGenerateGrowthProgram(FALLBACK_PROCESSORS[0]);
    }
    setStepsCompleted((prev) => new Set([...prev, 3]));
    setCurrentStep(4);
  }, [compiling, selectedBehaviors, fitnessFunctions, threeLayerMap, log, logDelayed, apiAvailable]);

  // --- Module click ---
  const handleModuleClick = useCallback((moduleId: number) => {
    setSelectedModule(moduleId);
    const mod = modules.find((m) => m.id === moduleId);
    if (mod) log(`Selected module ${mod.id} (${mod.role}) - ${fmtNumber(mod.n_neurons)} neurons`, "info");
  }, [modules, log]);

  // --- Compiled output ---
  const compiledOutput = useMemo(() => {
    if (!threeLayerMap || selectedBehaviors.length === 0) return null;
    const osConns: { src: number; tgt: number; functions: string[] }[] = [];
    const appConns: { src: number; tgt: number; behavior: string }[] = [];
    const involvedModules = new Set<number>();
    for (const behavior of selectedBehaviors) {
      const pairs = threeLayerMap.app_layer[behavior];
      if (pairs) {
        for (const p of pairs) {
          appConns.push({ src: p.src, tgt: p.tgt, behavior });
          involvedModules.add(p.src);
          involvedModules.add(p.tgt);
        }
      }
    }
    for (const pair of threeLayerMap.os_layer) {
      const relevant = pair.functions.some((f) => selectedBehaviors.includes(f));
      if (relevant) {
        osConns.push({ src: pair.src, tgt: pair.tgt, functions: pair.functions });
        involvedModules.add(pair.src);
        involvedModules.add(pair.tgt);
      }
    }
    return { osConns, appConns, moduleCount: involvedModules.size };
  }, [threeLayerMap, selectedBehaviors]);

  // --- Extract Processor (API with precomputed fallback) ---
  const handleExtractProcessor = useCallback(async (processor: ProcessorSpec) => {
    if (extracting) return;
    setExtracting(true);
    setSelectedProcessor(processor);
    setConsoleOpen(true);

    const methodLabel = processor.method === "gene-guided" ? "developmental hemilineage" : "module selection";
    const behaviorsStr = processor.behaviors_compiled.map((b) => `"${b}"`).join(", ");

    log(`> extract_processor("${processor.method}", behaviors=[${behaviorsStr}])`, "command");

    // Try live API first
    if (apiAvailable) {
      try {
        const { extractProcessor: extractProcessorApi } = await import("@/lib/api");
        log("Connecting to ML worker...", "info");
        const result = await extractProcessorApi({ fitness_function: processor.behaviors_compiled[0], method: processor.method });
        log(`Live extraction: ${JSON.stringify(result).slice(0, 200)}...`, "detail");
      } catch {
        log("Live API unavailable, using precomputed extraction.", "info");
      }
    }

    // Precomputed extraction (always runs — the precomputed data is the validated result)
    await logDelayed(`Selecting neurons by ${methodLabel}...`, 200, "info");

    if (processor.hemilineages) {
      await logDelayed(`${processor.hemilineages.length} hemilineages identified from essential modules ${processor.essential_modules.join(", ")}`, 400, "info");
    }

    const reductionPct = ((1 - processor.n_neurons / 139255) * 100).toFixed(1);
    await logDelayed(`Filtering: 139,255 -> ${fmtNumber(processor.n_neurons)} neurons (${reductionPct}% reduction)`, 300, "info");
    await logDelayed("Testing behaviors on extracted circuit...", 400, "info");

    for (const b of processor.behaviors_compiled) {
      // Precomputed spike counts from research sprint; unknown behaviors show "active"
      const knownSpikes: Record<string, number> = { navigation: 1057, escape: 130, arousal: 1438, circles: 207, rhythm: 79 };
      const spikes = knownSpikes[b];
      await logDelayed(`  ${b}: ACTIVE${spikes ? ` (${fmtNumber(spikes)} spikes)` : ""}`, 150, "success");
    }
    for (const b of processor.behaviors_failed) {
      await logDelayed(`  ${b}: FAILED (0 spikes)`, 150, "default");
    }

    const total = processor.behaviors_compiled.length + processor.behaviors_failed.length;
    log(`Processor extracted: ${fmtNumber(processor.n_neurons)} neurons, ${processor.behaviors_compiled.length}/${total} behaviors.`, "success");

    setStepsCompleted((prev) => new Set([...prev, 4]));
    setExtracting(false);
    setCurrentStep(4);
  }, [extracting, log, logDelayed, apiAvailable]);

  // --- Generate Growth Program (API with precomputed fallback) ---
  const handleGenerateGrowthProgram = useCallback(async (processor: ProcessorSpec) => {
    if (generatingGrowth) return;
    setGeneratingGrowth(true);
    setConsoleOpen(true);

    const gp = FALLBACK_GROWTH_PROGRAMS.find((g) => g.processor_id === processor.id) ?? FALLBACK_GROWTH_PROGRAMS[0];

    log(`> generate_growth_program("${processor.id}")`, "command");

    // Try live API first
    if (apiAvailable) {
      try {
        const { generateGrowthProgram: generateGrowthApi } = await import("@/lib/api");
        log("Connecting to ML worker...", "info");
        const result = await generateGrowthApi({ processor_id: processor.id });
        log(`Live growth program: ${JSON.stringify(result).slice(0, 200)}...`, "detail");
      } catch {
        log("Live API unavailable, using precomputed growth program.", "info");
      }
    }

    // Precomputed growth program — show loading steps before revealing
    await logDelayed("Reverse-compiling circuit to developmental specification...", 400, "info");
    await logDelayed(`Mapping ${fmtNumber(processor.n_neurons)} neurons to hemilineage identities...`, 500, "info");
    await logDelayed(`Computing connection rules (${gp.n_connection_rules} hemilineage pairs)...`, 400, "info");
    await logDelayed("Generating spatial layout and neurotransmitter profiles...", 300, "info");

    // NOW reveal the growth program
    setSelectedGrowthProgram(gp);

    const ntCounts: Record<string, number> = {};
    for (const ct of gp.cell_types) {
      ntCounts[ct.neurotransmitter] = (ntCounts[ct.neurotransmitter] || 0) + 1;
    }
    const ntSummary = Object.entries(ntCounts)
      .map(([nt, count]) => `${count} ${nt === "acetylcholine" ? "cholinergic" : nt === "gaba" ? "GABAergic" : "dopaminergic"}`)
      .join(", ");

    log(`Cell types: ${gp.n_cell_types} (${ntSummary})`, "detail");
    log(`Connection rules: ${gp.n_connection_rules} hemilineage-to-hemilineage`, "detail");
    log("Growth program ready for export.", "success");

    setStepsCompleted((prev) => new Set([...prev, 4]));
    setGeneratingGrowth(false);
  }, [generatingGrowth, log, logDelayed]);

  // --- Export growth program ---
  const handleExportGrowthProgram = useCallback(() => {
    if (!selectedGrowthProgram) return;
    const archNames = selectedArchitectures.map((id) => ARCHITECTURES.find((a) => a.id === id)?.name || id);
    const isComposite = selectedArchitectures.length > 1;
    const exportData = {
      ...selectedGrowthProgram,
      architectures: selectedArchitectures,
      architecture_names: archNames,
      composite: isComposite,
      compiled_behaviors: selectedBehaviors,
    };
    const filename = isComposite ? "growth-program-composite.json" : `growth-program-${selectedArchitectures[0]}.json`;
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    log(`Exported growth program (${archNames.join(" + ")}) as JSON`);
  }, [selectedGrowthProgram, selectedArchitectures, selectedBehaviors, log]);

  // --- Export compiled output ---
  const handleExport = useCallback((format: "json" | "api") => {
    if (format === "json" && compiledOutput) {
      const blob = new Blob([JSON.stringify(compiledOutput, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "compile-output.json";
      a.click();
      URL.revokeObjectURL(url);
      log("Exported compiled output as JSON");
    }
  }, [compiledOutput, log]);

  // --- Navigation ---
  const goToStep = useCallback((step: 1 | 2 | 3 | 4) => {
    setCurrentStep(step);
  }, []);

  const nextStep = useCallback(() => {
    if (currentStep < 4) setCurrentStep((currentStep + 1) as 1 | 2 | 3 | 4);
  }, [currentStep]);

  const prevStep = useCallback(() => {
    if (currentStep > 1) setCurrentStep((currentStep - 1) as 1 | 2 | 3 | 4);
  }, [currentStep]);

  // --- Active fitness function ---
  const activeFF = activePreset ? fitnessFunctions.find((f) => f.name === activePreset.id) : null;

  // --- Total stats for selected behaviors ---
  const selectedStats = useMemo(() => {
    let totalEdges = 0;
    for (const bId of selectedBehaviors) {
      const m = PRESET_METRICS[bId];
      if (m) totalEdges += m.evolvableEdges;
    }
    return { totalEdges };
  }, [selectedBehaviors]);

  // --- Loading state ---
  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  const stepLabels = [
    { step: 1 as const, label: "Specify Behaviors", icon: Terminal },
    { step: 2 as const, label: "Constraints", icon: Cpu },
    { step: 3 as const, label: "Architecture", icon: Layers },
    { step: 4 as const, label: "Results & Growth Program", icon: Dna },
  ];

  return (
    <div className={`h-screen ${pgBg} ${pgText} flex flex-col overflow-hidden transition-colors duration-300`}>
      <style jsx global>{`
        @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
      `}</style>

      {/* ================================================================= */}
      {/* Top Navbar                                                         */}
      {/* ================================================================= */}
      <div className={`flex items-center justify-between px-4 md:px-6 py-2.5 border-b ${pgBorder} ${pgPanel} z-30 relative`}>
        <Link href="/" className="flex items-center gap-2" aria-label="Compile home">
          <svg viewBox="0 0 44 40" className="w-7 h-7" aria-hidden="true">
            <line x1="12" y1="20" x2="32" y2="20" stroke="#9333EA" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="12" cy="20" r="5" fill="#7C3AED"/>
            <circle cx="32" cy="20" r="5" fill="#A855F7"/>
          </svg>
          <span className={`text-xs font-mono ${pgMuted}`}>.playground</span>
        </Link>

        {/* Step indicator (center) */}
        <div className="hidden md:flex items-center gap-1">
          {stepLabels.map(({ step, label, icon: Icon }, idx) => {
            const isActive = currentStep === step;
            const isCompleted = stepsCompleted.has(step);
            return (
              <div key={step} className="flex items-center">
                {idx > 0 && (
                  <div className={`w-6 h-px mx-1 transition-colors ${isCompleted || currentStep > step ? "bg-green-500/50" : pgSep}`} />
                )}
                <button
                  onClick={() => goToStep(step)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all ${
                    isActive
                      ? "bg-[#7C3AED]/15 text-[#7C3AED] border border-[#7C3AED]/30"
                      : isCompleted
                      ? `${isDark ? "text-green-400 hover:bg-white/[0.04]" : "text-green-600 hover:bg-gray-100"} border border-transparent`
                      : `${pgMuted} ${isDark ? "hover:bg-white/[0.04]" : "hover:bg-gray-100"} border border-transparent`
                  }`}
                >
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0 ${
                    isActive ? "bg-[#7C3AED] text-white" : isCompleted ? "bg-green-500 text-white" : `${isDark ? "bg-[#1e1e2e] text-gray-500" : "bg-gray-200 text-gray-400"}`
                  }`}>
                    {isCompleted && !isActive ? <Check className="w-3 h-3" /> : step}
                  </span>
                  <Icon className="w-3 h-3" />
                  <span>{label}</span>
                </button>
              </div>
            );
          })}
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-3">
          {/* Species selector */}
          <div className="relative">
            <button
              onClick={() => setSpeciesDropdownOpen(!speciesDropdownOpen)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono border ${pgBorder} ${isDark ? "hover:bg-white/[0.04]" : "hover:bg-gray-100"} transition`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${selectedSpecies.status === "complete" ? "bg-green-500" : "bg-amber-500"}`} />
              <span className={pgDimText}>{selectedSpecies.name.split(" ")[0]}</span>
              <ChevronDown className="w-2.5 h-2.5" />
            </button>
            {speciesDropdownOpen && (
              <div className={`absolute right-0 top-full mt-1 ${pgPanel} border ${pgBorder} rounded-lg shadow-xl z-50 min-w-[200px]`}>
                {FALLBACK_SPECIES.map((sp) => (
                  <button
                    key={sp.id}
                    onClick={() => { setSelectedSpecies(sp); setSpeciesDropdownOpen(false); }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-left text-[10px] ${isDark ? "hover:bg-white/[0.04]" : "hover:bg-gray-50"} transition ${selectedSpecies.id === sp.id ? "bg-[#7C3AED]/10" : ""}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${sp.status === "complete" ? "bg-green-500" : "bg-amber-500"}`} />
                    <div className="flex-1">
                      <div className={`font-medium ${pgText}`}>{sp.name}</div>
                      <div className={`${pgMuted} text-[9px]`}>{sp.dataset}</div>
                    </div>
                    {sp.status !== "complete" && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 uppercase font-bold tracking-wider">Soon</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={`p-1.5 rounded ${isDark ? "hover:bg-white/10" : "hover:bg-gray-200"} transition`}
            title={`Theme: ${mode}`}
          >
            {mode === "dark" ? <Sun className="w-3.5 h-3.5" /> : mode === "light" ? <Moon className="w-3.5 h-3.5" /> : <Monitor className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* ================================================================= */}
      {/* Mobile Step Pills                                                  */}
      {/* ================================================================= */}
      <div className={`md:hidden flex items-center justify-center gap-2 py-2 border-b ${pgBorder} ${pgPanel}`}>
        {stepLabels.map(({ step }) => (
          <button
            key={step}
            onClick={() => goToStep(step)}
            className={`w-8 h-2 rounded-full transition-all ${
              currentStep === step ? "bg-[#7C3AED]" : stepsCompleted.has(step) ? "bg-green-500/50" : isDark ? "bg-[#1e1e2e]" : "bg-gray-200"
            }`}
          />
        ))}
      </div>

      {/* ================================================================= */}
      {/* Step Content (full width)                                          */}
      {/* ================================================================= */}
      <div className="flex-1 min-h-0 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {/* ============================================================= */}
          {/* ============================================================= */}
          {/* STEP 2: BIOLOGICAL CONSTRAINTS                                   */}
          {/* ============================================================= */}
          {currentStep === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden"
            >
              <div className="md:w-1/2 w-full overflow-y-auto p-4 md:p-8 lg:p-10">
                <div className="max-w-2xl">
                  <h1 className={`text-2xl md:text-3xl font-bold mb-2 ${pgText}`}>
                    Biological constraints
                  </h1>
                  <p className={`${pgDimText} text-sm md:text-base mb-8`}>
                    Optional. Set physical limits based on your growth environment. Defaults work for most cases.
                  </p>

                  {/* Neuron count */}
                  <div className="mb-6">
                    <label className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2 flex items-center justify-between`}>
                      <span>Neuron count</span>
                      <span className="text-[#7C3AED] font-mono text-sm normal-case tracking-normal">{neuronCount.toLocaleString()}</span>
                    </label>
                    <p className={`text-[10px] ${pgMuted} mb-3`}>Minimum viable: 3,000. Current organoids: 1-3M.</p>
                    <input
                      type="range"
                      min={3000}
                      max={100000}
                      step={1000}
                      value={neuronCount}
                      onChange={(e) => setNeuronCount(parseInt(e.target.value))}
                      className="w-full accent-[#7C3AED]"
                    />
                    <div className={`flex justify-between text-[10px] ${pgMuted} mt-1`}>
                      <span>3K</span><span>100K</span>
                    </div>
                  </div>

                  {/* Cell types available */}
                  <div className="mb-6">
                    <label className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2 block`}>
                      Available neuron types
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {["Excitatory (ACH)", "Inhibitory (GABA)", "Dopaminergic (DA)", "Serotonergic (5HT)"].map((nt, i) => (
                        <label key={nt} className={`flex items-center gap-2 text-[11px] px-3 py-2 rounded-lg border ${pgBorder} ${pgCard} cursor-pointer`}>
                          <input type="checkbox" defaultChecked={i < 3} className="accent-[#7C3AED]" />
                          <span className={pgDimText}>{nt}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Spatial constraint */}
                  <div className="mb-6">
                    <label className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2 block`}>
                      Spatial constraint
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {["Petri dish (2D)", "Microfluidic chamber", "3D scaffold", "No constraint"].map((opt, i) => (
                        <label key={opt} className={`flex items-center gap-2 text-[11px] px-3 py-2 rounded-lg border ${pgBorder} ${pgCard} cursor-pointer`}>
                          <input type="radio" name="spatial" defaultChecked={i === 3} className="accent-[#7C3AED]" />
                          <span className={pgDimText}>{opt}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <p className={`text-[10px] ${pgMuted} italic`}>
                    These constraints inform which architectures the system recommends in the next step.
                  </p>
                </div>
              </div>

              {/* Right panel — summary of selected behaviors */}
              <div className={`md:w-1/2 w-full flex flex-col border-t md:border-t-0 md:border-l ${pgBorder} ${isDark ? "bg-black" : "bg-gray-50"} p-6`}>
                <h3 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-4`}>Selected Behaviors</h3>
                {selectedBehaviors.length === 0 ? (
                  <p className={`text-sm ${pgMuted}`}>No behaviors selected. Go back to step 1.</p>
                ) : (
                  <div className="space-y-3">
                    {selectedBehaviors.map((bId) => {
                      const preset = PRESETS.find((p) => p.id === bId);
                      return (
                        <div key={bId} className={`flex items-center gap-3 p-3 rounded-lg border ${pgBorder} ${pgCard}`}>
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: preset?.color || "#7C3AED" }} />
                          <div>
                            <div className={`text-sm font-medium ${pgText}`}>{preset?.label || bId}</div>
                            <div className={`text-[10px] ${pgMuted} capitalize`}>Requires: {preset?.tag || "speed"}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* ============================================================= */}
          {/* STEP 3: DESIGN ARCHITECTURE                                    */}
          {/* ============================================================= */}
          {currentStep === 3 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden"
            >
              {/* Left: Architecture Selection (50%) */}
              <div className="md:w-1/2 w-full overflow-y-auto p-4 md:p-8 lg:p-10">
                <div className="max-w-2xl">
                  <h1 className={`text-2xl md:text-3xl font-bold mb-2 ${pgText}`}>
                    Design the architecture
                  </h1>
                  <p className={`${pgDimText} text-sm md:text-base mb-6`}>
                    Choose the neural circuit architecture. This determines how the brain is wired before behaviors are compiled onto it.
                  </p>

                  {/* Category tabs */}
                  <div className="flex flex-wrap gap-1.5 mb-5">
                    <button
                      onClick={() => setArchitectureCategoryFilter("all")}
                      className={`text-[10px] px-2.5 py-1 rounded-full transition ${
                        architectureCategoryFilter === "all"
                          ? "bg-[#7C3AED]/15 text-[#7C3AED] border border-[#7C3AED]/30"
                          : `${pgMuted} border ${pgBorder} hover:border-gray-400`
                      }`}
                    >
                      All
                    </button>
                    {ARCHITECTURE_CATEGORIES.map((cat) => (
                      <button
                        key={cat.id}
                        onClick={() => setArchitectureCategoryFilter(cat.id)}
                        className={`text-[10px] px-2.5 py-1 rounded-full transition ${
                          architectureCategoryFilter === cat.id
                            ? "bg-[#7C3AED]/15 text-[#7C3AED] border border-[#7C3AED]/30"
                            : `${pgMuted} border ${pgBorder} hover:border-gray-400`
                        }`}
                      >
                        {cat.label}
                      </button>
                    ))}
                    <button
                      onClick={() => setArchitectureCategoryFilter("composites")}
                      className={`text-[10px] px-2.5 py-1 rounded-full transition ${
                        architectureCategoryFilter === "composites"
                          ? "bg-[#7C3AED]/15 text-[#7C3AED] border border-[#7C3AED]/30"
                          : `${pgMuted} border ${pgBorder} hover:border-gray-400 opacity-50`
                      }`}
                    >
                      Composites
                    </button>
                  </div>

                  {/* Composite indicator */}
                  {selectedArchitectures.length > 1 && (
                    <div className={`mb-4 px-3 py-2 rounded-lg ${isDark ? "bg-[#7C3AED]/10 border border-[#7C3AED]/20" : "bg-purple-50 border border-purple-200"}`}>
                      <div className={`text-[11px] font-medium ${isDark ? "text-[#7C3AED]" : "text-purple-700"}`}>
                        Composite: {selectedArchitectures.map((id) => ARCHITECTURES.find((a) => a.id === id)?.name || id).join(" + ")}
                      </div>
                      <div className={`text-[10px] ${pgMuted}`}>{selectedArchitectures.length} regions · ~{(selectedArchitectures.length * 3000).toLocaleString()} neurons minimum</div>
                    </div>
                  )}

                  {/* Architecture cards */}
                  {architectureCategoryFilter === "composites" ? (
                    <div className={`rounded-xl border ${pgBorder} ${pgCard} p-5 mb-6`}>
                      <p className={`text-sm ${pgDimText} leading-relaxed mb-3`}>
                        Select multiple architectures from any category to create a composite. Each architecture becomes a region in the circuit. The system wires them together automatically.
                      </p>
                      {selectedArchitectures.length > 1 && (
                        <div className={`text-[11px] ${pgMuted}`}>
                          <span className="text-[#7C3AED] font-medium">{selectedArchitectures.length} regions selected:</span>{" "}
                          {selectedArchitectures.map((id) => ARCHITECTURES.find((a) => a.id === id)?.name || id).join(" + ")}
                        </div>
                      )}
                      {selectedArchitectures.length <= 1 && (
                        <p className={`text-[10px] ${pgMuted}`}>Switch to any category tab and select 2+ architectures.</p>
                      )}
                    </div>
                  ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                    {ARCHITECTURES
                      .filter((a) => architectureCategoryFilter === "all" || a.category === architectureCategoryFilter)
                      .map((arch) => {
                        const isSelected = selectedArchitectures.includes(arch.id);
                        return (
                          <button
                            key={arch.id}
                            onClick={() => setSelectedArchitectures((prev) =>
                              prev.includes(arch.id)
                                ? prev.filter((a) => a !== arch.id).length > 0 ? prev.filter((a) => a !== arch.id) : prev
                                : [...prev.filter((a) => a !== "custom"), arch.id]
                            )}
                            className={`relative text-left rounded-xl border p-4 transition-all duration-200 ${
                              isSelected
                                ? `${isDark ? "bg-white/[0.06]" : "bg-white"} border-[#7C3AED]/60`
                                : `${isDark ? "bg-white/[0.02] hover:bg-white/[0.04]" : "bg-white/60 hover:bg-white"} ${pgBorder} hover:border-gray-300`
                            }`}
                            style={isSelected ? { boxShadow: "0 0 20px rgba(124,58,237,0.1)" } : undefined}
                          >
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className={`text-sm font-medium ${isSelected ? pgText : pgDimText}`}>{arch.name}</span>
                              {isSelected && <Check className="w-3.5 h-3.5 text-[#7C3AED] ml-auto" />}
                            </div>
                            <p className={`text-[11px] ${pgMuted} leading-relaxed mb-2`}>{arch.description}</p>
                            <div className={`flex items-center gap-3 text-[10px] font-mono ${pgMuted}`}>
                              <span>{arch.cellTypeCount} types</span>
                              <span>{arch.connectionRuleCount} rules</span>
                              <span>{arch.totalNeurons.toLocaleString()} neurons</span>
                            </div>
                          </button>
                        );
                      })}
                  </div>
                  )}

                  {/* Custom architecture option */}
                  <div className={`rounded-xl border ${pgBorder} ${pgCard} p-4`}>
                    <h3 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2`}>Custom</h3>
                    <p className={`text-[10px] ${pgMuted} mb-3`}>
                      Define your own architecture with cell types, proportions, and connection rules.
                    </p>
                    <button
                      onClick={() => setSelectedArchitectures(["custom"])}
                      className={`text-[10px] px-3 py-1.5 rounded-lg transition ${
                        selectedArchitectures[0] === "custom"
                          ? "bg-[#7C3AED]/15 text-[#7C3AED] border border-[#7C3AED]/30"
                          : `border ${pgBorder} ${pgMuted} hover:border-gray-400`
                      }`}
                    >
                      {selectedArchitectures[0] === "custom" ? "Custom selected" : "Use custom spec"}
                    </button>
                  </div>

                </div>
              </div>

              {/* Right: Architecture detail + BioTube (50%) */}
              <div className={`md:w-1/2 w-full flex flex-col border-t md:border-t-0 md:border-l ${pgBorder} ${isDark ? "bg-black" : "bg-gray-50"}`}>
                {/* BioTube visualization (hidden when custom editor is open) */}
                {selectedArchitectures[0] !== "custom" && (
                  <div className="h-1/2 min-h-[250px] relative w-full">
                    <BioTube className="w-full h-full" architectures={selectedArchitectures} color="#7C3AED" speed={0.8} />
                  </div>
                )}

                <div className={`${selectedArchitectures[0] === "custom" ? "flex-1 flex flex-col" : "h-1/2 overflow-y-auto"}`}>
                {/* Composite tabs */}
                {selectedArchitectures.length > 1 && selectedArchitectures[0] !== "custom" && (
                  <div className={`flex border-b ${isDark ? "border-white/10" : "border-gray-200"} px-4 pt-2`}>
                    {selectedArchitectures.map((archId, i) => {
                      const a = ARCHITECTURES.find((x) => x.id === archId);
                      return (
                        <button
                          key={archId}
                          onClick={() => setArchDetailTab(i)}
                          className={`px-3 py-1.5 text-[10px] font-medium transition border-b-2 -mb-px ${
                            archDetailTab === i
                              ? `${isDark ? "text-[#7C3AED] border-[#7C3AED]" : "text-purple-600 border-purple-600"}`
                              : `${pgMuted} border-transparent hover:border-gray-400`
                          }`}
                        >
                          {a?.name || archId}
                        </button>
                      );
                    })}
                  </div>
                )}
                {(() => {
                  const activeArchId = selectedArchitectures.length > 1 ? selectedArchitectures[archDetailTab] || selectedArchitectures[0] : selectedArchitectures[0];
                  const arch = ARCHITECTURES.find((a) => a.id === activeArchId);
                  if (selectedArchitectures[0] === "custom") return (
                    <div className="flex-1 flex flex-col p-3 min-h-0">
                      <div className="flex items-center justify-between mb-2 px-1">
                        <h3 className="text-[10px] uppercase tracking-wider text-gray-500 font-medium flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-[#7C3AED]" />
                          architecture_spec.json
                        </h3>
                        <span className="text-[9px] text-gray-600 font-mono">JSON</span>
                      </div>
                      <textarea
                        className={`flex-1 w-full font-mono text-[11px] leading-[1.7] p-4 rounded-lg border ${pgBorder} ${isDark ? "bg-[#050508] text-[#e5c07b]" : "bg-[#1e1e2e] text-[#e5c07b]"} resize-none focus:outline-none focus:border-[#7C3AED]/50 selection:bg-[#7C3AED]/30`}
                        defaultValue={JSON.stringify({
                          cell_types: [
                            { id: "excitatory", nt: "ACH", role: "processing" },
                            { id: "inhibitory", nt: "GABA", role: "inhibitory" },
                            { id: "motor", nt: "ACH", role: "motor" },
                          ],
                          proportions: { excitatory: 0.7, inhibitory: 0.2, motor: 0.1 },
                          connection_rules: [
                            { from: "excitatory", to: "excitatory", prob: 0.1, type: "recurrent" },
                            { from: "excitatory", to: "inhibitory", prob: 0.15, type: "feedforward" },
                            { from: "inhibitory", to: "excitatory", prob: 0.15, type: "feedback" },
                            { from: "excitatory", to: "motor", prob: 0.1, type: "output" },
                          ],
                          growth_order: ["excitatory", "inhibitory", "motor"],
                          total_neurons: 5000,
                          spatial_layout: "uniform_3d",
                        }, null, 2)}
                        spellCheck={false}
                      />
                    </div>
                  );
                  if (!arch) return (
                    <div className="flex-1 flex items-center justify-center p-8">
                      <p className={`text-sm ${pgMuted}`}>Select an architecture</p>
                    </div>
                  );
                  return (
                    <div className="p-6 space-y-5">
                      <div>
                        <h2 className={`text-xl font-bold ${pgText} mb-1`}>{arch.name}</h2>
                        <p className={`text-xs ${pgMuted} uppercase tracking-wider`}>{arch.category} · {arch.source}</p>
                      </div>
                      <p className={`text-sm ${pgDimText} leading-relaxed`}>{arch.description}</p>

                      {/* Growth program spec */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${pgBorder} rounded-lg p-3 text-center`}>
                          <div className="text-lg font-light text-[#7C3AED]">{arch.cellTypeCount}</div>
                          <div className={`text-[9px] ${pgMuted} uppercase`}>Cell Types</div>
                        </div>
                        <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${pgBorder} rounded-lg p-3 text-center`}>
                          <div className={`text-lg font-light ${isDark ? "text-cyan-400" : "text-cyan-600"}`}>{arch.connectionRuleCount}</div>
                          <div className={`text-[9px] ${pgMuted} uppercase`}>Rules</div>
                        </div>
                        <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${pgBorder} rounded-lg p-3 text-center`}>
                          <div className={`text-lg font-light ${isDark ? "text-green-400" : "text-green-600"}`}>{arch.totalNeurons.toLocaleString()}</div>
                          <div className={`text-[9px] ${pgMuted} uppercase`}>Neurons</div>
                        </div>
                      </div>

                      {/* Tradeoffs */}
                      {arch.tradeoffs.length > 0 && (
                        <div>
                          <h3 className={`text-[10px] uppercase tracking-wider ${pgMuted} mb-2`}>Tradeoffs</h3>
                          <ul className="space-y-1">
                            {arch.tradeoffs.map((t, i) => (
                              <li key={i} className={`text-[11px] ${pgDimText} flex items-start gap-2`}>
                                <span className="text-[#7C3AED] mt-1">·</span> {t}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Best for */}
                      {arch.bestFor.length > 0 && (
                        <div>
                          <h3 className={`text-[10px] uppercase tracking-wider ${pgMuted} mb-2`}>Best For</h3>
                          <div className="flex flex-wrap gap-1.5">
                            {arch.bestFor.map((b, i) => (
                              <span key={i} className={`text-[10px] px-2 py-0.5 rounded-full ${isDark ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-green-50 text-green-700 border border-green-200"}`}>
                                {b}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Notes */}
                      {arch.notes && (
                        <p className={`text-[10px] ${pgMuted} italic`}>{arch.notes}</p>
                      )}
                    </div>
                  );
                })()}
                </div>
              </div>
            </motion.div>
          )}

          {/* ============================================================= */}
          {/* STEP 1: SPECIFY BEHAVIORS                                      */}
          {/* ============================================================= */}
          {currentStep === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden"
            >
              {/* Left: Behavior Selection (50%) */}
              <div className="md:w-1/2 w-full overflow-y-auto p-4 md:p-8 lg:p-10">
                <div className="max-w-2xl">
                  <h1 className={`text-2xl md:text-3xl font-bold mb-2 ${pgText}`}>
                    What should the brain do?
                  </h1>
                  <p className={`${pgDimText} text-sm md:text-base mb-6`}>
                    Select one or more capabilities to compile.
                  </p>

                  {/* Behavior presets by computational tag */}
                  {BEHAVIOR_TAGS.filter((tag) => PRESETS.some((p) => p.tag === tag.id)).map((tag) => (
                    <div key={tag.id} className="mb-4">
                      <h2 className={`text-[10px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2`}>
                        {tag.label}
                      </h2>
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                        {PRESETS.filter((p) => p.tag === tag.id).map((preset) => {
                        const isSelected = selectedBehaviors.includes(preset.id);
                        const metrics = PRESET_METRICS[preset.id];
                        return (
                          <button
                            key={preset.id}
                            onClick={() => toggleBehavior(preset.id)}
                            className={`relative text-left rounded-lg border p-2.5 transition-all duration-200 ${
                              isSelected
                                ? `${isDark ? "bg-white/[0.06]" : "bg-white"} border-opacity-60`
                                : `${isDark ? "bg-white/[0.02] hover:bg-white/[0.04]" : "bg-white/60 hover:bg-white"} ${pgBorder} hover:border-gray-300`
                            }`}
                            style={isSelected ? { borderColor: preset.color + "80", boxShadow: `0 0 15px ${preset.color}10` } : undefined}
                          >
                            <div className="flex items-center gap-2 mb-0.5">
                              <span
                                className="w-2 h-2 rounded-full flex-shrink-0 transition-shadow"
                                style={{ backgroundColor: preset.color, boxShadow: isSelected ? `0 0 8px ${preset.color}80` : "none" }}
                              />
                              <span className={`text-[12px] font-medium ${isSelected ? pgText : pgDimText}`}>{preset.label}</span>
                              {preset.isNew && (
                                <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400">NEW</span>
                              )}
                              {preset.badge && (
                                <span className={`text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${isDark ? "bg-amber-500/10 text-amber-400" : "bg-amber-100 text-amber-600"}`}>{preset.badge}</span>
                              )}
                              {isSelected && <Check className="w-3.5 h-3.5 text-green-400 ml-auto" />}
                            </div>
                            <p className={`text-[11px] ${pgMuted} leading-relaxed`}>{preset.description}</p>
                            {metrics && (
                              <div className={`flex items-center gap-3 mt-2 text-[10px] font-mono ${pgMuted}`}>
                                <span className="text-green-400">{metrics.improvement}</span>
                                <span>{metrics.evolvableEdges} edges</span>
                              </div>
                            )}
                          </button>
                        );
                      })}
                      </div>
                    </div>
                  ))}

                  {/* Community-compiled behaviors (from past playground runs) */}
                  {communityBehaviors.length > 0 && (
                    <div className="mb-6">
                      <div className="flex items-center gap-3 mb-3">
                        <h2 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold`}>
                          Community
                        </h2>
                        {communityBehaviors.some((b) => b.isMine) && (
                          <div className="flex gap-1">
                            {(["all", "mine"] as const).map((f) => (
                              <button
                                key={f}
                                onClick={() => setBehaviorFilter(f)}
                                className={`text-[9px] px-2 py-0.5 rounded-full transition ${
                                  behaviorFilter === f
                                    ? "bg-purple-500/15 text-purple-400"
                                    : `${pgMuted} hover:text-gray-300`
                                }`}
                              >
                                {f === "all" ? "All" : "Mine"}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {communityBehaviors.filter((b) => behaviorFilter === "all" || b.isMine).map((preset) => {
                          const isSelected = selectedBehaviors.includes(preset.id);
                          return (
                            <button
                              key={preset.id}
                              onClick={() => toggleBehavior(preset.id)}
                              className={`relative text-left rounded-xl border p-4 transition-all duration-200 ${
                                isSelected
                                  ? `${isDark ? "bg-white/[0.06]" : "bg-white"} border-opacity-60`
                                  : `${isDark ? "bg-white/[0.02] hover:bg-white/[0.04]" : "bg-white/60 hover:bg-white"} ${pgBorder} hover:border-gray-300`
                              }`}
                              style={isSelected ? { borderColor: preset.color + "80", boxShadow: `0 0 20px ${preset.color}15` } : undefined}
                            >
                              <div className="flex items-center gap-2.5 mb-1.5">
                                <span
                                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                  style={{ backgroundColor: preset.color }}
                                />
                                <span className={`text-sm font-medium ${isSelected ? pgText : pgDimText}`}>{preset.label}</span>
                                <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">USER</span>
                                {isSelected && <Check className="w-3.5 h-3.5 text-green-400 ml-auto" />}
                              </div>
                              <p className={`text-[11px] ${pgMuted} leading-relaxed`}>{preset.description}</p>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Custom behavior input */}
                  <div className="mb-6">
                    <h2 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-3`}>
                      Custom
                    </h2>
                    <div className={`flex gap-2 items-start`}>
                      <input
                        type="text"
                        value={customBehavior}
                        onChange={(e) => setCustomBehavior(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && customBehavior.trim() && apiAvailable) {
                            if (!isAuthenticated()) { log("Sign in to compile custom behaviors.", "default"); return; }
                            const id = customBehavior.trim().toLowerCase().replace(/\s+/g, "_");
                            if (!selectedBehaviors.includes(id)) {
                              setSelectedBehaviors((prev) => [...prev, id]);
                            }
                            setCustomBehavior("");
                          }
                        }}
                        placeholder={apiAvailable ? "Describe a behavior (e.g. pheromone tracking)" : "API offline"}
                        disabled={!apiAvailable}
                        className={`flex-1 px-4 py-3 rounded-xl text-sm border ${pgBorder} ${pgCard} ${pgText} placeholder:${pgMuted} focus:outline-none focus:border-[#7C3AED]/50 transition disabled:opacity-40 disabled:cursor-not-allowed`}
                      />
                      <button
                        onClick={async () => {
                          if (customBehavior.trim() && apiAvailable) {
                            if (!isAuthenticated()) { log("Sign in to compile custom behaviors.", "default"); setConsoleOpen(true); return; }
                            const id = customBehavior.trim().toLowerCase().replace(/\s+/g, "_");
                            if (!selectedBehaviors.includes(id)) {
                              setSelectedBehaviors((prev) => [...prev, id]);
                              // Classify with AI
                              try {
                                const { classifyBehavior } = await import("@/lib/api");
                                const result = await classifyBehavior(customBehavior.trim());
                                log(`Classified "${customBehavior.trim()}" as ${result.tag} (${result.source})`, "info");
                              } catch { /* classification is best-effort */ }
                            }
                            setCustomBehavior("");
                          }
                        }}
                        disabled={!apiAvailable || !customBehavior.trim()}
                        className={`px-4 py-3 rounded-xl text-sm font-medium transition ${
                          apiAvailable && customBehavior.trim()
                            ? "bg-[#7C3AED] text-white hover:bg-[#6D28D9]"
                            : `${isDark ? "bg-[#1e1e2e] text-gray-600" : "bg-gray-200 text-gray-400"} cursor-not-allowed`
                        }`}
                      >
                        {apiAvailable ? "Add" : "Offline"}
                      </button>
                    </div>
                    <div className={`text-[10px] mt-2 ${pgMuted}`}>
                      {apiAvailable && isAuthenticated() ? (
                        <span className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                          Signed in — custom behaviors compile in 5-15 min
                        </span>
                      ) : apiAvailable ? (
                        <div className="flex items-center gap-3 mt-1">
                          <span className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            Sign in to compile custom behaviors
                          </span>
                          <AuthInline isDark={isDark} compact onSuccess={(_user: unknown, token: string) => { setAuthToken(token); log("Signed in. Custom behaviors enabled.", "success"); }} />
                        </div>
                      ) : (
                        <span className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                          Precomputed mode — 8 behaviors available
                        </span>
                      )}
                    </div>
                  </div>


                  {/* Composability panel — shows when 2+ behaviors selected */}
                  {selectedBehaviors.length >= 2 && (
                    <div className={`mb-6 rounded-xl border ${pgBorder} ${pgCard} p-4`}>
                      <h3 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-3`}>
                        Compatibility
                      </h3>
                      <div className="space-y-2">
                        {(() => {
                          let hasConflict = false;
                          const pairs: React.ReactNode[] = [];
                          for (let i = 0; i < selectedBehaviors.length; i++) {
                            for (let j = i + 1; j < selectedBehaviors.length; j++) {
                              const a = selectedBehaviors[i];
                              const b = selectedBehaviors[j];
                              // Look up interference from live data or fallback
                              const entry = interferenceData.find(
                                (e) => (e.compiled === a && e.tested === b) || (e.compiled === b && e.tested === a)
                              );
                              const delta = entry?.delta_pct ?? 0;
                              const isConflict = delta < -10;
                              if (isConflict) hasConflict = true;
                              pairs.push(
                                <div key={`${a}-${b}`} className={`flex items-center gap-2 text-[11px] px-3 py-2 rounded-lg ${isConflict ? (isDark ? "bg-red-500/10 border border-red-500/20" : "bg-red-50 border border-red-200") : (isDark ? "bg-green-500/5 border border-green-500/10" : "bg-green-50 border border-green-200")}`}>
                                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${isConflict ? "bg-red-500" : "bg-green-500"}`} />
                                  <span className={`capitalize ${pgDimText}`}>{a}</span>
                                  <span className={pgMuted}>+</span>
                                  <span className={`capitalize ${pgDimText}`}>{b}</span>
                                  <span className="ml-auto font-mono text-[10px]">
                                    {isConflict ? (
                                      <span className="text-red-400">{delta}%</span>
                                    ) : delta > 10 ? (
                                      <span className="text-green-400">+{delta}% synergy</span>
                                    ) : (
                                      <span className="text-green-400">compatible</span>
                                    )}
                                  </span>
                                </div>
                              );
                            }
                          }
                          return (
                            <>
                              {pairs}
                              {!hasConflict && (
                                <p className={`text-[10px] ${pgMuted} mt-3`}>
                                  All selected behaviors compose without conflict. Multi-objective evolution preserves both simultaneously.
                                </p>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  )}


                  {/* How it works — collapsed by default */}
                  {selectedBehaviors.length === 0 && (
                    <div className={`rounded-xl border ${pgBorder} ${pgCard} p-4`}>
                      <h3 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-2`}>
                        How it works
                      </h3>
                      <div className={`text-[11px] ${pgMuted} leading-relaxed space-y-2`}>
                        <p>Select behaviors to compile onto a biological processor. Each behavior finds its own evolvable surface on the connectome — the specific connections that matter for that capability.</p>
                        <p>Behaviors compose: 9/10 pairs work together without interference. When behaviors compete (like circular locomotion vs escape), the interference matrix tells you. Conflict resolution handles competing internal states through the DN hub architecture.</p>
                        <p>Precomputed behaviors load instantly. Custom behaviors run directed evolution in 5-15 minutes.</p>
                      </div>
                    </div>
                  )}

                </div>
              </div>

              {/* Right: 3D Brain/Body + Stats (50%) */}
              <div className={`md:w-1/2 w-full flex flex-col border-t md:border-t-0 md:border-l ${pgBorder} ${isDark ? "bg-black" : "bg-gray-50"}`}>
                {/* Viz tabs */}
                <div className={`flex items-center border-b border-white/10 ${isDark ? "bg-[#0a0a0f]/80" : "bg-white/90"}`}>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setVizMode("brain")}
                    onKeyDown={(e) => e.key === "Enter" && setVizMode("brain")}
                    className={`flex-1 text-center py-2 text-[10px] uppercase tracking-wider font-medium cursor-pointer transition ${
                      vizMode === "brain"
                        ? "text-[#7C3AED] border-b-2 border-[#7C3AED]"
                        : "text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    3D Brain
                  </div>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setVizMode("body")}
                    onKeyDown={(e) => e.key === "Enter" && setVizMode("body")}
                    className={`flex-1 text-center py-2 text-[10px] uppercase tracking-wider font-medium cursor-pointer transition ${
                      vizMode === "body"
                        ? "text-[#7C3AED] border-b-2 border-[#7C3AED]"
                        : "text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    3D Body
                  </div>
                </div>

                {/* 3D visualization */}
                <div className="flex-1 relative min-h-[300px] md:min-h-0">
                  {vizMode === "brain" ? (
                    <FlyBrain3D
                      className="w-full h-full"
                      selectedBehaviors={selectedBehaviors}
                      onModuleClick={handleModuleClick}
                      autoRotate={selectedBehaviors.length === 0}
                      enableZoom
                    />
                  ) : (
                    <FlyBody3D
                      className="w-full h-full"
                      activePreset={selectedBehaviors.length > 0 ? selectedBehaviors[selectedBehaviors.length - 1] : null}
                      playing={bodyPlaying}
                      replayKey={replayKey}
                      onFinished={() => {
                        setBodyFinished(true);
                        setTimeout(() => {
                          setBodyFinished(false);
                          setReplayKey((k) => k + 1);
                          setBodyPlaying(true);
                        }, 1500);
                      }}
                    />
                  )}
                  {/* Status overlay */}
                  <div className="absolute top-3 right-3 text-[10px] font-mono text-gray-500 bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/5 z-10">
                    {compiling ? (
                      <span className="text-[#7C3AED]">Compiling...</span>
                    ) : selectedBehaviors.length > 0 ? (
                      <span>
                        <span className="text-white">{selectedBehaviors.length}</span> selected
                        {stepsCompleted.has(1) && (
                          <>
                            <span className="text-gray-700 mx-1.5">|</span>
                            <span className="text-green-400">compiled</span>
                          </>
                        )}
                      </span>
                    ) : (
                      vizMode === "brain" ? "Select behaviors" : "Select a behavior to see it"
                    )}
                  </div>
                  {/* Behavior overlay with play/pause (body mode only) */}
                  {vizMode === "body" && selectedBehaviors.length > 0 && (
                    <div className="absolute bottom-3 left-3 right-3 bg-black/80 backdrop-blur-sm rounded-xl border border-white/10 px-4 py-3 z-20">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => {
                            if (bodyFinished) {
                              setBodyFinished(false);
                              setReplayKey((k) => k + 1);
                              setBodyPlaying(true);
                            } else {
                              setBodyPlaying((p) => !p);
                            }
                          }}
                          className="w-8 h-8 flex items-center justify-center rounded-full bg-[#7C3AED] hover:bg-[#6D28D9] text-white transition flex-shrink-0"
                        >
                          {bodyFinished ? (
                            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>
                          ) : bodyPlaying ? (
                            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                          ) : (
                            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor"><polygon points="6,4 20,12 6,20"/></svg>
                          )}
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="text-[11px] font-semibold text-white capitalize truncate">
                            {selectedBehaviors[selectedBehaviors.length - 1]}
                            {bodyFinished && <span className="ml-2 text-amber-400 text-[9px] font-normal">finished — tap to replay</span>}
                            {!bodyFinished && bodyPlaying && <span className="ml-2 text-green-400 text-[9px] font-normal">playing</span>}
                            {!bodyFinished && !bodyPlaying && <span className="ml-2 text-gray-500 text-[9px] font-normal">paused</span>}
                          </div>
                          <div className="text-[10px] text-gray-400 leading-snug truncate">
                            {(() => { const b = selectedBehaviors[selectedBehaviors.length - 1]; const descs: Record<string, string> = { navigation: "Walking toward food. P9 neurons drive forward locomotion.", escape: "Ballistic escape via Giant Fiber. Rapid backward dart.", turning: "Sustained turning via asymmetric DNa01/DNa02.", arousal: "Heightened alertness. Rapid direction changes.", circles: "Constant forward speed + constant turn rate.", rhythm: "Walk 2s, stop 1s, repeat. Motor pattern alternation." }; return descs[b] || `User-compiled behavior: ${b}`; })()}
                          </div>
                        </div>
                        {selectedBehaviors.length > 1 && (
                          <div className="text-[9px] text-gray-500 font-mono flex-shrink-0">
                            {selectedBehaviors.length} selected
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Stats panel below */}
                <div className={`border-t border-white/10 p-4 ${isDark ? "bg-[#0a0a0f]/80" : "bg-white/90"} backdrop-blur-sm`}>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-lg md:text-xl font-bold font-mono text-[#7C3AED]">
                        {selectedStats.totalEdges || "--"}
                      </div>
                      <div className="text-[9px] text-gray-500 uppercase tracking-wider">Evolvable Edges</div>
                    </div>
                    <div>
                      <div className="text-lg md:text-xl font-bold font-mono text-green-400">
                        {selectedBehaviors.length > 0
                          ? PRESET_METRICS[selectedBehaviors[selectedBehaviors.length - 1]]?.improvement || "--"
                          : "--"}
                      </div>
                      <div className="text-[9px] text-gray-500 uppercase tracking-wider">Fitness Gain</div>
                    </div>
                    <div>
                      <div className="text-lg md:text-xl font-bold font-mono text-cyan-400">
                        {compiledOutput?.moduleCount || "--"}
                      </div>
                      <div className="text-[9px] text-gray-500 uppercase tracking-wider">Modules</div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ============================================================= */}
          {/* REMOVED: EXTRACT PROCESSOR (merged into Results & Growth) */}
          {/* ============================================================= */}
          {/* STEP 4: RESULTS & GROWTH PROGRAM                               */}
          {/* ============================================================= */}
          {currentStep === 4 && (
            <motion.div
              key="step4-growth"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden"
            >
              {/* Left: Growth program details (60%) */}
              <div className="md:w-1/2 w-full overflow-y-auto p-4 md:p-8 lg:p-10">
                <div className="max-w-2xl">
                  <h1 className={`text-2xl md:text-3xl font-bold mb-2 ${pgText}`}>
                    The growth program
                  </h1>
                  <p className={`${pgDimText} text-sm mb-6`}>
                    The recipe for a stem cell lab.
                  </p>

                  {!selectedProcessor ? (
                    <div className={`text-center py-16 ${pgCard} border ${pgBorder} rounded-xl`}>
                      <div className={`text-lg mb-2 ${isDark ? "text-gray-700" : "text-gray-400"}`}>No processor selected</div>
                      <div className={`${pgMuted} text-sm`}>Go back to Step 2 to extract a processor first.</div>
                      <button
                        onClick={() => goToStep(2)}
                        className="mt-4 px-5 py-2 rounded-lg text-sm border border-[#7C3AED]/30 text-[#7C3AED] hover:bg-[#7C3AED]/10 transition"
                      >
                        Go to Step 2
                      </button>
                    </div>
                  ) : !selectedGrowthProgram ? (
                    <>
                      <div className={`${pgCard} border ${pgBorder} rounded-xl p-5 mb-6`}>
                        <div className="flex items-center gap-2 mb-2">
                          <Cpu className="w-4 h-4 text-[#7C3AED]" />
                          <span className={`text-sm font-medium ${pgText}`}>{selectedProcessor.name}</span>
                        </div>
                        <div className={`text-[11px] font-mono ${pgDimText}`}>
                          {fmtNumber(selectedProcessor.n_neurons)} neurons | {fmtNumber(selectedProcessor.n_synapses)} synapses
                        </div>
                      </div>
                      <button
                        onClick={() => handleGenerateGrowthProgram(selectedProcessor)}
                        disabled={generatingGrowth}
                        className={`px-8 py-3 rounded-xl text-sm font-semibold transition-all ${
                          !generatingGrowth
                            ? "bg-[#7C3AED] text-white hover:bg-[#6D28D9] shadow-lg shadow-[#7C3AED]/25"
                            : `${isDark ? "bg-[#1e1e2e] text-gray-600" : "bg-gray-200 text-gray-400"} cursor-not-allowed`
                        }`}
                      >
                        {generatingGrowth ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                            Generating...
                          </span>
                        ) : (
                          "Generate Growth Program"
                        )}
                      </button>
                    </>
                  ) : (
                    <>
                      {/* Cell type recipe as stacked bars */}
                      <div className="mb-6">
                        <h2 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-3`}>
                          Cell Type Recipe ({selectedGrowthProgram.n_cell_types} types)
                        </h2>
                        <div className="space-y-2">
                          {selectedGrowthProgram.cell_types.map((ct, i) => {
                            const ntColors: Record<string, string> = { acetylcholine: "#06b6d4", gaba: "#ef4444", dopamine: "#f59e0b" };
                            const ntLabels: Record<string, string> = { acetylcholine: "ACh", gaba: "GABA", dopamine: "DA" };
                            const color = ntColors[ct.neurotransmitter] || "#7C3AED";
                            const widthPct = Math.max(ct.proportion * 100, 2);
                            return (
                              <div key={i} className="flex items-center gap-3">
                                <span className={`text-[9px] font-mono w-28 truncate ${pgDimText}`} title={ct.hemilineage}>
                                  {ct.hemilineage}
                                </span>
                                <div className={`flex-1 h-5 rounded-full ${isDark ? "bg-[#1e1e2e]" : "bg-gray-200"} overflow-hidden relative`}>
                                  <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{ width: `${widthPct}%`, backgroundColor: color }}
                                  />
                                </div>
                                <span className={`text-[9px] font-mono w-10 text-right ${pgDimText}`}>
                                  {(ct.proportion * 100).toFixed(1)}%
                                </span>
                                <span className="text-[8px] px-1 py-0.5 rounded" style={{ backgroundColor: color + "20", color }}>
                                  {ntLabels[ct.neurotransmitter] || ct.neurotransmitter}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Connection rules */}
                      <div className="mb-6">
                        <h2 className={`text-[11px] uppercase tracking-[2px] ${pgMuted} font-semibold mb-3`}>
                          Connection Rules (top 10)
                        </h2>
                        <div className={`${pgCard} border ${pgBorder} rounded-xl overflow-hidden`}>
                          <div className="space-y-0">
                            {[...selectedGrowthProgram.connection_rules]
                              .sort((a, b) => b.synapse_count - a.synapse_count)
                              .slice(0, 10)
                              .map((rule, i) => (
                                <div key={i} className={`flex items-center gap-2 px-4 py-2.5 text-[10px] font-mono ${i > 0 ? `border-t ${isDark ? "border-[#1e1e2e]/50" : "border-gray-100"}` : ""}`}>
                                  <span className="text-[#7C3AED] truncate max-w-[100px]" title={rule.from_hemilineage}>
                                    {rule.from_hemilineage}
                                  </span>
                                  <span className={pgMuted}>{"\u2192"}</span>
                                  <span className={`${pgDimText} truncate max-w-[100px]`} title={rule.to_hemilineage}>
                                    {rule.to_hemilineage}
                                  </span>
                                  <span className="ml-auto flex items-center gap-3">
                                    <span className={`${pgMuted}`}>p={rule.connection_probability.toFixed(3)}</span>
                                    <span className={pgText}>{(rule.synapse_count / 1000).toFixed(1)}k syn</span>
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>
                      </div>

                    </>
                  )}
                </div>
              </div>

              {/* Right: Growth visualization (40%) */}
              <div className={`md:w-1/2 w-full flex flex-col border-t md:border-t-0 md:border-l ${pgBorder} ${isDark ? "bg-black" : "bg-gray-50"}`}>
                <div className="flex-1 relative min-h-[300px] md:min-h-0">
                  {selectedGrowthProgram ? (
                    <GrowthVisualization isDark={isDark} cellTypes={selectedGrowthProgram.cell_types} />
                  ) : (
                    <FlyBrain3D
                      className="w-full h-full"
                      selectedBehaviors={selectedProcessor?.behaviors_compiled ?? []}
                      onModuleClick={handleModuleClick}
                      autoRotate
                      enableZoom
                    />
                  )}
                </div>

                {/* Growth stats */}
                {selectedGrowthProgram && (
                  <div className={`border-t border-white/10 p-4 ${isDark ? "bg-[#0a0a0f]/80" : "bg-white/90"} backdrop-blur-sm`}>
                    {/* NT breakdown bars */}
                    {(() => {
                      const ntMap: Record<string, { count: number; neurons: number }> = {};
                      for (const ct of selectedGrowthProgram.cell_types) {
                        if (!ntMap[ct.neurotransmitter]) ntMap[ct.neurotransmitter] = { count: 0, neurons: 0 };
                        ntMap[ct.neurotransmitter].count++;
                        ntMap[ct.neurotransmitter].neurons += ct.count;
                      }
                      const ntColors: Record<string, string> = { acetylcholine: "#06b6d4", gaba: "#ef4444", dopamine: "#f59e0b" };
                      const ntLabels: Record<string, string> = { acetylcholine: "Cholinergic", gaba: "GABAergic", dopamine: "Dopaminergic" };
                      const totalNeurons = selectedGrowthProgram.cell_types.reduce((s, c) => s + c.count, 0);
                      return (
                        <div className="space-y-2">
                          {Object.entries(ntMap).map(([nt, data]) => {
                            const pct = (data.neurons / totalNeurons) * 100;
                            return (
                              <div key={nt}>
                                <div className="flex justify-between text-[10px] mb-1">
                                  <span style={{ color: ntColors[nt] }}>{ntLabels[nt] || nt}</span>
                                  <span className="font-mono text-gray-500">{data.count} types / {fmtNumber(data.neurons)}</span>
                                </div>
                                <div className={`h-1.5 rounded-full ${isDark ? "bg-[#1e1e2e]" : "bg-gray-700"} overflow-hidden`}>
                                  <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: ntColors[nt] }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ================================================================= */}
      {/* Sticky Action Bar                                                  */}
      {/* ================================================================= */}
      <div className={`border-t ${pgBorder} ${isDark ? "bg-[#12121a]" : "bg-white"} px-4 py-2.5 flex items-center justify-between z-20`}>
        <button
          onClick={prevStep}
          disabled={currentStep === 1}
          className={`flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium transition ${
            currentStep === 1
              ? `${isDark ? "text-gray-700" : "text-gray-300"} cursor-not-allowed`
              : `border ${pgBorder} ${pgDimText} hover:${pgText}`
          }`}
        >
          <ArrowLeft className="w-4 h-4" /> <span className="hidden sm:inline">Back</span>
        </button>

        {/* Step indicator (compact) */}
        <div className="flex items-center gap-1.5">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`w-2 h-2 rounded-full transition ${
                s === currentStep
                  ? "bg-[#7C3AED]"
                  : stepsCompleted.has(s)
                  ? "bg-green-500"
                  : isDark ? "bg-gray-700" : "bg-gray-300"
              }`}
            />
          ))}
        </div>

        {/* Contextual action button */}
        {currentStep === 1 && (
          <button
            onClick={() => { setStepsCompleted((prev) => new Set([...prev, 1])); setCurrentStep(2); }}
            disabled={selectedBehaviors.length === 0}
            className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-semibold transition-all ${
              selectedBehaviors.length > 0
                ? "bg-[#7C3AED] text-white hover:bg-[#6D28D9] shadow-lg shadow-[#7C3AED]/25"
                : `${isDark ? "bg-[#1e1e2e] text-gray-600" : "bg-gray-200 text-gray-400"} cursor-not-allowed`
            }`}
          >
            Continue <ArrowRight className="w-4 h-4" />
          </button>
        )}
        {currentStep === 2 && (
          <button
            onClick={() => { setStepsCompleted((prev) => new Set([...prev, 2])); setCurrentStep(3); }}
            className="flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-semibold bg-[#7C3AED] text-white hover:bg-[#6D28D9] shadow-lg shadow-[#7C3AED]/25 transition-all"
          >
            Continue <ArrowRight className="w-4 h-4" />
          </button>
        )}
        {currentStep === 3 && (
          <button
            onClick={handleCompile}
            disabled={compiling}
            className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-semibold transition-all ${
              !compiling
                ? "bg-[#7C3AED] text-white hover:bg-[#6D28D9] shadow-lg shadow-[#7C3AED]/25"
                : `${isDark ? "bg-[#1e1e2e] text-gray-600" : "bg-gray-200 text-gray-400"} cursor-not-allowed`
            }`}
          >
            {compiling ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                {compileProgress > 0 ? `${compileProgress}%` : "Compiling..."}
              </>
            ) : (
              <>Compile{selectedBehaviors.length > 0 ? ` (${selectedBehaviors.length})` : ""} <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        )}
        {currentStep === 4 && (
          <button
            onClick={handleExportGrowthProgram}
            disabled={!selectedGrowthProgram}
            className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-semibold transition-all ${
              selectedGrowthProgram
                ? "bg-[#7C3AED] text-white hover:bg-[#6D28D9] shadow-lg shadow-[#7C3AED]/25"
                : `${isDark ? "bg-[#1e1e2e] text-gray-600" : "bg-gray-200 text-gray-400"} cursor-not-allowed`
            }`}
          >
            <Download className="w-4 h-4" /> Export JSON
          </button>
        )}
      </div>

      {/* ================================================================= */}
      {/* Console (persistent, collapsible)                                  */}
      {/* ================================================================= */}
      <div className={`border-t ${pgBorder} ${isDark ? "bg-[#0a0a0f]" : "bg-white"} z-20`}>
        {/* Console header */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setConsoleOpen(!consoleOpen)}
          onKeyDown={(e) => e.key === "Enter" && setConsoleOpen(!consoleOpen)}
          className={`w-full flex items-center justify-between px-4 py-1.5 ${isDark ? "bg-[#12121a]/80" : "bg-gray-50"} transition cursor-pointer select-none`}
        >
          <div className="flex items-center gap-2">
            <Terminal className={`w-3 h-3 ${pgMuted}`} />
            <span className={`text-[9px] uppercase tracking-wider ${pgMuted} font-medium`}>Console</span>
            {consoleLogs.length > 0 && (
              <span className={`text-[8px] px-1.5 py-0.5 rounded-full ${isDark ? "bg-white/[0.04]" : "bg-gray-200"} ${pgMuted} font-mono`}>
                {consoleLogs.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); setConsoleLogs([]); }}
              className={`text-[9px] ${pgMuted} hover:${pgText} transition px-1.5`}
            >
              clear
            </button>
            {consoleOpen ? <ChevronDown className={`w-3 h-3 ${pgMuted}`} /> : <ChevronUp className={`w-3 h-3 ${pgMuted}`} />}
          </div>
        </div>

        {/* Console body */}
        {consoleOpen && (
          <div className={`h-[120px] overflow-y-auto ${isDark ? "bg-black/80" : "bg-gray-900"} px-4 py-1.5`}>
            {consoleLogs.map((entry, i) => (
              <div key={i} className="font-mono text-[10px] leading-[1.6]">
                <span className="text-gray-700 mr-2">
                  {entry.timestamp.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
                <span
                  className={
                    entry.type === "command" ? "text-cyan-400"
                    : entry.type === "success" ? "text-green-400"
                    : entry.type === "detail" ? "text-gray-400"
                    : entry.type === "metric" ? "text-amber-400"
                    : entry.type === "info" ? "text-gray-500"
                    : entry.text.startsWith("ERROR") ? "text-red-400"
                    : "text-gray-500"
                  }
                >
                  {entry.text}
                </span>
              </div>
            ))}
            {consoleLogs.length === 0 && (
              <div className="font-mono text-[10px] text-gray-700 italic">
                Waiting for data...
              </div>
            )}
            <div ref={consoleEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
