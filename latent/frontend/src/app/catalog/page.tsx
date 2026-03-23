"use client";

import { useState, useEffect, useMemo, Fragment, useCallback } from "react";

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
import { motion, AnimatePresence } from "framer-motion";
import { Search, ChevronUp, ChevronDown, ChevronRight, Play, Zap } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { fetchModules, fetchThreeLayerMap, fetchFitnessFunctions, fetchCatalog } from "@/lib/api";
import { ARCHITECTURES, ARCHITECTURE_CATEGORIES } from "@/lib/architecture-data";
import type { CatalogData } from "@/lib/api";
import type { CompileModule, ThreeLayerMap, FitnessFunction } from "@/types/compile";
import { ROLE_COLORS } from "@/types/compile";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortKey = "id" | "role" | "n_neurons" | "top_super_class" | "top_nt" | "top_group";
type SortDir = "asc" | "desc";
type RoleFilter = "all" | "source" | "sink" | "intermediary" | "core";

const ROLE_FILTERS: RoleFilter[] = ["all", "source", "sink", "intermediary", "core"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function RoleBadge({ role }: { role: string }) {
  const color = ROLE_COLORS[role] ?? "#6b7280";
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}44` }}
    >
      {role}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CatalogPage() {
  const { theme, mode, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Data
  const [modules, setModules] = useState<CompileModule[]>([]);
  const [threeLayer, setThreeLayer] = useState<ThreeLayerMap | null>(null);
  const [fitnessFns, setFitnessFns] = useState<FitnessFunction[]>([]);
  const [catalogData, setCatalogData] = useState<CatalogData | null>(null);
  const [loading, setLoading] = useState(true);

  // Tab state
  const [activeTab, setActiveTab] = useState<"library" | "growth" | "architectures">("library");
  const [archCategoryFilter, setArchCategoryFilter] = useState<string>("all");
  const [behaviorFilter, setBehaviorFilter] = useState<"all" | "mine">("all");

  // UI state
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => { setMounted(true); }, []);

  const isDark = theme === "dark";
  const bg = isDark ? "bg-black" : "bg-white";
  const text = isDark ? "text-white" : "text-gray-900";
  const textMuted = isDark ? "text-gray-400" : "text-gray-600";
  const textSubtle = isDark ? "text-gray-500" : "text-gray-400";
  const border = isDark ? "border-white/10" : "border-gray-200";
  const cardBg = isDark ? "bg-white/[0.03]" : "bg-gray-50";

  // Fetch data on mount
  useEffect(() => {
    async function load() {
      try {
        const [mods, tlm, ffs] = await Promise.all([
          fetchModules(),
          fetchThreeLayerMap(),
          fetchFitnessFunctions(),
        ]);
        setModules(mods);
        setThreeLayer(tlm);
        setFitnessFns(ffs);

        // Try to fetch live catalog (includes community-compiled behaviors)
        try {
          const catalog = await fetchCatalog();
          setCatalogData(catalog);
        } catch {
          // API not available — catalog sections use hardcoded fallback
        }
      } catch (e) {
        console.error("Failed to load catalog data", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Derived: fitness participation map  moduleId -> function names
  const fitnessMap = useMemo(() => {
    const map = new Map<number, Set<string>>();
    for (const ff of fitnessFns) {
      for (const ep of ff.evolvable_pairs) {
        for (const mid of [ep.pre_module, ep.post_module]) {
          if (!map.has(mid)) map.set(mid, new Set());
          map.get(mid)!.add(ff.name);
        }
      }
    }
    return map;
  }, [fitnessFns]);

  // Derived: evolvable connections per module
  const connectionsMap = useMemo(() => {
    const map = new Map<number, { src: number; tgt: number; fn: string }[]>();
    for (const ff of fitnessFns) {
      for (const ep of ff.evolvable_pairs) {
        for (const mid of [ep.pre_module, ep.post_module]) {
          if (!map.has(mid)) map.set(mid, []);
          map.get(mid)!.push({ src: ep.pre_module, tgt: ep.post_module, fn: ff.name });
        }
      }
    }
    return map;
  }, [fitnessFns]);

  // Derived: OS / APP layer membership
  const layerMap = useMemo(() => {
    if (!threeLayer) return new Map<number, { os: boolean; app: string[] }>();
    const map = new Map<number, { os: boolean; app: string[] }>();

    const osModules = new Set<number>();
    for (const pair of threeLayer.os_layer) {
      osModules.add(pair.src);
      osModules.add(pair.tgt);
    }

    const appModules = new Map<number, Set<string>>();
    for (const [fnName, pairs] of Object.entries(threeLayer.app_layer)) {
      for (const pair of pairs) {
        for (const mid of [pair.src, pair.tgt]) {
          if (!appModules.has(mid)) appModules.set(mid, new Set());
          appModules.get(mid)!.add(fnName);
        }
      }
    }

    for (const mod of modules) {
      map.set(mod.id, {
        os: osModules.has(mod.id),
        app: Array.from(appModules.get(mod.id) ?? []),
      });
    }
    return map;
  }, [threeLayer, modules]);

  // Filter + sort
  const filtered = useMemo(() => {
    let list = modules;
    if (roleFilter !== "all") {
      list = list.filter((m) => m.role === roleFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (m) =>
          String(m.id).includes(q) ||
          m.role.toLowerCase().includes(q) ||
          m.top_super_class.toLowerCase().includes(q) ||
          m.top_nt.toLowerCase().includes(q) ||
          m.top_group.toLowerCase().includes(q)
      );
    }
    list = [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return list;
  }, [modules, roleFilter, search, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ChevronRight className="w-3 h-3 opacity-30" />;
    return sortDir === "asc" ? (
      <ChevronUp className="w-3 h-3" />
    ) : (
      <ChevronDown className="w-3 h-3" />
    );
  };

  // ---------------------------------------------------------------------------
  // Detail panel (expanded row)
  // ---------------------------------------------------------------------------

  function DetailPanel({ mod }: { mod: CompileModule }) {
    const fns = Array.from(fitnessMap.get(mod.id) ?? []);
    const conns = connectionsMap.get(mod.id) ?? [];
    const layer = layerMap.get(mod.id);
    // Deduplicate connections by src-tgt
    const uniqueConns = Array.from(
      new Map(conns.map((c) => [`${c.src}-${c.tgt}`, c])).values()
    );

    return (
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: "auto", opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        transition={{ duration: 0.25 }}
        className="overflow-hidden"
      >
        <div className="px-4 py-4 sm:px-6 bg-white/[0.02] border-t border-white/5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
            {/* Fitness functions */}
            <div>
              <h4 className="text-gray-400 font-medium mb-2">Fitness Functions</h4>
              {fns.length === 0 ? (
                <p className="text-gray-600">None</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {fns.map((f) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 text-xs border border-purple-500/20"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Evolvable connections */}
            <div>
              <h4 className="text-gray-400 font-medium mb-2">
                Evolvable Connections ({uniqueConns.length})
              </h4>
              {uniqueConns.length === 0 ? (
                <p className="text-gray-600">None</p>
              ) : (
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {uniqueConns.slice(0, 10).map((c) => (
                    <div key={`${c.src}-${c.tgt}`} className="text-gray-500 text-xs font-mono">
                      {c.src} &rarr; {c.tgt}{" "}
                      <span className="text-gray-600">({c.fn})</span>
                    </div>
                  ))}
                  {uniqueConns.length > 10 && (
                    <p className="text-gray-600 text-xs">
                      +{uniqueConns.length - 10} more
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Layer membership */}
            <div>
              <h4 className="text-gray-400 font-medium mb-2">Layer Membership</h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${layer?.os ? "bg-cyan-400" : "bg-gray-700"}`}
                  />
                  <span className={layer?.os ? "text-cyan-400" : "text-gray-600"}>
                    OS Layer {layer?.os ? "(shared core)" : "(not in OS)"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      layer?.app && layer.app.length > 0 ? "bg-purple-400" : "bg-gray-700"
                    }`}
                  />
                  <span
                    className={
                      layer?.app && layer.app.length > 0 ? "text-purple-400" : "text-gray-600"
                    }
                  >
                    APP Layer{" "}
                    {layer?.app && layer.app.length > 0
                      ? `(${layer.app.join(", ")})`
                      : "(not in APP)"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const columns: { key: SortKey; label: string; hideOnMobile?: boolean }[] = [
    { key: "id", label: "ID" },
    { key: "role", label: "Role" },
    { key: "n_neurons", label: "Neurons" },
    { key: "top_super_class", label: "Cell Type", hideOnMobile: true },
    { key: "top_nt", label: "Neurotransmitter", hideOnMobile: true },
    { key: "top_group", label: "Brain Region", hideOnMobile: true },
  ];

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
      <section className="pt-32 pb-4 px-4 sm:px-8 max-w-7xl mx-auto">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">Catalog</h1>
        <p className={`${textMuted} text-lg max-w-2xl mb-6`}>
          Everything Compile has designed. 22 results plus 1 partial (attention) across 2 species -- cognitive capabilities, reactive behaviors, processors, and growth programs.
        </p>

        {/* Tab Toggle */}
        <div className="flex gap-1 mb-8">
          <button
            onClick={() => setActiveTab("library")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "library"
                ? `bg-purple-500/20 text-purple-400 border border-purple-500/30`
                : `${isDark ? "text-gray-400 hover:text-white hover:bg-white/5" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"} border ${border}`
            }`}
          >
            Circuit Library
          </button>
          <button
            onClick={() => setActiveTab("growth")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "growth"
                ? `bg-purple-500/20 text-purple-400 border border-purple-500/30`
                : `${isDark ? "text-gray-400 hover:text-white hover:bg-white/5" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"} border ${border}`
            }`}
          >
            Growth Programs
          </button>
          <button
            onClick={() => setActiveTab("architectures")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "architectures"
                ? `bg-purple-500/20 text-purple-400 border border-purple-500/30`
                : `${isDark ? "text-gray-400 hover:text-white hover:bg-white/5" : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"} border ${border}`
            }`}
          >
            Architectures
          </button>
        </div>
      </section>

      {/* TAB 3: Architectures */}
      {activeTab === "architectures" && (
        <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5 mb-6">
            <button
              onClick={() => setArchCategoryFilter("all")}
              className={`text-xs px-3 py-1 rounded-full transition ${
                archCategoryFilter === "all"
                  ? "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                  : `${textSubtle} border ${border}`
              }`}
            >
              All ({ARCHITECTURES.length})
            </button>
            {ARCHITECTURE_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setArchCategoryFilter(cat.id)}
                className={`text-xs px-3 py-1 rounded-full transition ${
                  archCategoryFilter === cat.id
                    ? "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                    : `${textSubtle} border ${border}`
                }`}
              >
                {cat.label} ({ARCHITECTURES.filter((a) => a.category === cat.id).length})
              </button>
            ))}
          </div>

          {/* Architecture cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {ARCHITECTURES
              .filter((a) => archCategoryFilter === "all" || a.category === archCategoryFilter)
              .map((arch) => (
                <motion.div
                  key={arch.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`${cardBg} border ${border} rounded-xl p-5 hover:border-purple-500/30 transition-all`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium text-sm text-purple-400">{arch.name}</span>
                  </div>
                  <p className={`text-[11px] ${textMuted} leading-relaxed mb-3`}>{arch.description}</p>
                  <div className={`flex items-center gap-3 text-[10px] font-mono ${textSubtle} mb-3`}>
                    <span>{arch.cellTypeCount} types</span>
                    <span>{arch.connectionRuleCount} rules</span>
                    <span>{arch.totalNeurons.toLocaleString()} neurons</span>
                  </div>
                  {arch.tradeoffs.length > 0 && (
                    <div className="space-y-1 mb-3">
                      {arch.tradeoffs.slice(0, 3).map((t, i) => (
                        <div key={i} className={`text-[10px] ${textSubtle}`}>· {t}</div>
                      ))}
                    </div>
                  )}
                  {arch.bestFor.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {arch.bestFor.map((b, i) => (
                        <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">{b}</span>
                      ))}
                    </div>
                  )}
                  <Link
                    href="/playground"
                    className="block mt-3 text-[10px] text-purple-400 hover:text-purple-300 transition"
                  >
                    Try in playground →
                  </Link>
                </motion.div>
              ))}
          </div>

          {/* Composability note */}
          <div className={`${cardBg} border ${border} rounded-xl p-5`}>
            <h3 className={`text-sm font-medium ${text} mb-2`}>Composable</h3>
            <p className={`text-[11px] ${textMuted} leading-relaxed`}>
              Architectures can be combined. Each occupies a spatial region with its own cell types and connection rules. Inter-architecture interfaces are additional connection rules in the growth program. The human brain uses 10+ architectures simultaneously — the cerebellum is sparse distributed memory, the basal ganglia is a priority queue, the cortex uses predictive coding with hierarchical hubs.
            </p>
          </div>
        </section>
      )}

      {/* TAB 1: Circuit Library */}
      {activeTab === "library" && (
        <>
          {/* Behavior filter: All / My Behaviors */}
          {catalogData && catalogData.behaviors.some((b) => b.is_mine) && (
            <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-6">
              <div className="flex gap-2">
                {(["all", "mine"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setBehaviorFilter(f)}
                    className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
                      behaviorFilter === f
                        ? `${isDark ? "bg-purple-500/15 text-purple-400 border border-purple-500/30" : "bg-purple-50 text-purple-600 border border-purple-300"}`
                        : `${isDark ? "text-gray-400 hover:text-white" : "text-gray-500 hover:text-gray-900"} border ${border}`
                    }`}
                  >
                    {f === "all" ? "All Behaviors" : "My Behaviors"}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* My Behaviors section (when filtered) */}
          {behaviorFilter === "mine" && catalogData && (
            <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
              <div className="flex items-center gap-3 mb-5">
                <Zap className="w-4 h-4 text-purple-400" />
                <h2 className="text-lg font-semibold">My Compiled Behaviors</h2>
              </div>
              {(() => {
                const mine = catalogData.behaviors.filter((b) => b.is_mine);
                if (mine.length === 0) return (
                  <p className={`${textMuted} text-sm`}>You haven&apos;t compiled any behaviors yet. Use the playground to compile your first custom behavior.</p>
                );
                return (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {mine.map((b) => (
                      <motion.div
                        key={b.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`${cardBg} border ${border} rounded-xl p-4 hover:border-purple-500/30 transition-all`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-2 h-2 rounded-full bg-purple-500" />
                          <span className="font-medium text-sm text-purple-400">{b.label}</span>
                        </div>
                        <p className={`text-[11px] ${textMuted} leading-relaxed mb-2`}>{b.description}</p>
                        <div className={`text-[10px] ${textSubtle}`}>{b.improvement} · {b.edges} edges · {b.capability_family || "reactive"}</div>
                      </motion.div>
                    ))}
                  </div>
                );
              })()}
            </section>
          )}

          {/* Sections 1-2 + Community (shown when filter is "all") */}
          {behaviorFilter === "all" && (<>

          {/* Behaviors organized by computational requirement */}
          {[
            { tag: "speed", label: "Speed", icon: "text-cyan-400", behaviors: [
              { id: 'navigation', label: 'Navigation', desc: 'Forward locomotion toward food via P9 motor neurons.', color: '#06b6d4', metric: '+100%' },
              { id: 'escape', label: 'Escape', desc: 'Ballistic escape via Giant Fiber pathway.', color: '#ef4444', metric: '+8.6%' },
              { id: 'turning', label: 'Turning', desc: 'Sustained turning via asymmetric DNa01/DNa02.', color: '#22c55e', metric: '+25%' },
              { id: 'arousal', label: 'Arousal', desc: 'Sensory gain control through visual module gating.', color: '#f59e0b', metric: '+60%' },
            ]},
            { tag: "persistence", label: "Persistence", icon: "text-purple-400", behaviors: [
              { id: 'working-memory', label: 'Working Memory', desc: 'Holds representation for 500 timesteps with no input. 3.8x navigation bias from memory trace.', color: '#a855f7', metric: '+29%' },
            ]},
            { tag: "competition", label: "Competition", icon: "text-pink-400", behaviors: [
              { id: 'conflict-resolution', label: 'Conflict Resolution', desc: '96% conflict coexistence — competing behaviors resolve through DN hub architecture.', color: '#ec4899', metric: '+153%' },
            ]},
            { tag: "rhythm", label: "Rhythm", icon: "text-emerald-400", behaviors: [
              { id: 'circles', label: 'Circular Locomotion', desc: 'Sustained circular walking. 3 novel connections.', color: '#10b981', metric: '+86%' },
              { id: 'rhythm', label: 'Rhythmic Alternation', desc: 'Walk 2s, stop 1s, repeat. 6 novel connections.', color: '#8b5cf6', metric: '+87%' },
            ]},
            { tag: "gating", label: "Gating", icon: "text-orange-400", behaviors: [
              { id: 'attention', label: 'Attention (weak)', desc: 'Compiled weakly. Laterality 0.32. Uses different circuitry — selective gating family.', color: '#f97316', metric: 'partial' },
            ]},
          ].map((group) => (
          <section key={group.tag} className="px-4 sm:px-8 max-w-7xl mx-auto mb-8">
            <div className="flex items-center gap-3 mb-4">
              <Zap className={`w-4 h-4 ${group.icon}`} />
              <h2 className="text-lg font-semibold">{group.label}</h2>
              <span className={`text-xs ${textSubtle}`}>— {group.tag === "speed" ? "fast sensory-to-motor" : group.tag === "persistence" ? "sustained internal state" : group.tag === "competition" ? "choosing between inputs" : group.tag === "rhythm" ? "temporal patterns" : "selective amplification"}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {group.behaviors.map((b) => (
                <motion.div
                  key={b.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`${cardBg} border ${border} rounded-xl p-4 hover:border-purple-500/30 transition-all`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: b.color }} />
                    <span className="font-medium text-sm" style={{ color: b.color }}>{b.label}</span>
                    <span className={`ml-auto text-xs font-mono ${b.metric === "partial" ? "text-amber-400" : "text-green-400"}`}>{b.metric}</span>
                  </div>
                  <p className={`text-[11px] ${textMuted} leading-relaxed`}>{b.desc}</p>
                </motion.div>
              ))}
            </div>
          </section>
          ))}

          {/* Community-compiled behaviors (from live API) */}
          {catalogData && catalogData.behaviors.filter((b) => !b.is_precomputed).length > 0 && (
            <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
              <div className="flex items-center gap-3 mb-5">
                <Zap className="w-4 h-4 text-purple-400" />
                <h2 className="text-lg font-semibold">Community Compiled</h2>
                <span className={`text-xs px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 font-medium`}>
                  {catalogData.behaviors.filter((b) => !b.is_precomputed).length} behaviors
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {catalogData.behaviors.filter((b) => !b.is_precomputed).map((b) => (
                  <motion.div
                    key={b.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`${cardBg} border ${border} rounded-xl p-4 hover:border-purple-500/30 transition-all`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 rounded-full bg-purple-500" />
                      <span className="font-medium text-sm text-purple-400">{b.label}</span>
                      <span className="text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">USER</span>
                    </div>
                    <p className={`text-[11px] ${textMuted} leading-relaxed mb-2`}>{b.description}</p>
                    <div className={`text-[10px] ${textSubtle}`}>{b.improvement} · {b.edges} edges</div>
                  </motion.div>
                ))}
              </div>
            </section>
          )}
          </>)}

          {/* Section 3: Composability & Interference */}
          <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
            <div className="flex items-center gap-3 mb-3">
              <Zap className="w-4 h-4 text-amber-400" />
              <h2 className="text-lg font-semibold">Composability</h2>
            </div>
            <p className={`text-sm ${textMuted} leading-relaxed mb-5 max-w-3xl`}>
              Behaviors compose onto the same processor like programs onto hardware. 9 out of 10 pairs coexist without interference. When behaviors compete, the interference matrix shows exactly which pairs conflict and by how much. Conflict resolution handles competing internal states through the DN hub architecture (modules 4 and 19).
            </p>

            {/* Interference matrix */}
            <div className={`${cardBg} border ${border} rounded-xl p-5 mb-6`}>
              <h3 className={`text-sm font-medium ${text} mb-3`}>Interference Matrix</h3>
              <p className={`text-[11px] ${textSubtle} mb-4`}>
                Each cell shows how compiling the row behavior affects the column behavior. Green = synergy or neutral. Red = conflict.
              </p>
              <div className="overflow-x-auto">
                {(() => {
                  // Build matrix from catalog data if available, otherwise use hardcoded fallback
                  const fallbackRows = [
                    { name: "navigation", vals: [100, 58, 0, 5, 3, 0] },
                    { name: "escape",     vals: [2, 100, 0, 0, 0, 0] },
                    { name: "turning",    vals: [0, 0, 100, 0, 5, 0] },
                    { name: "arousal",    vals: [8, 3, 0, 100, 0, 0] },
                    { name: "circles",    vals: [5, -41, 10, 0, 100, 0] },
                    { name: "rhythm",     vals: [0, 0, 0, 0, 0, 100] },
                  ];
                  const fallbackNames = fallbackRows.map((r) => r.name);

                  // Use catalog interference data if available
                  const interference = catalogData?.interference;
                  let behaviorNames: string[];
                  let getCell: (compiled: string, tested: string) => number;

                  if (interference && interference.length > 0) {
                    const nameSet = new Set<string>();
                    for (const e of interference) { nameSet.add(e.compiled); nameSet.add(e.tested); }
                    behaviorNames = Array.from(nameSet);
                    getCell = (compiled, tested) => {
                      if (compiled === tested) return 100;
                      const entry = interference.find((e) => e.compiled === compiled && e.tested === tested);
                      return entry?.delta_pct ?? 0;
                    };
                  } else {
                    behaviorNames = fallbackNames;
                    getCell = (compiled, tested) => {
                      if (compiled === tested) return 100;
                      const ri = fallbackNames.indexOf(compiled);
                      const ci = fallbackNames.indexOf(tested);
                      if (ri < 0 || ci < 0) return 0;
                      return fallbackRows[ri].vals[ci];
                    };
                  }

                  return (
                    <table className="w-full text-[11px] font-mono">
                      <thead>
                        <tr>
                          <th className={`text-left ${textSubtle} pb-2 pr-4`}>compiled &#x2193; tested &#x2192;</th>
                          {behaviorNames.map((b) => (
                            <th key={b} className={`text-center ${textSubtle} pb-2 px-2`}>{b.slice(0, 4)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {behaviorNames.map((row) => (
                          <tr key={row} className={`border-t ${border}`}>
                            <td className={`${textMuted} pr-4 py-2 capitalize`}>{row}</td>
                            {behaviorNames.map((col) => {
                              const v = getCell(row, col);
                              const isDiag = row === col;
                              const color = isDiag ? "text-purple-400 font-bold" : v > 10 ? "text-green-400" : v < -10 ? "text-red-400" : textSubtle;
                              return (
                                <td key={col} className={`text-center px-2 py-2 ${color}`}>
                                  {isDiag ? "\u2014" : `${v > 0 ? "+" : ""}${v}%`}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  );
                })()}
              </div>
              <div className={`text-[10px] ${textSubtle} mt-3 flex gap-4`}>
                <span><span className="text-purple-400">purple</span> = self</span>
                <span><span className="text-green-400">green</span> = synergy (&gt;10%)</span>
                <span><span className="text-red-400">red</span> = conflict (&lt;-10%)</span>
                <span>gray = neutral</span>
              </div>
            </div>

            {/* Capability families */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className={`${cardBg} border ${border} rounded-xl p-5`}>
                <h3 className="text-sm font-medium text-purple-400 mb-2">State Maintenance Family</h3>
                <p className={`text-[11px] ${textMuted} leading-relaxed mb-3`}>
                  Working memory and conflict resolution share 83% of their developmental cell types. 15 base hemilineages + 2-4 plugins per capability. Routes through DN hubs (modules 4 and 19).
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {["working memory", "conflict resolution"].map((b) => (
                    <span key={b} className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 capitalize">{b}</span>
                  ))}
                </div>
              </div>
              <div className={`${cardBg} border ${border} rounded-xl p-5`}>
                <h3 className="text-sm font-medium text-cyan-400 mb-2">Selective Gating Family</h3>
                <p className={`text-[11px] ${textMuted} leading-relaxed mb-3`}>
                  Attention uses different circuitry entirely — only 17% hemilineage overlap with state maintenance. Compiled weakly in the fly (laterality 0.32), which is biologically correct. Separate architecture.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">attention (partial)</span>
                </div>
              </div>
            </div>

            {/* Hub capacity */}
            <div className={`${cardBg} border ${border} rounded-xl p-5 mt-4`}>
              <h3 className={`text-sm font-medium ${text} mb-2`}>Capacity</h3>
              {catalogData?.hub_capacity ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${border} rounded-lg p-3 text-center`}>
                      <div className="text-lg font-light text-purple-400">{catalogData.hub_capacity.total_neurons.toLocaleString()}</div>
                      <div className={`text-[10px] ${textSubtle} uppercase`}>Total Neurons</div>
                    </div>
                    <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${border} rounded-lg p-3 text-center`}>
                      <div className="text-lg font-light text-purple-400">{catalogData.hub_capacity.behaviors_compiled}</div>
                      <div className={`text-[10px] ${textSubtle} uppercase`}>Behaviors</div>
                    </div>
                    <div className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${border} rounded-lg p-3 text-center`}>
                      <div className="text-lg font-light text-purple-400">{catalogData.hub_capacity.capability_families}</div>
                      <div className={`text-[10px] ${textSubtle} uppercase`}>Families</div>
                    </div>
                  </div>
                  <p className={`text-[11px] ${textMuted} leading-relaxed`}>
                    Capacity is determined by hub modules — the most shared nodes in the connectome. Behaviors that route through the same hubs compete for bandwidth. The interference matrix above shows which pairs conflict.
                  </p>
                </div>
              ) : (
                <p className={`text-[11px] ${textMuted} leading-relaxed`}>
                  The gene-guided processor supports multiple reactive behaviors simultaneously. Cognitive capabilities may require the full connectome. Hub modules that appear across many behaviors are the capacity bottleneck — the interference matrix shows which pairs compete.
                </p>
              )}
            </div>
          </section>

          {/* Section 4: Processor Designs */}
          <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
            <div className="flex items-center gap-3 mb-5">
              <Zap className="w-4 h-4 text-green-400" />
              <h2 className="text-lg font-semibold">Processors</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Gene-guided processor', desc: '8,158 neurons. 19 hemilineages. Supports 5/6 behaviors. 19x more active than the module-selected version.', color: '#a855f7' },
                { label: 'Module-selected processor', desc: '20,626 neurons. Supports 5/6 behaviors. Essential hubs at modules 4 and 19.', color: '#8b5cf6' },
                { label: 'Full brain', desc: '139,255 neurons. The complete FlyWire connectome. Required for cognitive capabilities.', color: '#06b6d4' },
                { label: 'Mouse V1 processor', desc: '18,522 neurons. 9 cell-type layers. 5 hub modules. Direction selectivity DSI=1.86.', color: '#22c55e' },
              ].map((b) => (
                <motion.div
                  key={b.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`${cardBg} border ${border} rounded-xl p-5 hover:border-purple-500/30 transition-all`}
                >
                  <span className="font-medium text-sm" style={{ color: b.color }}>{b.label}</span>
                  <p className={`text-[11px] ${textMuted} leading-relaxed mt-2`}>{b.desc}</p>
                </motion.div>
              ))}
            </div>
          </section>
        </>
      )}

      {/* TAB 2: Growth Programs */}
      {activeTab === "growth" && (
        <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-12">
          <div className="space-y-8">
            {/* Fly Processor Growth Program */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`${cardBg} border ${border} rounded-xl p-6`}
            >
              <div className="flex items-center gap-3 mb-4">
                <Zap className="w-4 h-4 text-amber-400" />
                <h2 className="text-lg font-semibold">Fly Processor Growth Program</h2>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                {[
                  { value: "19", label: "cell types" },
                  { value: "30", label: "connection rules" },
                  { value: "851", label: "sequential growth nav" },
                  { value: "1.45%", label: "physiological density" },
                ].map((stat) => (
                  <div key={stat.label} className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${border} rounded-lg p-3 text-center`}>
                    <div className="text-xl font-light text-purple-400 mb-1">{stat.value}</div>
                    <div className={`text-[10px] ${textSubtle} uppercase`}>{stat.label}</div>
                  </div>
                ))}
              </div>

              <p className={`text-sm ${textMuted} leading-relaxed mb-4`}>
                14 cholinergic, 2 GABAergic, 2 dopaminergic cell types. Sequential activity-dependent growth validated at physiological density (1.45%). Growth order: size-ordered hemilineages with activity-dependent bias. Nav score 851, beating FlyWire (577) and random (459). Growth ORDER is critical — random order produces 0. Two growth program families: state maintenance (working memory + conflict resolution, 15 base hemilineages + 2-4 plugins, 83% of input hemilineages shared) and selective gating (attention — partial/weak, separate circuitry, 17% overlap).
              </p>

              <h3 className={`text-sm font-medium ${text} mb-3`}>Cell Type Proportions</h3>
              <div className={`overflow-x-auto rounded-lg border ${border}`}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className={`${isDark ? "bg-white/5" : "bg-gray-50"}`}>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>Type</th>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>NT</th>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>Family</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? "divide-white/5" : "divide-gray-100"}`}>
                    {[
                      { type: "14 hemilineages", nt: "Cholinergic (excitatory)", family: "State maintenance" },
                      { type: "2 hemilineages", nt: "GABAergic (inhibitory)", family: "State maintenance" },
                      { type: "2 hemilineages", nt: "Dopaminergic (modulatory)", family: "State maintenance" },
                      { type: "1 hemilineage", nt: "Mixed", family: "Selective gating" },
                    ].map((row, i) => (
                      <tr key={i} className={`${isDark ? "hover:bg-white/[0.02]" : "hover:bg-gray-50"}`}>
                        <td className={`px-3 py-2 ${isDark ? "text-gray-300" : "text-gray-700"}`}>{row.type}</td>
                        <td className={`px-3 py-2 ${textMuted}`}>{row.nt}</td>
                        <td className={`px-3 py-2 ${textMuted}`}>{row.family}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>

            {/* Mouse V1 Growth Program */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className={`${cardBg} border ${border} rounded-xl p-6`}
            >
              <div className="flex items-center gap-3 mb-4">
                <Zap className="w-4 h-4 text-green-400" />
                <h2 className="text-lg font-semibold">Mouse V1 Growth Program</h2>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                {[
                  { value: "9", label: "cell-type layers" },
                  { value: "DSI=0.28", label: "bundle growth" },
                  { value: "5", label: "hub modules" },
                  { value: "33", label: "evolvable pairs" },
                ].map((stat) => (
                  <div key={stat.label} className={`${isDark ? "bg-white/[0.03]" : "bg-white"} border ${border} rounded-lg p-3 text-center`}>
                    <div className="text-xl font-light text-green-400 mb-1">{stat.value}</div>
                    <div className={`text-[10px] ${textSubtle} uppercase`}>{stat.label}</div>
                  </div>
                ))}
              </div>

              <p className={`text-sm ${textMuted} leading-relaxed mb-4`}>
                Hub modules: V1_L5, V1_L2/3, HVA_L2/3, HVA_L5, SST. VIP-to-SST disinhibition circuit validated experimentally. Bundle growth achieves DSI=0.28 for direction selectivity.
              </p>

              <h3 className={`text-sm font-medium ${text} mb-3`}>Cell-Type Layer Proportions</h3>
              <div className={`overflow-x-auto rounded-lg border ${border}`}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className={`${isDark ? "bg-white/5" : "bg-gray-50"}`}>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>Layer</th>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>Proportion</th>
                      <th className={`text-left px-3 py-2 text-xs ${textSubtle} uppercase`}>Role</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? "divide-white/5" : "divide-gray-100"}`}>
                    {[
                      { layer: "V1_L2/3", pct: "23.1%", role: "Hub / output relay" },
                      { layer: "PV", pct: "21.1%", role: "Inhibitory" },
                      { layer: "V1_L4", pct: "16.5%", role: "Input" },
                      { layer: "V1_L5", pct: "12.8%", role: "Hub / deep integrator" },
                      { layer: "HVA_L2/3", pct: "9.2%", role: "Hub" },
                      { layer: "HVA_L5", pct: "7.4%", role: "Hub" },
                      { layer: "SST", pct: "5.1%", role: "Hub / inhibitory" },
                      { layer: "VIP", pct: "3.2%", role: "Disinhibition" },
                      { layer: "V1_L6", pct: "1.6%", role: "Feedback" },
                    ].map((row, i) => (
                      <tr key={i} className={`${isDark ? "hover:bg-white/[0.02]" : "hover:bg-gray-50"}`}>
                        <td className={`px-3 py-2 font-mono text-sm ${isDark ? "text-gray-300" : "text-gray-700"}`}>{row.layer}</td>
                        <td className={`px-3 py-2 ${textMuted}`}>{row.pct}</td>
                        <td className={`px-3 py-2 ${textMuted}`}>{row.role}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </div>
        </section>
      )}

      {activeTab === "library" && (<>
      {/* Divider */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 mb-8">
        <div className={`h-px ${isDark ? "bg-white/[0.06]" : "bg-gray-200"}`} />
      </div>

      {/* Modules section header */}
      <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-4">
        <h2 className="text-lg font-semibold mb-1">Modules</h2>
        <p className={`${textSubtle} text-sm`}>50 functional modules clustered by connectivity, cell type, and brain region.</p>
      </section>

      {/* Filter bar */}
      <section className="px-4 sm:px-8 max-w-7xl mx-auto mb-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          {/* Role filters */}
          <div className="flex flex-wrap gap-2">
            {ROLE_FILTERS.map((r) => {
              const active = roleFilter === r;
              const color = r === "all" ? "#ffffff" : ROLE_COLORS[r] ?? "#6b7280";
              return (
                <button
                  key={r}
                  onClick={() => setRoleFilter(r)}
                  className="px-3 py-1.5 rounded-full text-xs font-medium transition-all"
                  style={{
                    backgroundColor: active ? `${color}22` : "transparent",
                    color: active ? color : "#9ca3af",
                    border: `1px solid ${active ? `${color}44` : "#374151"}`,
                  }}
                >
                  {r === "all" ? "All" : r.charAt(0).toUpperCase() + r.slice(1)}
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${textSubtle}`} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search modules..."
              className={`w-full pl-9 pr-4 py-2 rounded-lg ${cardBg} border ${border} text-sm ${text} placeholder-gray-500 focus:outline-none focus:border-purple-500/50 transition`}
            />
          </div>

          <span className={`${textSubtle} text-sm`}>{filtered.length} modules</span>
        </div>
      </section>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-20">
          <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Desktop table */}
      {!loading && (
        <section className="px-4 sm:px-8 max-w-7xl mx-auto pb-20">
          {/* Table (hidden on mobile) */}
          <div className={`hidden sm:block rounded-xl border ${border} overflow-hidden`}>
            <table className="w-full text-sm">
              <thead>
                <tr className={`border-b ${border} ${cardBg}`}>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className={`px-4 py-3 text-left font-medium ${textMuted} cursor-pointer hover:${text} transition select-none ${
                        col.hideOnMobile ? "hidden md:table-cell" : ""
                      }`}
                    >
                      <span className="inline-flex items-center gap-1">
                        {col.label}
                        <SortIcon col={col.key} />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((mod) => (
                  <Fragment key={mod.id}>
                    <tr
                      onClick={() => setExpandedId(expandedId === mod.id ? null : mod.id)}
                      className={`border-b ${isDark ? "border-white/5 hover:bg-white/[0.03]" : "border-gray-100 hover:bg-gray-50"} cursor-pointer transition`}
                    >
                      <td className={`px-4 py-3 font-mono ${isDark ? "text-gray-300" : "text-gray-700"}`}>{mod.id}</td>
                      <td className="px-4 py-3">
                        <RoleBadge role={mod.role} />
                      </td>
                      <td className={`px-4 py-3 ${isDark ? "text-gray-300" : "text-gray-700"}`}>
                        {mod.n_neurons.toLocaleString()}
                      </td>
                      <td className={`px-4 py-3 ${textMuted} hidden md:table-cell`}>
                        {mod.top_super_class}
                      </td>
                      <td className={`px-4 py-3 ${textMuted} hidden md:table-cell`}>
                        {mod.top_nt}
                      </td>
                      <td className={`px-4 py-3 ${textMuted} hidden md:table-cell`}>
                        {mod.top_group}
                      </td>
                    </tr>
                    <AnimatePresence>
                      {expandedId === mod.id && (
                        <tr>
                          <td colSpan={columns.length}>
                            <DetailPanel mod={mod} />
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </Fragment>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className={`px-4 py-12 text-center ${textSubtle}`}>
                      No modules match your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="sm:hidden space-y-3">
            {filtered.map((mod) => (
              <div key={mod.id} className={`rounded-xl border ${border} overflow-hidden`}>
                <button
                  onClick={() => setExpandedId(expandedId === mod.id ? null : mod.id)}
                  className={`w-full px-4 py-3 flex items-center justify-between ${isDark ? "hover:bg-white/[0.03]" : "hover:bg-gray-50"} transition text-left`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`font-mono ${isDark ? "text-gray-300" : "text-gray-700"} text-sm`}>#{mod.id}</span>
                    <RoleBadge role={mod.role} />
                  </div>
                  <div className={`flex items-center gap-3 text-sm ${textMuted}`}>
                    <span>{mod.n_neurons.toLocaleString()} neurons</span>
                    <ChevronRight
                      className={`w-4 h-4 transition-transform ${
                        expandedId === mod.id ? "rotate-90" : ""
                      }`}
                    />
                  </div>
                </button>

                {/* Card summary fields */}
                <div className="px-4 pb-3 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className={textSubtle}>Cell Type</span>
                    <p className={`${isDark ? "text-gray-300" : "text-gray-700"} truncate`}>{mod.top_super_class}</p>
                  </div>
                  <div>
                    <span className={textSubtle}>NT</span>
                    <p className={`${isDark ? "text-gray-300" : "text-gray-700"} truncate`}>{mod.top_nt}</p>
                  </div>
                  <div>
                    <span className={textSubtle}>Region</span>
                    <p className={`${isDark ? "text-gray-300" : "text-gray-700"} truncate`}>{mod.top_group}</p>
                  </div>
                </div>

                <AnimatePresence>
                  {expandedId === mod.id && <DetailPanel mod={mod} />}
                </AnimatePresence>
              </div>
            ))}
            {filtered.length === 0 && (
              <p className={`text-center ${textSubtle} py-12`}>No modules match your filters.</p>
            )}
          </div>
        </section>
      )}
      </>)}

      {/* Footer */}
      <footer className={`py-12 border-t ${border}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3 sm:gap-4">
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

