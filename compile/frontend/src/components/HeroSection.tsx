"use client";

import { useRef, useEffect, useState } from "react";

// Neural waves component - positioned at bottom
function NeuralWaves({ width, height, isDark = true }: { width: number; height: number; isDark?: boolean }) {
  const [frame, setFrame] = useState(0);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const animate = () => {
      setFrame((f) => f + 1);
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const waveLayers = isDark ? [
    { baseFreq: 0.006, amp: 30, speed: 0.02, color: "#8b5cf6", opacity: 0.5, yOffset: 0 },
    { baseFreq: 0.008, amp: 22, speed: 0.03, color: "#a855f7", opacity: 0.4, yOffset: 15 },
    { baseFreq: 0.012, amp: 18, speed: 0.04, color: "#c084fc", opacity: 0.35, yOffset: -10 },
    { baseFreq: 0.004, amp: 40, speed: 0.015, color: "#7c3aed", opacity: 0.25, yOffset: 25 },
    { baseFreq: 0.015, amp: 12, speed: 0.05, color: "#6366f1", opacity: 0.3, yOffset: -20 },
  ] : [
    { baseFreq: 0.006, amp: 30, speed: 0.02, color: "#7c3aed", opacity: 0.6, yOffset: 0 },
    { baseFreq: 0.008, amp: 22, speed: 0.03, color: "#8b5cf6", opacity: 0.5, yOffset: 15 },
    { baseFreq: 0.012, amp: 18, speed: 0.04, color: "#a855f7", opacity: 0.4, yOffset: -10 },
    { baseFreq: 0.004, amp: 40, speed: 0.015, color: "#6366f1", opacity: 0.35, yOffset: 25 },
    { baseFreq: 0.015, amp: 12, speed: 0.05, color: "#4f46e5", opacity: 0.3, yOffset: -20 },
  ];

  const generateWavePath = (layer: typeof waveLayers[0], time: number) => {
    const points: string[] = [];
    const centerY = height / 2 + layer.yOffset;

    for (let x = 0; x <= width; x += 4) {
      const y1 = Math.sin(x * layer.baseFreq + time * layer.speed) * layer.amp;
      const y2 = Math.sin(x * layer.baseFreq * 2.3 + time * layer.speed * 1.4) * (layer.amp * 0.3);
      const y3 = Math.sin(x * layer.baseFreq * 0.6 + time * layer.speed * 0.7) * (layer.amp * 0.4);
      const beat = Math.sin(x * 0.003 + time * 0.015) * Math.sin(x * 0.004 + time * 0.02) * 12;

      const y = centerY + y1 + y2 + y3 + beat;

      if (x === 0) {
        points.push(`M ${x} ${y}`);
      } else {
        points.push(`L ${x} ${y}`);
      }
    }

    return points.join(" ");
  };

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ position: "absolute", bottom: 0, left: 0, right: 0 }}
      preserveAspectRatio="none"
    >
      <defs>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {waveLayers.map((layer, index) => (
        <g key={index}>
          <path
            d={generateWavePath(layer, frame)}
            fill="none"
            stroke={layer.color}
            strokeWidth="3"
            opacity={layer.opacity * 0.4}
            filter="url(#glow)"
            strokeLinecap="round"
          />
          <path
            d={generateWavePath(layer, frame)}
            fill="none"
            stroke={layer.color}
            strokeWidth="1.5"
            opacity={layer.opacity}
            strokeLinecap="round"
          />
        </g>
      ))}

      {/* Sparkle particles on waves */}
      {Array.from({ length: 12 }, (_, i) => {
        const x = ((i * 160 + frame * 1.5) % width);
        const y = height / 2 + Math.sin(x * 0.006 + frame * 0.02) * 30;
        const sparkle = Math.sin(frame * 0.1 + i * 0.7) * 0.5 + 0.5;
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={1.5 + sparkle * 2}
            fill="#ffffff"
            opacity={0.3 + sparkle * 0.5}
          />
        );
      })}
    </svg>
  );
}

