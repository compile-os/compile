"use client";

import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export const DataFlywheel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const isMobile = width < 500;

  // Rotation animation
  const rotation = interpolate(frame, [0, 300], [0, 360]);

  // Scale in animation
  const scale = spring({ frame, fps, config: { damping: 50 } });

  // Glow pulse
  const glowIntensity = interpolate(Math.sin(frame * 0.05), [-1, 1], [0.3, 0.7]);

  const segments = [
    { label: "More Users", color: "#9333ea" },
    { label: "More Data", color: "#7c3aed" },
    { label: "Better Model", color: "#6366f1" },
    { label: "More Value", color: "#8b5cf6" },
  ];

  const wheelSize = isMobile ? 280 : 400;
  const segmentRadius = isMobile ? 95 : 140;
  const centerSize = isMobile ? 80 : 120;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {/* Flywheel container */}
        <div style={{
          position: "relative",
          width: `${wheelSize}px`,
          height: `${wheelSize}px`,
          transform: `scale(${scale})`,
        }}>
          {/* Outer glow ring */}
          <div style={{
            position: "absolute",
            inset: "-20px",
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(147, 51, 234, ${glowIntensity}) 0%, transparent 70%)`,
          }} />

          {/* Main wheel */}
          <div style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: isMobile ? "2px solid #333" : "3px solid #333",
            transform: `rotate(${rotation}deg)`,
          }}>
            {/* Segments */}
            {segments.map((seg, i) => {
              const angle = (i * 90) - 45;
              const rad = (angle * Math.PI) / 180;
              const x = Math.cos(rad) * segmentRadius;
              const y = Math.sin(rad) * segmentRadius;

              return (
                <div
                  key={seg.label}
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) rotate(${-rotation}deg)`,
                    padding: isMobile ? "8px 10px" : "12px 16px",
                    borderRadius: "6px",
                    backgroundColor: seg.color,
                    color: "white",
                    fontSize: isMobile ? "9px" : "12px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "1px",
                    whiteSpace: "nowrap",
                  }}
                >
                  {seg.label}
                </div>
              );
            })}

            {/* Arrows between segments */}
            {segments.map((_, i) => {
              const angle = i * 90;
              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    width: isMobile ? "20px" : "30px",
                    height: isMobile ? "20px" : "30px",
                    transform: `translate(-50%, -50%) rotate(${angle}deg) translateX(${isMobile ? 65 : 100}px)`,
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" style={{ width: "100%", height: "100%" }}>
                    <path
                      d="M5 12h14m0 0l-4-4m4 4l-4 4"
                      stroke="#9333ea"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              );
            })}
          </div>

          {/* Center label */}
          <div style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}>
            <div style={{
              width: `${centerSize}px`,
              height: `${centerSize}px`,
              borderRadius: "50%",
              backgroundColor: "#111",
              border: "2px solid #9333ea",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              boxShadow: `0 0 30px rgba(147, 51, 234, ${glowIntensity})`,
            }}>
              <div style={{ color: "#9333ea", fontSize: isMobile ? "10px" : "12px", textTransform: "uppercase", letterSpacing: "1px" }}>
                The
              </div>
              <div style={{ color: "white", fontSize: isMobile ? "12px" : "16px", fontWeight: 600 }}>
                Flywheel
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
