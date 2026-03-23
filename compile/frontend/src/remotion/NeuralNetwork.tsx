"use client";

import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";
import { useMemo } from "react";

interface Neuron {
  id: number;
  x: number;
  y: number;
  radius: number;
  pulseDelay: number;
  connections: number[];
}

interface Signal {
  from: number;
  to: number;
  delay: number;
  speed: number;
}

// Generate a neural network layout
function generateNetwork(nodeCount: number, width: number, height: number, seed: number): Neuron[] {
  const neurons: Neuron[] = [];
  const random = (i: number) => {
    const x = Math.sin(seed + i * 9999) * 10000;
    return x - Math.floor(x);
  };

  // Create neurons in clusters (like brain regions)
  for (let i = 0; i < nodeCount; i++) {
    const cluster = Math.floor(i / (nodeCount / 4));
    const clusterCenterX = width * (0.2 + (cluster % 2) * 0.6);
    const clusterCenterY = height * (0.3 + Math.floor(cluster / 2) * 0.4);

    const angle = random(i) * Math.PI * 2;
    const distance = random(i + 100) * 150 + 50;

    neurons.push({
      id: i,
      x: clusterCenterX + Math.cos(angle) * distance,
      y: clusterCenterY + Math.sin(angle) * distance,
      radius: 3 + random(i + 200) * 4,
      pulseDelay: random(i + 300) * 60,
      connections: [],
    });
  }

  // Create connections (synapses)
  for (let i = 0; i < neurons.length; i++) {
    const connectionCount = Math.floor(random(i + 400) * 4) + 1;
    for (let j = 0; j < connectionCount; j++) {
      const targetIndex = Math.floor(random(i * 10 + j) * neurons.length);
      if (targetIndex !== i && !neurons[i].connections.includes(targetIndex)) {
        const dx = neurons[targetIndex].x - neurons[i].x;
        const dy = neurons[targetIndex].y - neurons[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 300) {
          neurons[i].connections.push(targetIndex);
        }
      }
    }
  }

  return neurons;
}

// Generate signal pulses
function generateSignals(neurons: Neuron[], count: number, seed: number): Signal[] {
  const signals: Signal[] = [];
  const random = (i: number) => {
    const x = Math.sin(seed + i * 7777) * 10000;
    return x - Math.floor(x);
  };

  let signalIndex = 0;
  for (let i = 0; i < neurons.length && signalIndex < count; i++) {
    for (const conn of neurons[i].connections) {
      if (signalIndex >= count) break;
      signals.push({
        from: i,
        to: conn,
        delay: random(signalIndex) * 120,
        speed: 0.5 + random(signalIndex + 1000) * 1,
      });
      signalIndex++;
    }
  }

  return signals;
}

export const NeuralNetwork: React.FC<{
  width?: number;
  height?: number;
  nodeCount?: number;
  color?: string;
  glowColor?: string;
}> = ({
  width = 1920,
  height = 1080,
  nodeCount = 60,
  color = "#a855f7",
  glowColor = "#c084fc",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const neurons = useMemo(() => generateNetwork(nodeCount, width, height, 12345), [nodeCount, width, height]);
  const signals = useMemo(() => generateSignals(neurons, 100, 54321), [neurons]);

  // Looping frame for continuous animation
  const loopDuration = 180; // 3 seconds at 60fps
  const loopFrame = frame % loopDuration;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ background: "transparent" }}
    >
      <defs>
        {/* Glow filter */}
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Stronger glow for active elements */}
        <filter id="strongGlow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="8" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Gradient for connections */}
        <linearGradient id="connectionGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0.1" />
          <stop offset="50%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.1" />
        </linearGradient>

        {/* Radial gradient for neurons */}
        <radialGradient id="neuronGradient">
          <stop offset="0%" stopColor={glowColor} />
          <stop offset="70%" stopColor={color} />
          <stop offset="100%" stopColor={color} stopOpacity="0.5" />
        </radialGradient>
      </defs>

      {/* Connections (synapses) */}
      <g opacity="0.6">
        {neurons.map((neuron) =>
          neuron.connections.map((targetId) => {
            const target = neurons[targetId];
            return (
              <line
                key={`${neuron.id}-${targetId}`}
                x1={neuron.x}
                y1={neuron.y}
                x2={target.x}
                y2={target.y}
                stroke={color}
                strokeWidth="1"
                opacity="0.3"
              />
            );
          })
        )}
      </g>

      {/* Signal pulses traveling along connections */}
      <g>
        {signals.map((signal, index) => {
          const fromNeuron = neurons[signal.from];
          const toNeuron = neurons[signal.to];

          const signalFrame = (loopFrame - signal.delay + loopDuration) % loopDuration;
          const progress = interpolate(
            signalFrame,
            [0, loopDuration * signal.speed],
            [0, 1],
            { extrapolateRight: "clamp" }
          );

          if (progress <= 0 || progress >= 1) return null;

          const x = fromNeuron.x + (toNeuron.x - fromNeuron.x) * progress;
          const y = fromNeuron.y + (toNeuron.y - fromNeuron.y) * progress;

          const pulseOpacity = Math.sin(progress * Math.PI);

          return (
            <circle
              key={`signal-${index}`}
              cx={x}
              cy={y}
              r={4}
              fill={glowColor}
              opacity={pulseOpacity * 0.9}
              filter="url(#strongGlow)"
            />
          );
        })}
      </g>

      {/* Neurons */}
      <g>
        {neurons.map((neuron) => {
          // Pulsing animation
          const pulseFrame = (loopFrame + neuron.pulseDelay) % 90;
          const pulse = interpolate(
            pulseFrame,
            [0, 30, 60, 90],
            [1, 1.3, 1, 1],
            { extrapolateRight: "clamp" }
          );

          const glowOpacity = interpolate(
            pulseFrame,
            [0, 30, 60, 90],
            [0.4, 0.8, 0.4, 0.4],
            { extrapolateRight: "clamp" }
          );

          return (
            <g key={neuron.id}>
              {/* Outer glow */}
              <circle
                cx={neuron.x}
                cy={neuron.y}
                r={neuron.radius * pulse * 2}
                fill={color}
                opacity={glowOpacity * 0.3}
                filter="url(#glow)"
              />
              {/* Core */}
              <circle
                cx={neuron.x}
                cy={neuron.y}
                r={neuron.radius * pulse}
                fill="url(#neuronGradient)"
                filter="url(#glow)"
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
};

export default NeuralNetwork;