export function HeroSection({ isDark = true }: { isDark?: boolean }) {
  const [frame, setFrame] = useState(0);
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    setMounted(true);
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);

    const animate = () => {
      setFrame((f) => f + 1);
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("resize", checkMobile);
    };
  }, []);

  // Fade in animations (only once, not looping) - faster loading
  const titleOpacity = Math.min(1, frame / 15);
  const titleY = Math.max(0, 20 - (frame / 15) * 20);
  const subtitleOpacity = Math.min(1, Math.max(0, (frame - 8) / 12));
  const taglineOpacity = Math.min(1, Math.max(0, (frame - 15) / 12));
  const pipelineOpacity = Math.min(1, Math.max(0, (frame - 22) / 12));

  // Signal animation - coordinated flow through pipeline
  // One continuous cycle: first connector (0-0.4), pause at orb (0.4-0.6), second connector (0.6-1.0)
  const cycleProgress = (frame % 180) / 180;
  const signal1Progress = cycleProgress < 0.4 ? cycleProgress / 0.4 : 1;
  const signal1Opacity = cycleProgress < 0.4 ? 1 : Math.max(0, 1 - (cycleProgress - 0.4) / 0.1);
  const signal2Progress = cycleProgress > 0.6 ? (cycleProgress - 0.6) / 0.4 : 0;
  const signal2Opacity = cycleProgress > 0.6 ? 1 : 0;

  // Compile orb subtle pulse
  const orbPulse = 1 + Math.sin(frame * 0.05) * 0.03;
  const orbGlow = 0.15 + Math.sin(frame * 0.03) * 0.05;

  // Theme colors
  const bgColor = isDark ? "bg-black" : "bg-white";
  const textColor = isDark ? "white" : "#111827";
  const textMuted = isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)";
  const textSubtle = isDark ? "rgba(255,255,255,0.7)" : "rgba(0,0,0,0.7)";
  const gradientColor = isDark ? "rgba(124, 58, 237, 0.08)" : "rgba(124, 58, 237, 0.05)";
  const cardBg = isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)";
  const cardBorder = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)";

  if (!mounted) {
    return <div className={`w-full h-full ${bgColor}`} />;
  }

  return (
    <div className={`absolute inset-0 ${bgColor} overflow-hidden`}>
      {/* Waves at BOTTOM */}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 280 }}>
        <NeuralWaves width={1920} height={280} isDark={isDark} />
      </div>

      {/* Subtle gradient overlays */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 40%, ${gradientColor} 0%, transparent 50%)`,
        }}
      />

      {/* Content */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: isMobile ? 16 : 80,
          paddingBottom: isMobile ? 40 : 200,
        }}
      >
        {/* Title */}
        <h1
          style={{
            fontSize: isMobile ? 72 : 180,
            fontWeight: 200,
            color: textColor,
            margin: 0,
            letterSpacing: "-0.03em",
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          compile
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: isMobile ? 14 : 30,
            color: textMuted,
            margin: "16px 0 0 0",
            opacity: subtitleOpacity,
            fontWeight: 400,
            letterSpacing: isMobile ? "0.15em" : "0.2em",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          We Design Biological Brains
        </p>

        {/* Tagline */}
        <p
          style={{
            fontSize: isMobile ? 20 : 34,
            color: textSubtle,
            maxWidth: 800,
            textAlign: "center",
            lineHeight: 1.6,
            opacity: taglineOpacity,
            marginTop: isMobile ? 24 : 40,
            fontWeight: 300,
            padding: isMobile ? "0 10px" : 0,
          }}
        >
          Synthetic neuroscience starts now.
        </p>

        {/* Pipeline visualization — 5 stages */}
        <div
          style={{
            marginTop: isMobile ? 16 : 60,
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            alignItems: "center",
            gap: 0,
            opacity: pipelineOpacity,
          }}
        >
          {/* Stage 1: SPECIFY */}
          <div
            style={{
              width: isMobile ? 140 : 200,
              height: isMobile ? 75 : 115,
              background: cardBg,
              borderRadius: isMobile ? 10 : 12,
              border: `1px solid ${cardBorder}`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(10px)",
            }}
          >
            <div style={{ fontFamily: "monospace", fontSize: isMobile ? 10 : 14, color: "#a855f7", opacity: 0.9, textAlign: "center" }}>
              <span style={{ color: textMuted, fontSize: isMobile ? 8 : 11 }}>{'>'} </span>
              <span style={{ color: "#22c55e" }}>&quot;working memory&quot;</span>
            </div>
            <svg width={isMobile ? 80 : 120} height={isMobile ? 14 : 20} viewBox="0 0 110 20" style={{ opacity: 0.7, marginTop: 2 }}>
              {Array.from({ length: 6 }, (_, i) => {
                const x = 8 + i * 18;
                const pulse = Math.sin(frame * 0.08 + i * 0.8) * 0.4 + 0.6;
                return <circle key={i} cx={x} cy={10} r={2.5 * pulse} fill="#a855f7" opacity={pulse} />;
              })}
            </svg>
            <span style={{ fontSize: isMobile ? 8 : 11, color: textMuted, marginTop: 3, letterSpacing: "0.15em", fontWeight: 500 }}>
              SPECIFY
            </span>
          </div>

          {/* Signal connector */}
          <div style={{ width: isMobile ? 2 : 32, height: isMobile ? 10 : 2, position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, background: isMobile ? "linear-gradient(180deg, rgba(168,85,247,0.3), rgba(168,85,247,0.3))" : "linear-gradient(90deg, rgba(168,85,247,0.2), rgba(168,85,247,0.4))", borderRadius: 1 }} />
            <div style={{ position: "absolute", left: isMobile ? "50%" : `${signal1Progress * 100}%`, top: isMobile ? `${signal1Progress * 100}%` : "50%", transform: "translate(-50%, -50%)", width: 5, height: 5, borderRadius: "50%", background: "#a855f7", boxShadow: "0 0 8px rgba(168,85,247,0.8)", opacity: signal1Opacity }} />
          </div>


          {/* Compile orb */}
          <div
            style={{
              width: isMobile ? 85 : 130,
              height: isMobile ? 85 : 130,
              borderRadius: "50%",
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${orbPulse})`,
              flexShrink: 0,
            }}
          >
            <div style={{ position: "absolute", inset: isMobile ? -6 : -10, borderRadius: "50%", background: `radial-gradient(circle, rgba(168,85,247,${orbGlow}) 0%, transparent 70%)` }} />
            <div style={{ position: "absolute", inset: -3, borderRadius: "50%", border: "1px solid rgba(168,85,247,0.2)" }} />
            <div style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "1px solid rgba(168,85,247,0.15)", transform: `rotate(${frame * 0.5}deg)` }}>
              <div style={{ position: "absolute", top: -2.5, left: "50%", transform: "translateX(-50%)", width: 5, height: 5, borderRadius: "50%", background: "#a855f7", boxShadow: "0 0 8px #a855f7" }} />
            </div>
            <div
              style={{
                width: isMobile ? 68 : 108,
                height: isMobile ? 68 : 108,
                borderRadius: "50%",
                background: isDark ? "radial-gradient(circle at 35% 35%, rgba(168,85,247,0.2), rgba(124,58,237,0.05))" : "radial-gradient(circle at 35% 35%, rgba(168,85,247,0.15), rgba(124,58,237,0.03))",
                border: "1px solid rgba(168,85,247,0.2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "inset 0 0 30px rgba(168,85,247,0.1)",
              }}
            >
              <span style={{ fontSize: isMobile ? 12 : 18, color: textColor, fontWeight: 500, letterSpacing: "0.02em" }}>compile</span>
            </div>
          </div>

          {/* Signal connector */}
          <div style={{ width: isMobile ? 2 : 32, height: isMobile ? 10 : 2, position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, background: isMobile ? "linear-gradient(180deg, rgba(168,85,247,0.3), rgba(6,182,212,0.3))" : "linear-gradient(90deg, rgba(168,85,247,0.3), rgba(6,182,212,0.3))", borderRadius: 1 }} />
            <div style={{ position: "absolute", left: isMobile ? "50%" : `${signal2Progress * 100}%`, top: isMobile ? `${signal2Progress * 100}%` : "50%", transform: "translate(-50%, -50%)", width: 5, height: 5, borderRadius: "50%", background: "linear-gradient(135deg, #a855f7, #06b6d4)", boxShadow: "0 0 8px rgba(6,182,212,0.8)", opacity: signal2Opacity }} />
          </div>

          {/* Stage 3: CIRCUIT — extracted processor */}
          <div
            style={{
              width: isMobile ? 140 : 200,
              height: isMobile ? 75 : 115,
              background: cardBg,
              borderRadius: isMobile ? 10 : 12,
              border: `1px solid ${isDark ? "rgba(6,182,212,0.15)" : "rgba(6,182,212,0.25)"}`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(10px)",
            }}
          >
            <svg width={isMobile ? 100 : 150} height={isMobile ? 30 : 45} viewBox="0 0 110 35" style={{ opacity: 0.9 }}>
              {/* Minimized circuit — fewer nodes, hub-and-spoke */}
              {[
                { x: 25, y: 12, r: 3, color: "#06b6d4" },
                { x: 55, y: 18, r: 5, color: "#a855f7" },
                { x: 85, y: 12, r: 3, color: "#22c55e" },
              ].map((n, i) => {
                const p = Math.sin(frame * 0.06 + i * 1.5) * 0.3 + 0.7;
                return <g key={i}><circle cx={n.x} cy={n.y} r={n.r * 1.6} fill={n.color} opacity={0.15 * p} /><circle cx={n.x} cy={n.y} r={n.r * p} fill={n.color} opacity={0.9} /></g>;
              })}
              {[
                { x1: 25, y1: 12, x2: 55, y2: 18 },
                { x1: 85, y1: 12, x2: 55, y2: 18 },
              ].map((c, i) => {
                const g = Math.sin(frame * 0.05 + i * 1.1) * 0.4 + 0.6;
                return <line key={i} x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2} stroke="#06b6d4" strokeWidth={1.5 * g} opacity={0.5 * g} />;
              })}
            </svg>
            <div style={{ fontSize: isMobile ? 10 : 14, color: "#06b6d4", fontFamily: "monospace", opacity: 0.8 }}>3K+ neurons</div>
            <span style={{ fontSize: isMobile ? 8 : 11, color: textMuted, marginTop: 3, letterSpacing: "0.15em", fontWeight: 500 }}>
              CIRCUIT
            </span>
          </div>

          {/* Signal connector */}
          <div style={{ width: isMobile ? 2 : 32, height: isMobile ? 10 : 2, position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, background: isMobile ? "linear-gradient(180deg, rgba(6,182,212,0.3), rgba(34,197,94,0.3))" : "linear-gradient(90deg, rgba(6,182,212,0.3), rgba(34,197,94,0.3))", borderRadius: 1 }} />
            <div style={{ position: "absolute", left: isMobile ? "50%" : `${((frame * 0.012 + 0.3) % 1) * 100}%`, top: isMobile ? `${((frame * 0.012 + 0.3) % 1) * 100}%` : "50%", transform: "translate(-50%, -50%)", width: 5, height: 5, borderRadius: "50%", background: "linear-gradient(135deg, #06b6d4, #22c55e)", boxShadow: "0 0 8px rgba(34,197,94,0.8)", opacity: 0.8 }} />
          </div>

          {/* Stage 4: GROWTH PROGRAM — the end product */}
          <div
            style={{
              width: isMobile ? 140 : 200,
              height: isMobile ? 75 : 115,
              background: cardBg,
              borderRadius: isMobile ? 10 : 12,
              border: `1px solid ${isDark ? "rgba(34,197,94,0.15)" : "rgba(34,197,94,0.25)"}`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(10px)",
            }}
          >
            {/* Cell type recipe visualization */}
            <svg width={isMobile ? 100 : 150} height={isMobile ? 30 : 45} viewBox="0 0 110 35" style={{ opacity: 0.9 }}>
              {/* Cell type clusters — representing the growth program */}
              {[
                { x: 20, y: 12, r: 6, color: "#22c55e", label: "" },
                { x: 45, y: 20, r: 4, color: "#f59e0b", label: "" },
                { x: 65, y: 10, r: 5, color: "#22c55e", label: "" },
                { x: 85, y: 22, r: 3, color: "#ef4444", label: "" },
                { x: 95, y: 10, r: 4, color: "#22c55e", label: "" },
              ].map((c, i) => {
                const grow = Math.sin(frame * 0.04 + i * 1.3) * 0.2 + 0.8;
                const scatter = Math.sin(frame * 0.03 + i * 2.1) * 2;
                return (
                  <g key={i}>
                    {/* Growth halo */}
                    <circle cx={c.x} cy={c.y + scatter} r={c.r * 2} fill={c.color} opacity={0.08 * grow} />
                    {/* Cell cluster */}
                    <circle cx={c.x} cy={c.y + scatter} r={c.r * grow} fill={c.color} opacity={0.7} />
                    {/* Tiny satellite cells */}
                    {[0, 120, 240].map((angle, j) => {
                      const rad = (angle + frame * 0.3) * Math.PI / 180;
                      const dx = Math.cos(rad) * c.r * 1.8;
                      const dy = Math.sin(rad) * c.r * 1.8;
                      return <circle key={j} cx={c.x + dx} cy={c.y + scatter + dy} r={1.2} fill={c.color} opacity={0.5 * grow} />;
                    })}
                  </g>
                );
              })}
            </svg>
            <div style={{ fontSize: isMobile ? 10 : 14, color: "#22c55e", fontFamily: "monospace", opacity: 0.8 }}>19 cell types</div>
            <span style={{ fontSize: isMobile ? 8 : 11, color: textMuted, marginTop: 3, letterSpacing: "0.15em", fontWeight: 500 }}>
              GROWTH PROGRAM
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HeroSection;
