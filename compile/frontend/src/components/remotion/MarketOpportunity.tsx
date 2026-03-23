"use client";

import { AbsoluteFill, useCurrentFrame, interpolate, useVideoConfig } from "remotion";

export const MarketOpportunity: React.FC = () => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const isMobile = width < 500;

  const companies = [
    { name: "Neuralink", val: "$9B", type: "Hardware" },
    { name: "Merge Labs", val: "$850M", type: "Hardware" },
    { name: "Synchron", val: "$500M+", type: "Hardware" },
  ];

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
        {/* Companies */}
        <div style={{
          display: "flex",
          flexDirection: isMobile ? "column" : "row",
          gap: isMobile ? "24px" : "40px",
          marginBottom: isMobile ? "30px" : "50px",
        }}>
          {companies.map((company, i) => {
            const delay = i * 15;
            const opacity = interpolate(frame - delay, [0, 25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const y = interpolate(frame - delay, [0, 25], [20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

            return (
              <div
                key={company.name}
                style={{
                  textAlign: "center",
                  opacity,
                  transform: `translateY(${y}px)`,
                }}
              >
                <div style={{ color: "#666", fontSize: isMobile ? "14px" : "13px", marginBottom: "6px" }}>
                  {company.name}
                </div>
                <div style={{ color: "white", fontSize: isMobile ? "28px" : "32px", fontWeight: 200 }}>
                  {company.val}
                </div>
                <div style={{ color: "#444", fontSize: isMobile ? "12px" : "11px", marginTop: "4px" }}>
                  {company.type}
                </div>
              </div>
            );
          })}
        </div>

        {/* Divider */}
        <div style={{
          width: interpolate(frame, [50, 80], [0, isMobile ? 200 : 300], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
          height: "1px",
          backgroundColor: "#333",
          marginBottom: isMobile ? "24px" : "40px",
        }} />

        {/* Our position */}
        <div style={{
          textAlign: "center",
          opacity: interpolate(frame, [70, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          <div style={{ color: "#9333ea", fontSize: isMobile ? "11px" : "12px", letterSpacing: "2px", marginBottom: "8px" }}>
            THE MODEL LAYER
          </div>
          <div style={{ color: "white", fontSize: isMobile ? "20px" : "24px", fontWeight: 300 }}>
            compile
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
