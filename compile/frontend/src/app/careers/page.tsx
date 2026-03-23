"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import ApplicationForm from "@/components/ApplicationForm";

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

interface Role {
  title: string;
  department: string;
  location: string;
  type: string;
  description: string;
  responsibilities: string[];
  slug: string;
}

const openRoles: Role[] = [
  {
    title: "Research Scientist",
    department: "Computational Neuroscience",
    location: "New York",
    type: "Full-time",
    description:
      "Design biological neural circuits using directed evolution on real connectomes. Validate growth programs that produce functional circuits from specification alone.",
    responsibilities: [
      "Run deterministic edge sweeps on complete connectomes (FlyWire, BANC, MICrONS)",
      "Design and validate sequential activity-dependent growth programs across species",
      "Validate circuit designs against experimental neuroscience (DNa02, LPLC2, VIP→SST)",
    ],
    slug: "research-scientist",
  },
  {
    title: "Member of Technical Staff",
    department: "Platform Engineering",
    location: "New York",
    type: "Full-time",
    description:
      "Build the infrastructure that powers connectome-scale circuit design, growth program generation, and real-time brain visualization.",
    responsibilities: [
      "Build the compile.now platform (Next.js, Go, React Three Fiber)",
      "Scale directed evolution, growth simulation, and edge sweep infrastructure across AWS",
      "Build real-time 3D brain visualization and growth program tools",
    ],
    slug: "member-of-technical-staff",
  },
];

export default function CareersPage() {
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

  const departments = [...new Set(openRoles.map((r) => r.department))];

  return (
    <div className={`min-h-screen ${bg} ${text} transition-colors duration-300`}>
      <Navbar theme={theme} themeMode={mode} onToggleTheme={toggleTheme} />

      <section className="pt-24 sm:pt-32 pb-12 sm:pb-16 px-4 sm:px-8">
        <div className="max-w-3xl mx-auto">
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

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-light mb-8">Join Compile</h1>

            <div className={`text-base sm:text-lg ${textMuted} leading-relaxed space-y-4`}>
              <p>
                We design biological brains. Compile is synthetic neuroscience.
              </p>
              <p className={isDark ? "text-purple-300" : "text-purple-600"}>
                22 results across 2 species. 3 cognitive capabilities compiled. 8 reactive behaviors.
                Gene-guided 8,158-neuron processor. Sequential activity-dependent growth produces
                functional circuits that outperform the real FlyWire brain (851 vs 577) from
                specification alone at physiological density. Growth program validated on mouse cortex.
                The computational loop is closed.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="py-8 sm:py-12 px-4 sm:px-8">
        <div className="max-w-3xl mx-auto">
          <h2 className={`text-sm uppercase tracking-widest ${textSubtle} mb-6 sm:mb-8`}>
            Open Roles
          </h2>

          <div className="space-y-8">
            {departments.map((dept) => {
              const deptRoles = openRoles.filter((r) => r.department === dept);

              return (
                <div key={dept}>
                  <h3 className="text-xs text-purple-400 uppercase tracking-wider mb-4">{dept}</h3>
                  <div className="space-y-3">
                    {deptRoles.map((role, i) => (
                      <motion.div
                        key={`${role.title}-${i}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 * i }}
                      >
                        <Link
                          href={`/careers/${role.slug}`}
                          className={`block p-5 rounded-xl border ${border} ${cardBg} hover:border-purple-500/30 transition group`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h4 className="text-lg font-medium group-hover:text-purple-300 transition mb-1">
                                {role.title}
                              </h4>
                              <p className={`text-sm ${textSubtle} mb-3`}>
                                {role.type} · {role.location} · On-site
                              </p>
                              <p className={`text-sm ${textMuted} leading-relaxed mb-3`}>
                                {role.description}
                              </p>
                              <ul className="space-y-1">
                                {role.responsibilities.map((item, j) => (
                                  <li key={j} className={`text-sm ${textSubtle} flex items-start gap-2`}>
                                    <span className="text-purple-500 mt-1.5 w-1 h-1 rounded-full bg-purple-500 flex-shrink-0" />
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <ArrowUpRight className={`w-4 h-4 ${textSubtle} group-hover:text-purple-400 transition flex-shrink-0 mt-1`} />
                          </div>
                        </Link>
                      </motion.div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className={`py-8 sm:py-12 px-4 sm:px-8 border-t ${border}`}>
        <div className="max-w-3xl mx-auto">
          <div className="mb-6 sm:mb-8">
            <p className={`${textMuted} leading-relaxed mb-4`}>
              We design biological brains — from cognitive specification to developmental growth program,
              validated across species. If you don&apos;t see your role but are passionate about
              connectomics, synthetic neuroscience, or circuit design, reach out anyway.
            </p>
          </div>

          <ApplicationForm roleTitle="General Application" />
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
