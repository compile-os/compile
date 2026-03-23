"use client";

import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export const NeuralPipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const isMobile = width < 500;

  // Sequential animations for each stage
  const stage1 = spring({ frame, fps, config: { damping: 20 } });
  const stage2 = spring({ frame: frame - 20, fps, config: { damping: 20 } });
  const stage3 = spring({ frame: frame - 40, fps, config: { damping: 20 } });
  const stage4 = spring({ frame: frame - 60, fps, config: { damping: 20 } });

  const stages = [
    { label: "Raw Signal", sub: "Any device", color: "#9333ea" },
    { label: "Encoder", sub: "Universal", color: "#7c3aed" },
    { label: "768-D", sub: "Embedding", color: "#6366f1" },
    { label: "Decode", sub: "Any task", color: "#8b5cf6" },
  ];

  const stageAnimations = [stage1, stage2, stage3, stage4];

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
        padding: isMobile ? "16px" : "20px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        {/* Pipeline */}
        <div style={{
          display: "flex",
          flexDirection: isMobile ? "column" : "row",
          alignItems: "center",
          gap: isMobile ? "8px" : "16px",
          position: "relative",
        }}>
          {stages.map((stage, i) => (
            <div key={stage.label} style={{
              display: "flex",
              flexDirection: isMobile ? "column" : "row",
              alignItems: "center"
            }}>
              {/* Stage box */}
              <div style={{
                opacity: stageAnimations[i],
                transform: `scale(${stageAnimations[i]})`,
                padding: isMobile ? "10px 20px" : "12px 16px",
                borderRadius: "10px",
                border: `2px solid ${stage.color}`,
                backgroundColor: `${stage.color}20`,
                textAlign: "center",
                minWidth: isMobile ? "120px" : "80px",
              }}>
                <div style={{
                  color: "white",
                  fontSize: isMobile ? "16px" : "14px",
                  fontWeight: 500,
                  marginBottom: "2px",
                }}>
                  {stage.label}
                </div>
                <div style={{
                  color: "#888",
                  fontSize: isMobile ? "11px" : "10px",
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                }}>
                  {stage.sub}
                </div>
              </div>

              {/* Connector arrow */}
              {i < stages.length - 1 && (
                isMobile ? (
                  <div style={{
                    width: "2px",
                    height: "16px",
                    backgroundColor: "#333",
                    position: "relative",
                    marginTop: "4px",
                    marginBottom: "4px",
                    opacity: stageAnimations[i + 1],
                  }}>
                    <div style={{
                      position: "absolute",
                      bottom: "-6px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      width: 0,
                      height: 0,
                      borderLeft: "6px solid transparent",
                      borderRight: "6px solid transparent",
                      borderTop: "8px solid #9333ea",
                    }} />
                  </div>
                ) : (
                  <div style={{
                    width: "40px",
                    height: "2px",
                    backgroundColor: "#333",
                    position: "relative",
                    marginLeft: "12px",
                    opacity: stageAnimations[i + 1],
                  }}>
                    <div style={{
                      position: "absolute",
                      right: "-8px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      width: 0,
                      height: 0,
                      borderTop: "6px solid transparent",
                      borderBottom: "6px solid transparent",
                      borderLeft: "8px solid #9333ea",
                    }} />
                  </div>
                )
              )}
            </div>
          ))}
        </div>

        {/* Bottom label */}
        <div style={{
          marginTop: isMobile ? "16px" : "24px",
          textAlign: "center",
          opacity: interpolate(frame, [80, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}>
          <div style={{
            fontSize: isMobile ? "12px" : "14px",
            color: "#9333ea",
            textTransform: "uppercase",
            letterSpacing: "2px",
          }}>
            Zero Calibration Required
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
