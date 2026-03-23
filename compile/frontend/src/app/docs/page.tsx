"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Book,
  Code,
  Zap,
  Copy,
  Check,
  Brain,
  Cpu,
  Play,
  Menu,
  X,
  Dna,
  Target,
  Layers,
  Database,
} from "lucide-react";
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

// ============================================================================
// CODE EXAMPLES
// ============================================================================

const quickstartPython = `import compile

# 1. Load modules — 50 functional clusters from the connectome
modules = compile.list_modules()

# 2. Select behaviors — pick a fitness function
fitness = compile.get_fitness_function("navigation")

# 3. Get connections — inspect evolvable pairs
pairs = fitness.evolvable_pairs
print(f"Evolvable connections: {len(pairs)}")

# 4. Run experiment — submit an evolution job
job = compile.submit_job(
    fitness="navigation",
    generations=50,
    mutations_per_gen=5,
    seed=42
)
print(f"Job {job.id}: {job.status}")`;

const quickstartCurl = `# 1. Load modules
curl https://api.compile.now/api/v1/compile/modules

# 2. Select a fitness function
curl https://api.compile.now/api/v1/compile/fitness-functions/navigation

# 3. Get a specific connection
curl https://api.compile.now/api/v1/compile/connections/MOD_001/MOD_002

# 4. Submit an evolution job
curl -X POST https://api.compile.now/api/v1/compile/jobs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "fitness": "navigation",
    "generations": 50,
    "mutations_per_gen": 5,
    "seed": 42
  }'`;

// ============================================================================
// API ENDPOINT DATA
// ============================================================================

