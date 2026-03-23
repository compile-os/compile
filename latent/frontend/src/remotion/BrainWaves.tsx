"use client";

import { useCurrentFrame, interpolate } from "remotion";
import { useMemo } from "react";

interface WaveConfig {
  amplitude: number;
  frequency: number;
  phase: number;
  speed: number;
  color: string;
  opacity: number;
  strokeWidth: number;
}

export const BrainWaves: React.FC<{
  width?: number;
  height?: number;
  waveCount?: number;
  baseColor?: string;
}> = ({
  width = 1920,
  height = 400,
  waveCount = 5,
  baseColor = "#a855f7",
}) => {
  const frame = useCurrentFrame();

  const waves: WaveConfig[] = useMemo(() => {
    const colors = [
      "#a855f7", // purple
      "#ec4899", // pink
      "#8b5cf6", // violet
      "#c084fc", // light purple
      "#f472b6", // light pink
    ];

    return Array.from({ length: waveCount }, (_, i) => ({
      amplitude: 30 + i * 15,
      frequency: 0.005 + i * 0.002,
      phase: i * 0.5,
      speed: 0.02 + i * 0.01,
      color: colors[i % colors.length],
      opacity: 0.6 - i * 0.08,
      strokeWidth: 3 - i * 0.3,
    }));
  }, [waveCount]);

  const generateWavePath = (wave: WaveConfig, time: number): string => {
    const points: string[] = [];
    const centerY = height / 2;

    for (let x = 0; x <= width; x += 5) {
      // Combine multiple sine waves for more organic look
      const y1 = Math.sin(x * wave.frequency + time * wave.speed + wave.phase) * wave.amplitude;
      const y2 = Math.sin(x * wave.frequency * 2.3 + time * wave.speed * 1.5) * (wave.amplitude * 0.3);
      const y3 = Math.sin(x * wave.frequency * 0.7 + time * wave.speed * 0.8) * (wave.amplitude * 0.5);

      // Add some "spike" patterns like real EEG
      const spike = Math.random() > 0.995 ? (Math.random() - 0.5) * wave.amplitude * 2 : 0;

      const y = centerY + y1 + y2 + y3 + spike;

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
      style={{ background: "transparent" }}
    >
      <defs>
        <filter id="waveGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={baseColor} stopOpacity="0" />
          <stop offset="20%" stopColor={baseColor} stopOpacity="1" />
          <stop offset="80%" stopColor={baseColor} stopOpacity="1" />
          <stop offset="100%" stopColor={baseColor} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Grid lines (like EEG paper) */}
      <g opacity="0.1">
        {Array.from({ length: Math.floor(height / 40) }, (_, i) => (
          <line
            key={`h-${i}`}
            x1={0}
            y1={i * 40}
            x2={width}
            y2={i * 40}
            stroke={baseColor}
            strokeWidth="1"
          />
        ))}
        {Array.from({ length: Math.floor(width / 40) }, (_, i) => (
          <line
            key={`v-${i}`}
            x1={i * 40}
            y1={0}
            x2={i * 40}
            y2={height}
            stroke={baseColor}
            strokeWidth="1"
          />
        ))}
      </g>

      {/* Waves */}
      {waves.map((wave, index) => (
        <path
          key={index}
          d={generateWavePath(wave, frame)}
          fill="none"
          stroke={wave.color}
          strokeWidth={wave.strokeWidth}
          opacity={wave.opacity}
          filter="url(#waveGlow)"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}

      {/* Scanning line effect */}
      <rect
        x={interpolate(frame % 180, [0, 180], [0, width])}
        y={0}
        width={100}
        height={height}
        fill="url(#waveGradient)"
        opacity={0.15}
      />
    </svg>
  );
};

export default BrainWaves;
