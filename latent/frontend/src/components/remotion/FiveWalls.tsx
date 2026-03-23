"use client";

import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from "remotion";

export const FiveWalls: React.FC = () => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const isMobile = width < 500;

  const walls = [
    { num: "01", label: "Inter-Subject Variability", desc: "Different brains, different signals" },
    { num: "02", label: "Signal Drift", desc: "Degradation within sessions" },
    { num: "03", label: "Cross-Session Decay", desc: "Models fail across days" },
    { num: "04", label: "Device Heterogeneity", desc: "No shared representation" },
    { num: "05", label: "Data Scarcity", desc: "Fragmented datasets" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        height: "100%",
        padding: isMobile ? "20px" : "40px 60px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {walls.map((wall, i) => {
          const delay = i * 12;
          const opacity = interpolate(frame - delay, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const x = interpolate(frame - delay, [0, 20], [-20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

          return (
            <div
              key={wall.num}
              style={{
                display: "flex",
                flexDirection: isMobile ? "column" : "row",
                alignItems: isMobile ? "flex-start" : "center",
                gap: isMobile ? "4px" : "16px",
                marginBottom: i < walls.length - 1 ? (isMobile ? "16px" : "20px") : 0,
                opacity,
                transform: `translateX(${x}px)`,
              }}
            >
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: isMobile ? "8px" : "16px",
              }}>
                <span style={{
                  color: "#9333ea",
                  fontSize: isMobile ? "12px" : "14px",
                  fontWeight: 500,
                  minWidth: isMobile ? "24px" : "30px",
                }}>
                  {wall.num}
                </span>
                <span style={{
                  color: "white",
                  fontSize: isMobile ? "14px" : "16px",
                  fontWeight: 500,
                }}>
                  {wall.label}
                </span>
              </div>
              {!isMobile && (
                <div style={{
                  height: "1px",
                  width: "60px",
                  backgroundColor: "#333",
                }} />
              )}
              <span style={{
                color: "#666",
                fontSize: isMobile ? "12px" : "13px",
                marginLeft: isMobile ? "32px" : "0",
              }}>
                {wall.desc}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