const apiSections = [
  {
    title: "Modules",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/modules",
        description: "List all 50 functional modules from the connectome.",
        params: ["role?: string — Filter by role (e.g. ?role=source)"],
        curlExample: `curl https://api.compile.now/api/v1/compile/modules?role=source`,
        responseExample: `{
  "modules": [
    {
      "id": "MOD_001",
      "name": "Central Complex Ring",
      "neuron_count": 3412,
      "role": "source",
      "layer": "APP"
    },
    ...
  ],
  "total": 50
}`,
      },
      {
        method: "GET",
        path: "/api/v1/compile/modules/:id",
        description: "Get detailed information about a specific module.",
        params: ["id: string — Module identifier (e.g. MOD_001)"],
        curlExample: `curl https://api.compile.now/api/v1/compile/modules/MOD_001`,
        responseExample: `{
  "id": "MOD_001",
  "name": "Central Complex Ring",
  "neuron_count": 3412,
  "synapse_count": 28904,
  "role": "source",
  "layer": "APP",
  "top_connections": [
    { "target": "MOD_014", "weight": 0.87 },
    { "target": "MOD_022", "weight": 0.63 }
  ]
}`,
      },
    ],
  },
  {
    title: "Fitness Functions",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/fitness-functions",
        description: "List all available fitness functions.",
        params: [],
        curlExample: `curl https://api.compile.now/api/v1/compile/fitness-functions`,
        responseExample: `{
  "fitness_functions": [
    {
      "name": "navigation",
      "description": "Fly navigates toward a food source",
      "evolvable_pairs_count": 142
    },
    {
      "name": "escape",
      "description": "Fly escapes from a looming predator",
      "evolvable_pairs_count": 87
    },
    {
      "name": "turning",
      "description": "Coordinated left/right turning behavior",
      "evolvable_pairs_count": 64
    },
    {
      "name": "arousal",
      "description": "Arousal state modulation and transitions",
      "evolvable_pairs_count": 53
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/v1/compile/fitness-functions/:name",
        description: "Get details for a fitness function, including its evolvable module pairs.",
        params: ["name: string — Fitness function name (e.g. navigation)"],
        curlExample: `curl https://api.compile.now/api/v1/compile/fitness-functions/navigation`,
        responseExample: `{
  "name": "navigation",
  "description": "Fly navigates toward a food source",
  "evolvable_pairs": [
    { "source": "MOD_001", "target": "MOD_014", "baseline_weight": 0.87 },
    { "source": "MOD_001", "target": "MOD_022", "baseline_weight": 0.63 },
    ...
  ],
  "evolvable_pairs_count": 142,
  "baseline_fitness": 0.4454
}`,
      },
    ],
  },
  {
    title: "Three-Layer Map",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/three-layer-map",
        description: "Get the OS / APP / Hardware classification of all modules.",
        params: [],
        curlExample: `curl https://api.compile.now/api/v1/compile/three-layer-map`,
        responseExample: `{
  "layers": {
    "OS": {
      "description": "Core survival circuits — always on",
      "modules": ["MOD_003", "MOD_007", "MOD_019", ...]
    },
    "APP": {
      "description": "Behavioral programs — navigation, escape, foraging",
      "modules": ["MOD_001", "MOD_014", "MOD_022", ...]
    },
    "Hardware": {
      "description": "Sensory input and motor output",
      "modules": ["MOD_002", "MOD_010", "MOD_045", ...]
    }
  }
}`,
      },
    ],
  },
  {
    title: "Mutations",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/mutations",
        description: "Query mutation data for a given fitness function and seed.",
        params: [
          "fitness: string — Fitness function name (required)",
          "seed?: int — Random seed for reproducibility",
        ],
        curlExample: `curl "https://api.compile.now/api/v1/compile/mutations?fitness=navigation&seed=42"`,
        responseExample: `{
  "fitness": "navigation",
  "seed": 42,
  "mutations": [
    {
      "generation": 1,
      "type": "weight",
      "source": "MOD_001",
      "target": "MOD_014",
      "old_weight": 0.87,
      "new_weight": 1.04,
      "fitness_delta": +0.023
    },
    ...
  ],
  "total_mutations": 23,
  "final_fitness": 0.5840,
  "improvement_pct": 31.1
}`,
      },
    ],
  },
  {
    title: "Connections",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/connections/:src/:tgt",
        description: "Get details for a specific module-to-module connection.",
        params: [
          "src: string — Source module ID",
          "tgt: string — Target module ID",
        ],
        curlExample: `curl https://api.compile.now/api/v1/compile/connections/MOD_001/MOD_014`,
        responseExample: `{
  "source": "MOD_001",
  "target": "MOD_014",
  "weight": 0.87,
  "synapse_count": 1243,
  "neuron_pairs": 89,
  "layer_crossing": "APP -> APP",
  "evolvable_in": ["navigation", "turning"]
}`,
      },
    ],
  },
  {
    title: "Jobs (authenticated)",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/compile/jobs",
        description: "Submit a new evolution run. Requires authentication.",
        params: [
          "fitness_function: string — Fitness function name",
          "generations?: int — Number of generations (default 50)",
          "mutations_per_gen?: int — Mutations per generation (default 5)",
          "seed?: int — Random seed",
          "architecture?: string — Architecture ID (default cellular_automaton)",
        ],
        curlExample: `curl -X POST https://api.compile.now/api/v1/compile/jobs \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "fitness": "navigation",
    "generations": 50,
    "mutations_per_gen": 5,
    "seed": 42,
    "gain": 1.0
  }'`,
        responseExample: `{
  "id": "job_abc123",
  "status": "queued",
  "fitness": "navigation",
  "generations": 50,
  "created_at": "2026-03-16T12:00:00Z"
}`,
      },
      {
        method: "GET",
        path: "/api/v1/compile/jobs/:id",
        description: "Get the status and results of an evolution job.",
        params: ["id: string — Job identifier"],
        curlExample: `curl -H "Authorization: Bearer YOUR_API_KEY" \\
  https://api.compile.now/api/v1/compile/jobs/job_abc123`,
        responseExample: `{
  "id": "job_abc123",
  "status": "completed",
  "fitness": "navigation",
  "generations_completed": 50,
  "total_mutations": 23,
  "baseline_fitness": 0.4454,
  "final_fitness": 0.5840,
  "improvement_pct": 31.1,
  "created_at": "2026-03-16T12:00:00Z",
  "completed_at": "2026-03-16T12:04:32Z"
}`,
      },
      {
        method: "GET",
        path: "/api/v1/compile/jobs/:id/stream",
        description: "Server-Sent Events stream of job progress. Connect and receive real-time updates.",
        params: ["id: string — Job identifier"],
        curlExample: `curl -N -H "Authorization: Bearer YOUR_API_KEY" \\
  https://api.compile.now/api/v1/compile/jobs/job_abc123/stream`,
        responseExample: `event: generation
data: {"gen": 1, "fitness": 0.4512, "mutations": 3, "improved": true}

event: generation
data: {"gen": 2, "fitness": 0.4512, "mutations": 5, "improved": false}

event: complete
data: {"final_fitness": 0.5840, "total_generations": 50}`,
      },
    ],
  },
  {
    title: "Architectures",
    endpoints: [
      {
        method: "GET",
        path: "/api/v1/compile/architectures",
        description: "List all 26 validated neural circuit architectures with performance scores.",
        params: [],
        curlExample: `curl https://api.compile.now/api/v1/compile/architectures`,
        responseExample: `{
  "architectures": [
    {
      "id": "cellular_automaton",
      "name": "Neuronal Cellular Automaton",
      "category": "exotic",
      "cell_type_count": 4,
      "connection_rule_count": 4,
      "total_neurons": 3000,
      "scores": { "navigation": 100, "escape": 99, "working_memory": 288, "total": 509 }
    },
    ...
  ]
}`,
      },
    ],
  },
  {
    title: "AI Classification",
    endpoints: [
      {
        method: "POST",
        path: "/api/v1/compile/classify-behavior",
        description: "Classify a custom behavior description into a computational requirement tag using AI.",
        params: ["description: string — Natural language description of the behavior"],
        curlExample: `curl -X POST https://api.compile.now/api/v1/compile/classify-behavior \\
  -H "Content-Type: application/json" \\
  -d '{"description": "navigate toward pheromone concentration gradient"}'`,
        responseExample: `{
  "tag": "speed",
  "source": "ai"
}`,
      },
      {
        method: "POST",
        path: "/api/v1/compile/recommend-architecture",
        description: "Get AI-recommended architecture(s) for a set of behaviors and biological constraints.",
        params: [
          "behaviors: array — List of {id, tag, label} objects",
          "constraints?: object — Biological constraints (neuron_count, cell_types, spatial)",
        ],
        curlExample: `curl -X POST https://api.compile.now/api/v1/compile/recommend-architecture \\
  -H "Content-Type: application/json" \\
  -d '{
    "behaviors": [
      {"id": "navigation", "tag": "speed", "label": "Navigation"},
      {"id": "working_memory", "tag": "persistence", "label": "Working Memory"}
    ],
    "constraints": {"neuron_count": 8000}
  }'`,
        responseExample: `{
  "architecture": "composite",
  "regions": [
    {"architecture": "cellular_automaton", "for": "navigation, working_memory"},
    {"architecture": "winner_take_all", "for": "conflict_resolution"}
  ],
  "explanation": "Navigation and working memory require both speed and persistence, best served by cellular automaton. Conflict resolution requires competition, best served by winner-take-all.",
  "composite": true,
  "source": "ai"
}`,
      },
    ],
  },
];

