"use client";

import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

// Dynamic neural waves - positioned at bottom
function NeuralWaves({ width, height, frame }: { width: number; height: number; frame: number }) {
  const waveLayers = [
    { baseFreq: 0.006, amp: 30, speed: 0.02, color: "#8b5cf6", opacity: 0.5, yOffset: 0 },
    { baseFreq: 0.008, amp: 22, speed: 0.03, color: "#a855f7", opacity: 0.4, yOffset: 15 },
    { baseFreq: 0.012, amp: 18, speed: 0.04, color: "#c084fc", opacity: 0.35, yOffset: -10 },
    { baseFreq: 0.004, amp: 40, speed: 0.015, color: "#7c3aed", opacity: 0.25, yOffset: 25 },
    { baseFreq: 0.015, amp: 12, speed: 0.05, color: "#6366f1", opacity: 0.3, yOffset: -20 },
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
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ position: "absolute", bottom: 0, left: 0 }}
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

export const CompileHero: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  // Content fades in and STAYS visible forever (clamp ensures it stays at 1)
  const titleOpacity = interpolate(frame, [0, 40], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, 40], [30, 0], { extrapolateRight: "clamp" });
  const subtitleOpacity = interpolate(frame, [25, 55], [0, 1], { extrapolateRight: "clamp" });
  const taglineOpacity = interpolate(frame, [45, 75], [0, 1], { extrapolateRight: "clamp" });
  const pipelineOpacity = interpolate(frame, [65, 95], [0, 1], { extrapolateRight: "clamp" });

  // Signal animations - staggered! First one leads, second follows
  const signal1Progress = (frame % 120) / 120;
  const signal2Progress = ((frame + 60) % 120) / 120; // Offset by half cycle

  // Compile orb subtle pulse
  const orbPulse = 1 + Math.sin(frame * 0.05) * 0.03;
  const orbGlow = 0.15 + Math.sin(frame * 0.03) * 0.05;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* Waves at BOTTOM - not center */}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 280 }}>
        <NeuralWaves width={width} height={280} frame={frame} />
      </div>

      {/* Subtle gradient overlays */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at 50% 40%, rgba(124, 58, 237, 0.08) 0%, transparent 50%)",
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
          padding: 80,
          paddingBottom: 200, // Push up from waves
        }}
      >
        {/* Title */}
        <h1
          style={{
            fontSize: 140,
            fontWeight: 200,
            color: "white",
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
            fontSize: 24,
            color: "rgba(255,255,255,0.5)",
            margin: "16px 0 0 0",
            opacity: subtitleOpacity,
            fontWeight: 400,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
          }}
        >
          We Design Biological Brains
        </p>

        {/* Tagline */}
        <p
          style={{
            fontSize: 28,
            color: "rgba(255,255,255,0.7)",
            maxWidth: 700,
            textAlign: "center",
            lineHeight: 1.6,
            opacity: taglineOpacity,
            marginTop: 40,
            fontWeight: 300,
          }}
        >
          Synthetic neuroscience starts now.
        </p>

        {/* Pipeline visualization */}
        <div
          style={{
            marginTop: 70,
            display: "flex",
            alignItems: "center",
            gap: 0,
            opacity: pipelineOpacity,
          }}
        >
          {/* Input: RAW SIGNALS */}
          <div
            style={{
              width: 200,
              height: 100,
              background: "rgba(255,255,255,0.02)",
              borderRadius: 16,
              border: "1px solid rgba(255,255,255,0.06)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(10px)",
            }}
          >
            <svg width="160" height="40" viewBox="0 0 160 40" style={{ opacity: 0.8 }}>
              {[0, 1, 2].map((i) => (
                <path
                  key={i}
                  d={`M 0 ${20 + i * 5} ${Array.from({ length: 32 }, (_, x) => {
                    const xPos = x * 5;
                    const yPos = 20 + Math.sin((x + frame * 0.1 + i * 2.5) * 0.45) * (7 - i * 1.5);
                    return `L ${xPos} ${yPos}`;
                  }).join(" ")}`}
                  fill="none"
                  stroke={["#ef4444", "#f97316", "#eab308"][i]}
                  strokeWidth="1.5"
                  opacity={0.85 - i * 0.1}
                />
              ))}
            </svg>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", marginTop: 8, letterSpacing: "0.15em", fontWeight: 500 }}>
              RAW SIGNALS
            </span>
          </div>

          {/* Connection 1 */}
          <div style={{ width: 80, height: 2, position: "relative" }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "linear-gradient(90deg, rgba(239,68,68,0.3), rgba(168,85,247,0.3))",
                borderRadius: 1,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: `${signal1Progress * 100}%`,
                top: "50%",
                transform: "translate(-50%, -50%)",
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: `linear-gradient(135deg, #ef4444, #a855f7)`,
                boxShadow: "0 0 12px rgba(168,85,247,0.8), 0 0 24px rgba(168,85,247,0.4)",
              }}
            />
          </div>

          {/* Compile orb - more sophisticated */}
          <div
            style={{
              width: 110,
              height: 110,
              borderRadius: "50%",
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${orbPulse})`,
            }}
          >
            {/* Outer glow ring */}
            <div
              style={{
                position: "absolute",
                inset: -12,
                borderRadius: "50%",
                background: `radial-gradient(circle, rgba(168,85,247,${orbGlow}) 0%, transparent 70%)`,
              }}
            />
            {/* Outer ring */}
            <div
              style={{
                position: "absolute",
                inset: -4,
                borderRadius: "50%",
                border: "1px solid rgba(168,85,247,0.2)",
              }}
            />
            {/* Middle ring with rotating dot */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                border: "1px solid rgba(168,85,247,0.15)",
                transform: `rotate(${frame * 0.5}deg)`,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: -3,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#a855f7",
                  boxShadow: "0 0 8px #a855f7",
                }}
              />
            </div>
            {/* Core */}
            <div
              style={{
                width: 90,
                height: 90,
                borderRadius: "50%",
                background: "radial-gradient(circle at 35% 35%, rgba(168,85,247,0.2), rgba(124,58,237,0.05))",
                border: "1px solid rgba(168,85,247,0.2)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "inset 0 0 30px rgba(168,85,247,0.1)",
              }}
            >
              <span style={{ fontSize: 13, color: "white", fontWeight: 500, letterSpacing: "0.02em" }}>
                compile
              </span>
              <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", marginTop: 2 }}>
                ( )
              </span>
            </div>
          </div>

          {/* Connection 2 - staggered timing */}
          <div style={{ width: 80, height: 2, position: "relative" }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "linear-gradient(90deg, rgba(168,85,247,0.3), rgba(34,197,94,0.3))",
                borderRadius: 1,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: `${signal2Progress * 100}%`,
                top: "50%",
                transform: "translate(-50%, -50%)",
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: `linear-gradient(135deg, #a855f7, #22c55e)`,
                boxShadow: "0 0 12px rgba(34,197,94,0.8), 0 0 24px rgba(34,197,94,0.4)",
              }}
            />
          </div>

          {/* Output: EMBEDDING */}
          <div
            style={{
              width: 200,
              height: 100,
              background: "rgba(255,255,255,0.02)",
              borderRadius: 16,
              border: "1px solid rgba(34,197,94,0.1)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(10px)",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(12, 1fr)",
                gap: 2,
                padding: 8,
              }}
            >
              {Array.from({ length: 36 }, (_, i) => {
                const row = Math.floor(i / 12);
                const col = i % 12;
                const wave = Math.sin((col + frame * 0.05) * 0.6 + row * 0.3) * 0.5 + 0.5;
                return (
                  <div
                    key={i}
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: 1.5,
                      background: `rgba(34,197,94,${0.15 + wave * 0.5})`,
                    }}
                  />
                );
              })}
            </div>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", marginTop: 4, letterSpacing: "0.15em", fontWeight: 500 }}>
              768D EMBEDDING
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default CompileHero;
