"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Sun, Moon, Monitor } from "lucide-react";
import dynamic from "next/dynamic";
import { setAuthToken } from "@/lib/api";

const AuthInline = dynamic(() => import("@/components/AuthInline").then((mod) => ({ default: mod.AuthInline })), { ssr: false });

type ThemeMode = "dark" | "light" | "system";

interface NavbarProps {
  theme?: "dark" | "light";
  themeMode?: ThemeMode;
  onToggleTheme?: () => void;
}

export default function Navbar({ theme: externalTheme, themeMode: externalMode, onToggleTheme }: NavbarProps = {}) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [internalMode, setInternalMode] = useState<ThemeMode>("system");
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
    if (!externalTheme && !externalMode) {
      const stored = localStorage.getItem("themeMode") as ThemeMode | null;
      if (stored) setInternalMode(stored);
    }
  }, [externalTheme, externalMode]);

  // Determine current mode and resolved theme
  const currentMode = externalMode ?? internalMode;
  const resolvedTheme = externalTheme ?? (currentMode === "system" ? (systemPrefersDark ? "dark" : "light") : currentMode);
  const isDark = resolvedTheme === "dark";

  const toggleTheme = () => {
    if (onToggleTheme) {
      onToggleTheme();
    } else {
      // Cycle: dark -> light -> system -> dark
      const nextMode: ThemeMode = currentMode === "dark" ? "light" : currentMode === "light" ? "system" : "dark";
      setInternalMode(nextMode);
      localStorage.setItem("themeMode", nextMode);
    }
  };

  const getThemeIcon = () => {
    if (currentMode === "system") return <Monitor className="w-4 h-4" />;
    if (currentMode === "light") return <Sun className="w-4 h-4" />;
    return <Moon className="w-4 h-4" />;
  };

  const isActive = (path: string) => {
    if (path === "/careers" || path === "/about") {
      return pathname?.startsWith(path);
    }
    return pathname === path;
  };

  const navLinks = [
    { href: "/research", label: "Research" },
    { href: "/playground", label: "Playground" },
    { href: "/catalog", label: "Catalog" },
    { href: "/docs", label: "Docs" },
    { href: "/about", label: "About" },
    { href: "/credits", label: "Credits" },
    { href: "/deck", label: "Deck" },
    // { href: "/careers", label: "Careers" },
  ];

  const bg = isDark ? "bg-black/80" : "bg-white/80";
  const border = isDark ? "border-white/10" : "border-gray-200";
  const text = isDark ? "text-white" : "text-gray-900";
  const textMuted = isDark ? "text-gray-400" : "text-gray-600";
  const cardBg = isDark ? "bg-white/5" : "bg-gray-100";

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 ${bg} backdrop-blur-xl border-b ${border}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-0" aria-label="Compile home">
          <svg viewBox="0 0 44 40" className="w-14 h-14" aria-hidden="true">
            <line x1="12" y1="20" x2="32" y2="20" stroke="#9333EA" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="12" cy="20" r="5" fill="#7C3AED"/>
            <circle cx="32" cy="20" r="5" fill="#A855F7"/>
          </svg>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm transition relative ${isActive(link.href) ? `${text} font-medium` : `${textMuted} hover:${text}`}`}
            >
              {link.label}
              {isActive(link.href) && (
                <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
              )}
            </Link>
          ))}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg ${cardBg} hover:bg-purple-500/10 transition`}
            title={`Theme: ${currentMode}`}
          >
            {getThemeIcon()}
          </button>
          <a
            href="https://github.com/compile-os"
            target="_blank"
            rel="noopener noreferrer"
            className={`p-2 rounded-lg ${isDark ? "hover:bg-white/10" : "hover:bg-gray-200"} transition`}
            title="GitHub"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
          </a>
          <AuthInline isDark={isDark} onSuccess={(_user: unknown, token: string) => setAuthToken(token)} />
        </div>

        {/* Mobile nav controls */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg ${cardBg} hover:bg-purple-500/10 transition`}
            title={`Theme: ${currentMode}`}
          >
            {getThemeIcon()}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className={`p-2 ${textMuted} hover:${text} transition`}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className={`md:hidden border-t ${border} ${isDark ? "bg-black/95" : "bg-white/95"} backdrop-blur-xl`}>
          <div className="px-4 py-4 space-y-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block py-2 text-base transition ${isActive(link.href) ? `${text} font-medium border-l-2 border-purple-500 pl-3` : `${textMuted} hover:${text} pl-3`}`}
              >
                {link.label}
              </Link>
            ))}
            <div className="pt-2 border-t border-white/10">
              <AuthInline isDark={isDark} onSuccess={(_user: unknown, token: string) => setAuthToken(token)} />
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