const connectomes = [
  { name: "FlyWire FAFB v783", species: "Drosophila", neurons: "139,255", synapses: "50.1M", status: "Available" },
  { name: "BANC", species: "Drosophila (VNC)", neurons: "~115,000", synapses: "TBD", status: "Coming Soon" },
  { name: "MANC", species: "Drosophila (VNC)", neurons: "~10,000", synapses: "TBD", status: "Coming Soon" },
  { name: "MICrONS", species: "Mouse (visual cortex)", neurons: "~75,000", synapses: "TBD", status: "Coming Soon" },
];

const fitnessTypes = [
  { name: "navigation", description: "Navigate toward food sources", metric: "P9/MN9 motor output", status: "Active", tag: "speed" },
  { name: "escape", description: "Flee from looming threats", metric: "GF/MDN escape response", status: "Active", tag: "speed" },
  { name: "turning", description: "Turn toward auditory stimuli", metric: "DNa01/DNa02 asymmetry", status: "Active", tag: "speed" },
  { name: "arousal", description: "Increase alertness and responsiveness", metric: "Total DN output", status: "Active", tag: "speed" },
  { name: "working_memory", description: "Hold sensory traces after stimulus stops", metric: "CX persistent activity", status: "Active", tag: "persistence" },
  { name: "conflict", description: "Resolve competing motor commands", metric: "DN hub competition", status: "Active", tag: "competition" },
  { name: "circles", description: "Sustained circular locomotion", metric: "Angular displacement", status: "Active", tag: "rhythm" },
  { name: "rhythm", description: "Rhythmic walk-stop alternation", metric: "Motor pattern regularity", status: "Active", tag: "rhythm" },
  { name: "attention", description: "Selective attention to cued stimulus", metric: "Laterality index", status: "Partial", tag: "gating" },
];

