"use client";

import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export const BandwidthGap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const isMobile = width < 500;

  // Animate the brain bar
  const brainBarWidth = spring({
    frame,
    fps,
    config: { damping: 50, stiffness: 100 },
  }) * 100;

  // Pulsing glow effect
  const glowOpacity = interpolate(
    Math.sin(frame * 0.1),
    [-1, 1],
    [0.3, 0.8]
  );

  // Number counter animation
  const brainBits = Math.floor(interpolate(frame, [0, 60], [0, 10], { extrapolateRight: "clamp" }));
  const bciBits = Math.floor(interpolate(frame, [30, 90], [0, 10], { extrapolateRight: "clamp" }));

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
        padding: isMobile ? "20px" : "30px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {/* Brain bandwidth */}
        <div style={{ width: "100%", marginBottom: isMobile ? "24px" : "40px" }}>
          <div style={{
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            justifyContent: isMobile ? "flex-start" : "space-between",
            alignItems: isMobile ? "flex-start" : "baseline",
            marginBottom: isMobile ? "10px" : "16px",
            gap: isMobile ? "4px" : "0",
          }}>
            <span style={{ color: "#9333ea", fontSize: isMobile ? "11px" : "14px", textTransform: "uppercase", letterSpacing: "2px" }}>
              Brain Computation
            </span>
            <span style={{ color: "white", fontSize: isMobile ? "32px" : "48px", fontWeight: 200 }}>
              {brainBits}B <span style={{ fontSize: isMobile ? "14px" : "20px", color: "#888" }}>bits/sec</span>
            </span>
          </div>
          <div style={{
            height: isMobile ? "8px" : "12px",
            backgroundColor: "rgba(255,255,255,0.1)",
            borderRadius: "6px",
            overflow: "hidden",
            position: "relative",
          }}>
            <div style={{
              width: `${brainBarWidth}%`,
              height: "100%",
              background: "linear-gradient(90deg, #9333ea, #c084fc, #9333ea)",
              borderRadius: "6px",
              boxShadow: `0 0 30px rgba(147, 51, 234, ${glowOpacity})`,
            }} />
          </div>
        </div>

        {/* BCI bandwidth */}
        <div style={{ width: "100%" }}>
          <div style={{
            display: "flex",
            flexDirection: isMobile ? "column" : "row",
            justifyContent: isMobile ? "flex-start" : "space-between",
            alignItems: isMobile ? "flex-start" : "baseline",
            marginBottom: isMobile ? "10px" : "16px",
            gap: isMobile ? "4px" : "0",
          }}>
            <span style={{ color: "#666", fontSize: isMobile ? "11px" : "14px", textTransform: "uppercase", letterSpacing: "2px" }}>
              Best BCI Decoder
            </span>
            <span style={{ color: "#666", fontSize: isMobile ? "32px" : "48px", fontWeight: 200 }}>
              ~{bciBits} <span style={{ fontSize: isMobile ? "14px" : "20px" }}>bits/sec</span>
            </span>
          </div>
          <div style={{
            height: isMobile ? "8px" : "12px",
            backgroundColor: "rgba(255,255,255,0.05)",
            borderRadius: "6px",
            overflow: "hidden",
          }}>
            <div style={{
              width: "3px",
              minWidth: "3px",
              height: "100%",
              backgroundColor: "#444",
              borderRadius: "6px",
            }} />
          </div>
        </div>

        {/* Gap indicator */}
        <div style={{
          marginTop: isMobile ? "24px" : "40px",
          textAlign: "center",
        }}>
          <div style={{
            fontSize: isMobile ? "48px" : "72px",
            fontWeight: 200,
            color: "white",
            lineHeight: 1,
          }}>
            9
          </div>
          <div style={{
            fontSize: isMobile ? "11px" : "14px",
            color: "#9333ea",
            textTransform: "uppercase",
            letterSpacing: "2px",
            marginTop: "8px",
          }}>
            orders of magnitude
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
