"use client";

import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from "remotion";

export const SignalCompression: React.FC = () => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const isMobile = width < 500;

  // Signal visualization - many lines compressing to few
  const signalCount = isMobile ? 12 : 20;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
        padding: isMobile ? "20px" : "40px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {/* Signal visualization */}
        <div style={{
          display: "flex",
          flexDirection: isMobile ? "column" : "row",
          alignItems: "center",
          gap: isMobile ? "20px" : "40px",
          marginBottom: isMobile ? "24px" : "40px",
        }}>
          {/* Input signals */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: isMobile ? "2px" : "3px",
            opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}>
            {Array.from({ length: signalCount }).map((_, i) => {
              const waveOffset = Math.sin(frame * 0.1 + i * 0.5) * (isMobile ? 6 : 10);
              return (
                <div
                  key={i}
                  style={{
                    width: isMobile ? "60px" : "80px",
                    height: "2px",
                    backgroundColor: "#9333ea",
                    opacity: 0.3 + (i % 3) * 0.2,
                    transform: `translateX(${waveOffset}px)`,
                  }}
                />
              );
            })}
          </div>

          {/* Arrow */}
          <div style={{
            color: "#444",
            fontSize: isMobile ? "20px" : "24px",
            opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            transform: isMobile ? "rotate(90deg)" : "none",
          }}>
            →
          </div>

          {/* Compressed output */}
          <div style={{
            display: "flex",
            flexDirection: isMobile ? "row" : "column",
            gap: isMobile ? "6px" : "8px",
            opacity: interpolate(frame, [40, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          }}>
            {["↑", "↓", "←", "→"].map((arrow, i) => (
              <div
                key={i}
                style={{
                  width: isMobile ? "32px" : "40px",
                  height: isMobile ? "20px" : "24px",
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #333",
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#666",
                  fontSize: isMobile ? "12px" : "14px",
                }}
              >
                {arrow}
              </div>
            ))}
          </div>
        </div>

        {/* Label */}
        <div style={{
          textAlign: "center",
          opacity: interpolate(frame, [60, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          <div style={{
            color: "#666",
            fontSize: isMobile ? "11px" : "13px",
            marginBottom: isMobile ? "6px" : "8px",
          }}>
            Millions of samples per second
          </div>
          <div style={{
            color: "white",
            fontSize: isMobile ? "14px" : "18px",
            fontWeight: 300,
          }}>
            reduced to 4 discrete commands
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
