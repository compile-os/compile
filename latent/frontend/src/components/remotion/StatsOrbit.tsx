"use client";

import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from "remotion";

export const StatsOrbit: React.FC = () => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const isMobile = width < 500;

  const stats = [
    { value: "0", label: "CALIBRATION", unit: "seconds" },
    { value: "10+", label: "DEVICES", unit: "supported" },
    { value: "768", label: "DIMENSIONS", unit: "embedding" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        flexDirection: isMobile ? "column" : "row",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
        gap: isMobile ? "24px" : "60px",
        padding: isMobile ? "20px" : "40px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {stats.map((stat, i) => {
          const delay = i * 15;
          const opacity = interpolate(frame - delay, [0, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const y = interpolate(frame - delay, [0, 30], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

          return (
            <div
              key={stat.label}
              style={{
                textAlign: "center",
                opacity,
                transform: `translateY(${y}px)`,
              }}
            >
              <div style={{
                fontSize: isMobile ? "48px" : "64px",
                fontWeight: 200,
                color: "white",
                lineHeight: 1,
                marginBottom: isMobile ? "8px" : "12px",
              }}>
                {stat.value}
              </div>
              <div style={{
                fontSize: isMobile ? "11px" : "12px",
                color: "#9333ea",
                letterSpacing: "2px",
                marginBottom: "4px",
              }}>
                {stat.label}
              </div>
              <div style={{
                fontSize: isMobile ? "10px" : "11px",
                color: "#666",
              }}>
                {stat.unit}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
