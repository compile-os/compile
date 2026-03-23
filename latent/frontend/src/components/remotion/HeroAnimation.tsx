"use client";

import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

export const HeroAnimation: React.FC = () => {
  const frame = useCurrentFrame();

  // Pulsing neural network visualization
  const pulse = interpolate(Math.sin(frame * 0.05), [-1, 1], [0.6, 1]);
  const rotation = interpolate(frame, [0, 600], [0, 360]);

  // Node positions in a brain-like cluster
  const nodes = [
    { x: 50, y: 50, size: 8, delay: 0 },
    { x: 30, y: 35, size: 6, delay: 10 },
    { x: 70, y: 35, size: 6, delay: 20 },
    { x: 40, y: 65, size: 7, delay: 15 },
    { x: 60, y: 65, size: 7, delay: 25 },
    { x: 25, y: 55, size: 5, delay: 30 },
    { x: 75, y: 55, size: 5, delay: 35 },
    { x: 50, y: 25, size: 5, delay: 40 },
    { x: 35, y: 80, size: 4, delay: 45 },
    { x: 65, y: 80, size: 4, delay: 50 },
    { x: 20, y: 40, size: 4, delay: 55 },
    { x: 80, y: 40, size: 4, delay: 60 },
    { x: 50, y: 75, size: 6, delay: 5 },
  ];

  // Connections between nodes
  const connections = [
    [0, 1], [0, 2], [0, 3], [0, 4], [0, 7], [0, 12],
    [1, 5], [1, 3], [2, 6], [2, 4],
    [3, 8], [4, 9], [3, 12], [4, 12],
    [5, 10], [6, 11], [7, 1], [7, 2],
  ];

  // Signal particles traveling along connections
  const signalProgress = (frame % 120) / 120;

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      <svg viewBox="0 0 100 100" style={{ width: "100%", height: "100%" }}>
        {/* Outer glow circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="url(#purpleGradient)"
          strokeWidth="0.5"
          opacity={0.3}
          style={{
            transform: `rotate(${rotation}deg)`,
            transformOrigin: "50px 50px",
          }}
          strokeDasharray="10 5"
        />

        {/* Inner glow */}
        <circle
          cx="50"
          cy="50"
          r="35"
          fill="url(#radialGlow)"
          opacity={pulse * 0.3}
        />

        {/* Connections */}
        {connections.map(([from, to], i) => {
          const fromNode = nodes[from];
          const toNode = nodes[to];
          const connectionPulse = interpolate(
            Math.sin(frame * 0.08 + i * 0.5),
            [-1, 1],
            [0.2, 0.6]
          );

          return (
            <g key={`conn-${i}`}>
              <line
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke="#9333ea"
                strokeWidth="0.3"
                opacity={connectionPulse}
              />
              {/* Traveling signal */}
              {((signalProgress * connections.length + i) % connections.length) < 1 && (
                <circle
                  cx={fromNode.x + (toNode.x - fromNode.x) * ((signalProgress * connections.length + i) % 1)}
                  cy={fromNode.y + (toNode.y - fromNode.y) * ((signalProgress * connections.length + i) % 1)}
                  r="1.5"
                  fill="#c084fc"
                  opacity={0.8}
                >
                  <animate
                    attributeName="r"
                    values="1;2;1"
                    dur="0.5s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node, i) => {
          const nodeScale = interpolate(
            Math.sin(frame * 0.1 + node.delay * 0.1),
            [-1, 1],
            [0.8, 1.2]
          );
          const nodeOpacity = interpolate(
            frame - node.delay,
            [0, 30],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          return (
            <g key={`node-${i}`} opacity={nodeOpacity}>
              {/* Glow */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size * 2}
                fill="url(#nodeGlow)"
                opacity={0.3 * nodeScale}
              />
              {/* Core */}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size * nodeScale * 0.5}
                fill="#9333ea"
              />
              {/* Highlight */}
              <circle
                cx={node.x - node.size * 0.15}
                cy={node.y - node.size * 0.15}
                r={node.size * 0.15}
                fill="white"
                opacity={0.5}
              />
            </g>
          );
        })}

        {/* Gradients */}
        <defs>
          <linearGradient id="purpleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#9333ea" />
            <stop offset="50%" stopColor="#c084fc" />
            <stop offset="100%" stopColor="#9333ea" />
          </linearGradient>
          <radialGradient id="radialGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#9333ea" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#9333ea" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#c084fc" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#9333ea" stopOpacity="0" />
          </radialGradient>
        </defs>
      </svg>
    </AbsoluteFill>
  );
};