// ============================================================================
// COMPONENTS
// ============================================================================

function CodeBlock({ code, language = "python" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <div className="absolute right-3 top-3 z-10">
        <button
          onClick={handleCopy}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition opacity-0 group-hover:opacity-100"
        >
          {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
      <div className="absolute left-4 top-3">
        <span className="text-[10px] uppercase tracking-wider text-gray-600 font-mono">{language}</span>
      </div>
      <pre className="bg-gray-950 rounded-xl p-6 pt-8 overflow-x-auto border border-gray-800">
        <code className="text-sm text-gray-300 font-mono">{code}</code>
      </pre>
    </div>
  );
}

function TabSwitch({ tabs, activeTab, onSwitch, isDark }: { tabs: string[]; activeTab: string; onSwitch: (t: string) => void; isDark?: boolean }) {
  return (
    <div className={`flex gap-1 mb-4 ${isDark !== false ? "bg-white/5" : "bg-gray-100"} rounded-lg p-1 w-fit`}>
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => onSwitch(tab)}
          className={`px-4 py-1.5 rounded-md text-sm transition ${
            activeTab === tab
              ? `bg-purple-500/30 ${isDark !== false ? "text-purple-300" : "text-purple-600"}`
              : `${isDark !== false ? "text-gray-400 hover:text-white" : "text-gray-600 hover:text-gray-900"}`
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

export default function DocsPage() {
  const [mounted, setMounted] = useState(false);
  const { theme, mode, toggleTheme } = useTheme();
  const [activeSection, setActiveSection] = useState("quickstart");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [quickstartTab, setQuickstartTab] = useState("Python");

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

  const sections = [
    { id: "quickstart", label: "Quickstart", icon: Zap },
    { id: "concepts", label: "Concepts", icon: Book },
    { id: "api", label: "API Reference", icon: Code },
    { id: "connectomes", label: "Connectomes", icon: Brain },
    { id: "evolution", label: "Evolution", icon: Dna },
  ];

  return (
    <div className={`min-h-screen ${bg} ${text} transition-colors duration-300`}>
      <Navbar theme={theme} themeMode={mode} onToggleTheme={toggleTheme} />

      <div className="flex pt-20">
        {/* Mobile sidebar toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="fixed bottom-4 right-4 z-40 md:hidden p-3 bg-purple-600 rounded-full shadow-lg"
        >
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>

        {/* Sidebar */}
        <aside className={`fixed left-0 top-20 bottom-0 w-64 border-r ${border} p-6 overflow-y-auto ${bg} z-30 transform transition-transform duration-300 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}>
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => {
                  setActiveSection(section.id);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-left text-sm transition ${
                  activeSection === section.id
                    ? isDark ? "bg-purple-500/20 text-purple-300" : "bg-purple-100 text-purple-700 font-medium"
                    : `${textMuted} hover:${text} ${isDark ? "hover:bg-white/5" : "hover:bg-gray-100"}`
                }`}
              >
                <section.icon className="w-4 h-4" />
                {section.label}
              </button>
            ))}
          </nav>

          <div className={`mt-8 pt-8 border-t ${border}`}>
            <p className={`text-xs ${textSubtle} uppercase tracking-wider mb-3`}>Try it</p>
            <Link
              href="/playground"
              className={`flex items-center gap-2 text-sm text-purple-400 ${isDark ? "hover:text-purple-300" : "hover:text-purple-600"} transition`}
            >
              <Play className="w-4 h-4" />
              Open Playground
            </Link>
          </div>

          <div className={`mt-8 pt-8 border-t ${border}`}>
            <p className={`text-xs ${textSubtle} uppercase tracking-wider mb-3`}>Resources</p>
            <div className="space-y-2">
              <Link href="/research" className={`block text-sm ${textMuted} hover:${text} transition`}>
                Research
              </Link>
              <a href="#" className={`block text-sm ${textMuted} hover:${text} transition`}>
                GitHub
              </a>
              <a href="#" className={`block text-sm ${textMuted} hover:${text} transition`}>
                Discord
              </a>
            </div>
          </div>
        </aside>

        {/* Overlay for mobile sidebar */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-20 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 md:ml-64 px-4 py-6 sm:px-8 sm:py-8 md:px-12 md:py-12 max-w-4xl overflow-x-hidden">
          <Link
            href="/"
            className={`inline-flex items-center gap-2 ${textMuted} hover:${text} transition mb-8`}
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>

          {/* Quickstart */}
          {activeSection === "quickstart" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div className="mb-8 p-4 rounded-xl border border-green-500/30 bg-green-500/10">
                <p className={`${isDark ? "text-green-400" : "text-green-600"} font-medium mb-1 text-sm sm:text-base`}>Compile API</p>
                <p className={`text-xs sm:text-sm ${textMuted}`}>
                  Evolve real connectomes. 50 modules, 4 fitness functions, full programmatic control.
                </p>
              </div>

              <h1 className="text-4xl font-light mb-4">Quickstart</h1>
              <p className={`${textMuted} mb-8 text-lg`}>
                Load modules. Select behaviors. Get connections. Run an experiment.
              </p>

              {/* The 5-step pipeline */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
                {[
                  { step: "1", label: "Specify", desc: "Cognitive capability" },
                  { step: "2", label: "Compile", desc: "Directed evolution" },
                  { step: "3", label: "Extract", desc: "Minimum circuit" },
                  { step: "4", label: "Identify", desc: "Developmental cell types" },
                  { step: "5", label: "Reverse-compile", desc: "Growth program" },
                  { step: "6", label: "Grow", desc: "Bundle growth" },
                  { step: "7", label: "Validate", desc: "Gain-robust" },
                ].map((s, i) => (
                  <div key={i} className={`p-4 text-center rounded-xl ${cardBg} border ${border}`}>
                    <div className="text-2xl font-mono text-purple-400 mb-2">{s.step}</div>
                    <div className="text-sm font-medium">{s.label}</div>
                    <div className={`text-xs ${textSubtle} mt-1`}>{s.desc}</div>
                  </div>
                ))}
              </div>

              <TabSwitch tabs={["Python", "curl"]} activeTab={quickstartTab} onSwitch={setQuickstartTab} isDark={isDark} />

              {quickstartTab === "Python" && (
                <CodeBlock code={quickstartPython} language="python" />
              )}
              {quickstartTab === "curl" && (
                <CodeBlock code={quickstartCurl} language="bash" />
              )}

              <div className="mt-8 p-6 rounded-xl bg-purple-500/10 border border-purple-500/20">
                <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-purple-400" />
                  What You Get
                </h3>
                <p className={textMuted}>
                  Submit a job and the platform runs mutation, simulation, and selection across generations.
                  Stream progress via SSE. Results include every mutation applied, fitness deltas, and the final evolved connectome.
                </p>
              </div>
            </motion.div>
          )}

          {/* Concepts */}
          {activeSection === "concepts" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h1 className="text-4xl font-light mb-4">Concepts</h1>
              <p className={`${textMuted} mb-8 text-lg`}>
                Core ideas behind the Compile API.
              </p>

              <div className="space-y-8">
                {/* Modules */}
                <div className={`p-6 rounded-xl ${cardBg} border ${border}`}>
                  <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-purple-400" />
                    Modules
                  </h3>
                  <p className={`${textMuted} mb-3`}>
                    The connectome is partitioned into <span className={text}>50 functional clusters</span> (modules).
                    Each module groups neurons that are densely connected to each other and perform a related function,
                    such as visual processing, motor control, or navigation.
                  </p>
                  <p className={`${textMuted} mb-3`}>
                    Modules can act as <span className={isDark ? "text-purple-300" : "text-purple-600"}>sources</span> (send signals),{" "}
                    <span className={isDark ? "text-purple-300" : "text-purple-600"}>targets</span> (receive signals), or both. Evolution operates
                    on the connections between modules, not individual neurons.
                  </p>
                  <p className={textMuted}>
                    The gene-guided approach selects neurons by developmental hemilineage rather than module ID,
                    producing the 8,158-neuron processor (19 hemilineages) that is 19x more active.
                    Both LIF and Izhikevich neuron models are supported for model-independent validation.
                  </p>
                </div>

                {/* Fitness Functions */}
                <div className={`p-6 rounded-xl ${cardBg} border ${border}`}>
                  <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                    <Target className="w-5 h-5 text-green-400" />
                    Fitness Functions
                  </h3>
                  <p className={`${textMuted} mb-3`}>
                    A fitness function defines the <span className={text}>behavioral objective</span> that drives evolution.
                    Each fitness function specifies which module pairs are evolvable and how performance is measured.
                  </p>
                  <div className={`mt-4 overflow-x-auto rounded-xl border ${border}`}>
                    <table className="w-full">
                      <thead className={isDark ? "bg-white/5" : "bg-gray-50"}>
                        <tr>
                          <th className="text-left text-xs uppercase tracking-wider text-gray-500 px-6 py-3">Name</th>
                          <th className="text-left text-xs uppercase tracking-wider text-gray-500 px-6 py-3">Tag</th>
                          <th className="text-left text-xs uppercase tracking-wider text-gray-500 px-6 py-3">Description</th>
                          <th className="text-left text-xs uppercase tracking-wider text-gray-500 px-6 py-3">Metric</th>
                        </tr>
                      </thead>
                      <tbody className={`divide-y ${isDark ? "divide-white/5" : "divide-gray-200"}`}>
                        {fitnessTypes.map((f, i) => (
                          <tr key={i} className={isDark ? "hover:bg-white/[0.02]" : "hover:bg-gray-50"}>
                            <td className={`px-6 py-3 font-mono text-sm ${isDark ? "text-purple-300" : "text-purple-600"}`}>{f.name}</td>
                            <td className={`px-6 py-3 text-sm`}><span className={`px-2 py-0.5 rounded-full text-[10px] ${isDark ? "bg-purple-500/10 text-purple-400" : "bg-purple-50 text-purple-600"}`}>{f.tag}</span></td>
                            <td className={`px-6 py-3 ${textMuted} text-sm`}>{f.description}</td>
                            <td className={`px-6 py-3 ${textMuted} text-sm`}>{f.metric}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Three-Layer Map */}
                <div className={`p-6 rounded-xl ${cardBg} border ${border}`}>
                  <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-cyan-400" />
                    Three-Layer Map
                  </h3>
                  <p className={`${textMuted} mb-4`}>
                    Every module belongs to one of three layers, analogous to a computer architecture.
                  </p>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                      <div className="text-sm font-medium text-red-400 mb-1">OS</div>
                      <p className={`text-xs ${textMuted}`}>
                        Core survival circuits. Always on. Breathing, homeostasis, arousal state.
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                      <div className="text-sm font-medium text-purple-400 mb-1">APP</div>
                      <p className={`text-xs ${textMuted}`}>
                        Behavioral programs. Navigation, escape, foraging. The layer evolution primarily targets.
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <div className="text-sm font-medium text-blue-400 mb-1">Hardware</div>
                      <p className={`text-xs ${textMuted}`}>
                        Sensory input and motor output. Eyes, antennae, leg motor neurons.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Evolvable Pairs */}
                <div className={`p-6 rounded-xl ${cardBg} border ${border}`}>
                  <h3 className="text-lg font-medium mb-3 flex items-center gap-2">
                    <Dna className="w-5 h-5 text-green-400" />
                    Evolvable Pairs
                  </h3>
                  <p className={textMuted}>
                    Not every module connection is evolvable. Each fitness function defines a subset of
                    source-target module pairs that evolution is allowed to mutate. This constrains the search
                    space and ensures that core survival circuits (OS layer) remain intact. Query evolvable pairs
                    through the <code className={`${isDark ? "text-purple-300 bg-white/5" : "text-purple-600 bg-gray-100"} text-sm px-1.5 py-0.5 rounded`}>fitness-functions/:name</code> endpoint.
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* API Reference */}
          {activeSection === "api" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h1 className="text-4xl font-light mb-4">API Reference</h1>
              <p className={`${textMuted} mb-4 text-lg`}>
                Complete reference for the Compile REST API.
              </p>
              <p className={`text-sm ${textSubtle} mb-8`}>
                Base URL: <code className={`${isDark ? "text-purple-300 bg-white/5" : "text-purple-600 bg-gray-100"} px-2 py-0.5 rounded`}>https://api.compile.now</code>
              </p>

              <div className="space-y-12">
                {apiSections.map((section, si) => (
                  <div key={si}>
                    <h2 className="text-2xl font-medium mb-6 flex items-center gap-2">
                      {section.title}
                    </h2>
                    <div className="space-y-6">
                      {section.endpoints.map((endpoint, ei) => (
                        <div
                          key={ei}
                          className={`p-6 rounded-xl border ${border} ${cardBg}`}
                        >
                          <div className="flex items-center gap-3 mb-3 flex-wrap">
                            <span
                              className={`text-xs font-mono px-2 py-1 rounded ${
                                endpoint.method === "POST"
                                  ? "bg-green-500/20 text-green-400"
                                  : "bg-blue-500/20 text-blue-400"
                              }`}
                            >
                              {endpoint.method}
                            </span>
                            <code className={`${isDark ? "text-purple-300" : "text-purple-600"} font-mono text-sm break-all`}>{endpoint.path}</code>
                          </div>
                          <p className={`${textMuted} mb-4`}>{endpoint.description}</p>

                          {endpoint.params.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                                Parameters
                              </p>
                              <div className="space-y-1">
                                {endpoint.params.map((param, j) => (
                                  <code key={j} className={`block text-sm ${textMuted} font-mono`}>
                                    {param}
                                  </code>
                                ))}
                              </div>
                            </div>
                          )}

                          <div className="mb-4">
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Example Request</p>
                            <CodeBlock code={endpoint.curlExample} language="bash" />
                          </div>

                          <div>
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Example Response</p>
                            <CodeBlock code={endpoint.responseExample} language="json" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Connectomes */}
          {activeSection === "connectomes" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h1 className="text-4xl font-light mb-4">Connectomes</h1>
              <p className={`${textMuted} mb-8 text-lg`}>
                Brain wiring diagrams that serve as evolution seeds. Each connectome is a complete map
                of neurons and synaptic connections.
              </p>

              <div className="mb-8 p-6 rounded-xl bg-green-500/10 border border-green-500/20">
                <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
                  <Database className="w-5 h-5 text-green-400" />
                  Available Now
                </h3>
                <p className={textMuted}>
                  <span className={text}>FlyWire FAFB v783</span> — The complete <em>Drosophila</em> brain.
                  139,255 neurons and 50,186,344 synapses. This is the connectome used for all current evolution experiments.
                </p>
              </div>

              <div className={`overflow-x-auto rounded-xl border ${border}`}>
                <table className="w-full">
                  <thead className={isDark ? "bg-white/5" : "bg-gray-50"}>
                    <tr>
                      <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-4`}>Connectome</th>
                      <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-4`}>Species</th>
                      <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-4`}>Neurons</th>
                      <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-4`}>Synapses</th>
                      <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-4`}>Status</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? "divide-white/5" : "divide-gray-200"}`}>
                    {connectomes.map((c, i) => (
                      <tr key={i} className={isDark ? "hover:bg-white/[0.02]" : "hover:bg-gray-50"}>
                        <td className="px-6 py-4 font-medium">{c.name}</td>
                        <td className={`px-6 py-4 ${textMuted} text-sm`}>{c.species}</td>
                        <td className={`px-6 py-4 ${textMuted} font-mono`}>{c.neurons}</td>
                        <td className={`px-6 py-4 ${textMuted} font-mono`}>{c.synapses}</td>
                        <td className="px-6 py-4">
                          <span className={`text-xs px-2 py-1 rounded ${c.status === "Available" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                            {c.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className={`mt-8 p-6 rounded-xl ${cardBg} border ${border}`}>
                <h3 className="font-medium mb-2">Coming Soon</h3>
                <p className={`${textMuted} text-sm`}>
                  BANC, MANC, and MICrONS connectomes are in preparation. Each new connectome becomes a new
                  evolution seed with different neural architectures and capabilities.
                </p>
              </div>
            </motion.div>
          )}

          {/* Evolution */}
          {activeSection === "evolution" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h1 className="text-4xl font-light mb-4">Evolution</h1>
              <p className={`${textMuted} mb-8 text-lg`}>
                How the Compile evolution engine works. Mutation, fitness evaluation, selection.
              </p>

              {/* How it works */}
              <div className={`mb-8 p-6 rounded-xl ${cardBg} border ${border}`}>
                <h3 className="text-lg font-medium mb-4">How It Works</h3>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                    <div className="text-sm font-medium text-purple-400 mb-2">1. Mutation</div>
                    <p className={`text-xs ${textMuted}`}>
                      Each generation applies N mutations to evolvable module pairs. Mutations change
                      connection weights (strengthen or weaken) or rewire connections between modules.
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                    <div className="text-sm font-medium text-cyan-400 mb-2">2. Fitness Evaluation</div>
                    <p className={`text-xs ${textMuted}`}>
                      The mutated connectome is simulated in the fitness function environment.
                      Neural activity propagates through the network and produces behavior that is scored.
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                    <div className="text-sm font-medium text-green-400 mb-2">3. Selection</div>
                    <p className={`text-xs ${textMuted}`}>
                      If the mutation improved fitness, keep it. If not, revert. Only beneficial
                      changes accumulate. Conservative hill-climbing on the fitness landscape.
                    </p>
                  </div>
                </div>
              </div>

              {/* Fitness functions */}
              <div className="mb-8">
                <h3 className="text-lg font-medium mb-4">Fitness Functions</h3>
                <div className={`overflow-x-auto rounded-xl border ${border}`}>
                  <table className="w-full">
                    <thead className={isDark ? "bg-white/5" : "bg-gray-50"}>
                      <tr>
                        <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-3`}>Function</th>
                        <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-3`}>Behavior</th>
                        <th className={`text-left text-xs uppercase tracking-wider ${textSubtle} px-6 py-3`}>Metric</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y ${isDark ? "divide-white/5" : "divide-gray-200"}`}>
                      {fitnessTypes.map((f, i) => (
                        <tr key={i} className={isDark ? "hover:bg-white/[0.02]" : "hover:bg-gray-50"}>
                          <td className={`px-6 py-3 font-mono text-sm ${isDark ? "text-purple-300" : "text-purple-600"}`}>{f.name}</td>
                          <td className={`px-6 py-3 ${textMuted} text-sm`}>{f.description}</td>
                          <td className={`px-6 py-3 ${textMuted} text-sm`}>{f.metric}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Parameters */}
              <div className={`mb-8 p-6 rounded-xl ${cardBg} border ${border}`}>
                <h3 className="text-lg font-medium mb-4">Parameters</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-start">
                    <div>
                      <code className={`${isDark ? "text-purple-300" : "text-purple-600"} font-mono`}>generations</code>
                      <span className="text-gray-500 ml-2">int</span>
                    </div>
                    <span className={`${textMuted} text-right max-w-xs`}>Number of evolution cycles. Each generation applies mutations and evaluates fitness.</span>
                  </div>
                  <div className={`border-t ${border}`} />
                  <div className="flex justify-between items-start">
                    <div>
                      <code className={`${isDark ? "text-purple-300" : "text-purple-600"} font-mono`}>mutations_per_gen</code>
                      <span className="text-gray-500 ml-2">int</span>
                    </div>
                    <span className={`${textMuted} text-right max-w-xs`}>Mutations applied per generation. Conservative values (3-5) work best.</span>
                  </div>
                  <div className={`border-t ${border}`} />
                  <div className="flex justify-between items-start">
                    <div>
                      <code className={`${isDark ? "text-purple-300" : "text-purple-600"} font-mono`}>seed</code>
                      <span className="text-gray-500 ml-2">int, optional</span>
                    </div>
                    <span className={`${textMuted} text-right max-w-xs`}>Random seed for reproducible experiments.</span>
                  </div>
                  <div className={`border-t ${border}`} />
                  <div className="flex justify-between items-start">
                    <div>
                      <code className={`${isDark ? "text-purple-300" : "text-purple-600"} font-mono`}>gain</code>
                      <span className="text-gray-500 ml-2">float, optional</span>
                    </div>
                    <span className={`${textMuted} text-right max-w-xs`}>Synaptic gain multiplier. Controls signal amplification across connections. Default 1.0.</span>
                  </div>
                </div>
              </div>

              <div className="p-6 rounded-xl bg-purple-500/10 border border-purple-500/20">
                <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
                  <Dna className="w-5 h-5 text-purple-400" />
                  Key Finding
                </h3>
                <p className={textMuted}>
                  With 50 generations and 5 mutations per generation, the navigation fitness improved from
                  0.4454 to 0.5840 (<span className="text-green-400">+31.1%</span>) with only 23 total mutations applied.
                  Core circuits remained unchanged. Shuffled connectomes produce{" "}
                  <span className="text-red-400">zero activity</span> — biological structure is essential.
                </p>
              </div>
            </motion.div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className={`py-12 border-t ${border}`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-8">
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
