"use client";

import React, { useRef, useState, useMemo, useEffect, Suspense } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls, Html, Float } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";

// Brain region mapping - distinct colors for each region, more muted/organic look
const BRAIN_REGIONS: Record<string, {
  name: string;
  description: string;
  function: string;
  color: string;
  baseColor: string;
}> = {
  frontal: {
    name: "Frontal Lobe",
    description: "Executive functions, motor control, speech production",
    function: "Planning, decision-making, working memory",
    color: "#a855f7",  // Vibrant purple
    baseColor: "#ddd6fe", // Light violet
  },
  pariet: {
    name: "Parietal Lobe",
    description: "Sensory integration, spatial processing",
    function: "Touch, pressure, proprioception",
    color: "#6366f1",  // Indigo
    baseColor: "#c7d2fe", // Light indigo
  },
  temp: {
    name: "Temporal Lobe",
    description: "Auditory processing, memory, language",
    function: "Hearing, speech comprehension",
    color: "#14b8a6",  // Teal
    baseColor: "#99f6e4", // Light teal
  },
  occipit: {
    name: "Occipital Lobe",
    description: "Visual processing center",
    function: "Vision, object recognition",
    color: "#3b82f6",  // Blue
    baseColor: "#bfdbfe", // Light blue
  },
  cereb: {
    name: "Cerebellum",
    description: "Motor coordination, balance",
    function: "Fine motor control, posture",
    color: "#ec4899",  // Pink
    baseColor: "#fbcfe8", // Light pink
  },
  stem: {
    name: "Brain Stem",
    description: "Vital autonomic functions",
    function: "Heart rate, breathing, consciousness",
    color: "#8b5cf6",  // Violet
    baseColor: "#c4b5fd", // Light violet
  },
  corpus: {
    name: "Corpus Callosum",
    description: "Connects left and right hemispheres",
    function: "Inter-hemispheric communication",
    color: "#06b6d4",  // Cyan
    baseColor: "#a5f3fc", // Light cyan
  },
  pitua: {
    name: "Pituitary Gland",
    description: "Master endocrine gland",
    function: "Hormone regulation",
    color: "#f97316",  // Orange
    baseColor: "#fed7aa", // Light orange
  },
};

export type BrainRegionKey = keyof typeof BRAIN_REGIONS;

// Get region key from mesh name
function getRegionFromMeshName(name: string): BrainRegionKey | null {
  const lowerName = name.toLowerCase();
  for (const key of Object.keys(BRAIN_REGIONS)) {
    if (lowerName.includes(key)) {
      return key as BrainRegionKey;
    }
  }
  return null;
}

// Individual brain part mesh - memoized to prevent re-renders
const BrainPart = React.memo(function BrainPart({
  mesh,
  regionKey,
  isHovered,
  onHover,
}: {
  mesh: THREE.Mesh;
  regionKey: BrainRegionKey;
  isHovered: boolean;
  onHover: (region: BrainRegionKey | null) => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const region = BRAIN_REGIONS[regionKey];

  // Pre-allocate target vector to avoid creating objects in useFrame
  const targetScale = useRef(new THREE.Vector3(1, 1, 1));

  // Create materials - organic matte look with subtle sheen
  const baseMaterial = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: region.baseColor,
      transparent: true,
      opacity: 0.9,
      roughness: 0.7,
      metalness: 0.0,
      side: THREE.DoubleSide,
      emissive: region.color,
      emissiveIntensity: 0.03,
    });
  }, [region]);

  const hoverMaterial = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: region.color,
      transparent: true,
      opacity: 0.95,
      roughness: 0.5,
      metalness: 0.0,
      side: THREE.DoubleSide,
      emissive: region.color,
      emissiveIntensity: 0.2,
    });
  }, [region]);

  // Animate on hover - optimized to avoid object creation
  useFrame((state) => {
    if (meshRef.current) {
      const scale = isHovered ? 1.03 : 1;
      targetScale.current.set(scale, scale, scale);
      meshRef.current.scale.lerp(targetScale.current, 0.15);

      // Pulse effect when hovered
      if (isHovered) {
        const pulse = 0.3 + Math.sin(state.clock.elapsedTime * 4) * 0.15;
        (meshRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = pulse;
      }
    }
  });

  return (
    <mesh
      ref={meshRef}
      geometry={mesh.geometry}
      material={isHovered ? hoverMaterial : baseMaterial}
      onPointerEnter={(e) => {
        e.stopPropagation();
        onHover(regionKey);
        document.body.style.cursor = "pointer";
      }}
      onPointerLeave={(e) => {
        e.stopPropagation();
        onHover(null);
        document.body.style.cursor = "auto";
      }}
    />
  );
});

// Brain model with segmented parts
function SegmentedBrain({
  hoveredRegion,
  onHover,
}: {
  hoveredRegion: BrainRegionKey | null;
  onHover: (region: BrainRegionKey | null) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const obj = useLoader(OBJLoader, "/models/brain-parts-big.obj");

  // Extract meshes with their region assignments and pre-compute bounding boxes
  const { brainParts, regionCenters } = useMemo(() => {
    const parts: { mesh: THREE.Mesh; regionKey: BrainRegionKey }[] = [];
    const centers: Record<BrainRegionKey, THREE.Vector3> = {} as Record<BrainRegionKey, THREE.Vector3>;
    const regionMeshCenters: Record<BrainRegionKey, { sum: THREE.Vector3; count: number }> = {} as Record<BrainRegionKey, { sum: THREE.Vector3; count: number }>;

    obj.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const regionKey = getRegionFromMeshName(child.name);
        if (regionKey) {
          parts.push({ mesh: child, regionKey });

          // Pre-compute bounding box center for this mesh
          child.geometry.computeBoundingBox();
          const box = child.geometry.boundingBox;
          if (box) {
            const meshCenter = new THREE.Vector3();
            box.getCenter(meshCenter);

            if (!regionMeshCenters[regionKey]) {
              regionMeshCenters[regionKey] = { sum: new THREE.Vector3(), count: 0 };
            }
            regionMeshCenters[regionKey].sum.add(meshCenter);
            regionMeshCenters[regionKey].count++;
          }
        }
      }
    });

    // Calculate final centers for each region
    for (const [key, data] of Object.entries(regionMeshCenters)) {
      const center = data.sum.divideScalar(data.count);
      center.y += 50; // Offset upward for tooltip
      centers[key as BrainRegionKey] = center;
    }

    return { brainParts: parts, regionCenters: centers };
  }, [obj]);

  // Auto-rotate
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.002;
    }
  });

  // Get cached tooltip position - no computation needed
  const tooltipPosition = hoveredRegion ? regionCenters[hoveredRegion] : null;

  return (
    <group ref={groupRef} scale={[0.008, 0.008, 0.008]} position={[0, 0, 0]}>
      {brainParts.map(({ mesh, regionKey }, index) => (
        <BrainPart
          key={`${regionKey}-${index}`}
          mesh={mesh}
          regionKey={regionKey}
          isHovered={hoveredRegion === regionKey}
          onHover={onHover}
        />
      ))}

      {/* Tooltip */}
      {hoveredRegion && tooltipPosition && (
        <Html
          position={[tooltipPosition.x, tooltipPosition.y, tooltipPosition.z]}
          center
          style={{ pointerEvents: "none", whiteSpace: "nowrap" }}
        >
          <div className="bg-black/90 backdrop-blur-xl px-5 py-3 rounded-xl border border-white/20 shadow-2xl min-w-56">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: BRAIN_REGIONS[hoveredRegion].color }}
              />
              <span className="text-white font-semibold text-sm">
                {BRAIN_REGIONS[hoveredRegion].name}
              </span>
            </div>
            <p className="text-gray-300 text-xs leading-relaxed mb-2">
              {BRAIN_REGIONS[hoveredRegion].description}
            </p>
            <div className="text-gray-500 text-xs border-t border-white/10 pt-2 mt-2">
              <span className="text-purple-400 font-medium">Function:</span>{" "}
              {BRAIN_REGIONS[hoveredRegion].function}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

// Projection streamlines - fiber tracts connecting brain regions - memoized
const ProjectionStreamlines = React.memo(function ProjectionStreamlines() {
  const linesRef = useRef<THREE.Group>(null);

  const streamlines = useMemo(() => {
    const lines: { points: THREE.Vector3[]; color: THREE.Color }[] = [];

    // Define major fiber tract pathways
    const pathways = [
      { start: [0, 0.3, 0.8], end: [0, -0.5, -0.5], color: "#c084fc" },  // Frontal to cerebellum
      { start: [-0.8, 0, 0.3], end: [0.8, 0, 0.3], color: "#a78bfa" },   // Corpus callosum
      { start: [0, 0.5, 0.5], end: [0, -0.8, 0], color: "#818cf8" },     // Motor pathway
      { start: [0.6, -0.2, 0.2], end: [0, 0.3, -0.8], color: "#a5b4fc" }, // Temporal to occipital
      { start: [-0.6, -0.2, 0.2], end: [0, 0.3, -0.8], color: "#f0abfc" },
    ];

    pathways.forEach(({ start, end, color }) => {
      // Create curved path with bezier-like interpolation
      const points: THREE.Vector3[] = [];
      const startVec = new THREE.Vector3(...start);
      const endVec = new THREE.Vector3(...end);
      const mid = startVec.clone().add(endVec).multiplyScalar(0.5);
      mid.y += 0.3; // Arc upward

      for (let t = 0; t <= 1; t += 0.05) {
        const p = new THREE.Vector3();
        // Quadratic bezier
        p.x = (1 - t) * (1 - t) * startVec.x + 2 * (1 - t) * t * mid.x + t * t * endVec.x;
        p.y = (1 - t) * (1 - t) * startVec.y + 2 * (1 - t) * t * mid.y + t * t * endVec.y;
        p.z = (1 - t) * (1 - t) * startVec.z + 2 * (1 - t) * t * mid.z + t * t * endVec.z;
        // Add slight noise for organic feel
        p.x += (Math.random() - 0.5) * 0.02;
        p.y += (Math.random() - 0.5) * 0.02;
        p.z += (Math.random() - 0.5) * 0.02;
        points.push(p);
      }

      lines.push({ points, color: new THREE.Color(color) });
    });

    return lines;
  }, []);

  useFrame((state) => {
    if (linesRef.current) {
      linesRef.current.children.forEach((child, i) => {
        if (child instanceof THREE.Line) {
          const mat = child.material as THREE.LineBasicMaterial;
          mat.opacity = 0.2 + Math.sin(state.clock.elapsedTime * 2 + i * 0.5) * 0.1;
        }
      });
    }
  });

  return (
    <group ref={linesRef}>
      {streamlines.map((line, i) => {
        const positions = new Float32Array(line.points.flatMap(p => [p.x, p.y, p.z]));
        return (
          <line key={i}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[positions, 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial
              color={line.color}
              transparent
              opacity={0.25}
              blending={THREE.AdditiveBlending}
            />
          </line>
        );
      })}
    </group>
  );
});

// Single neuron morphology visualization - memoized
const NeuronMorphology = React.memo(function NeuronMorphology() {
  const groupRef = useRef<THREE.Group>(null);

  // Generate a realistic neuron structure
  const neuronData = useMemo(() => {
    const soma = new THREE.Vector3(0.5, 0.2, 0.4);
    const dendrites: THREE.Vector3[][] = [];
    const axon: THREE.Vector3[] = [];

    // Generate dendritic tree (branching structure)
    for (let branch = 0; branch < 5; branch++) {
      const dendrite: THREE.Vector3[] = [soma.clone()];
      let current = soma.clone();
      const angle = (branch / 5) * Math.PI * 2;

      for (let seg = 0; seg < 8; seg++) {
        const next = current.clone();
        next.x += Math.cos(angle + Math.random() * 0.5) * 0.08;
        next.y += (Math.random() - 0.3) * 0.06;
        next.z += Math.sin(angle + Math.random() * 0.5) * 0.08;
        dendrite.push(next);
        current = next;
      }
      dendrites.push(dendrite);
    }

    // Generate axon (single long projection)
    let axonPoint = soma.clone();
    axon.push(axonPoint.clone());
    for (let i = 0; i < 15; i++) {
      axonPoint = axonPoint.clone();
      axonPoint.y -= 0.06;
      axonPoint.x += (Math.random() - 0.5) * 0.03;
      axonPoint.z += (Math.random() - 0.5) * 0.03;
      axon.push(axonPoint);
    }

    return { soma, dendrites, axon };
  }, []);

  useFrame((state) => {
    if (groupRef.current) {
      // Subtle pulse animation
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.02;
      groupRef.current.scale.setScalar(scale);
    }
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Soma (cell body) */}
      <mesh position={neuronData.soma}>
        <sphereGeometry args={[0.04, 16, 16]} />
        <meshBasicMaterial color="#e879f9" transparent opacity={0.8} />
      </mesh>

      {/* Dendrites */}
      {neuronData.dendrites.map((dendrite, i) => {
        const positions = new Float32Array(dendrite.flatMap(p => [p.x, p.y, p.z]));
        return (
          <line key={`dendrite-${i}`}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[positions, 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#c084fc" transparent opacity={0.6} linewidth={2} />
          </line>
        );
      })}

      {/* Axon */}
      {(() => {
        const axonPositions = new Float32Array(neuronData.axon.flatMap(p => [p.x, p.y, p.z]));
        return (
          <line>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[axonPositions, 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#f0abfc" transparent opacity={0.7} />
          </line>
        );
      })()}
    </group>
  );
});

// Gene expression heatmap overlay - memoized
const GeneExpressionOverlay = React.memo(function GeneExpressionOverlay({ hoveredRegion }: { hoveredRegion: BrainRegionKey | null }) {
  const meshRef = useRef<THREE.Points>(null);
  const count = 200;

  const { positions, intensities } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const int = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Distribute within brain volume
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 0.3 + Math.random() * 0.7;

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.8;
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Gene expression intensity (simulated)
      int[i] = Math.random();
    }

    return { positions: pos, intensities: int };
  }, []);

  useFrame((state) => {
    if (meshRef.current) {
      const mat = meshRef.current.material as THREE.PointsMaterial;
      // Pulse based on hover
      mat.opacity = hoveredRegion
        ? 0.6 + Math.sin(state.clock.elapsedTime * 4) * 0.2
        : 0.3 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
    }
  });

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    // Color based on intensity (purple gradient)
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const color = new THREE.Color();
      color.setHSL(0.8 - intensities[i] * 0.15, 0.8, 0.3 + intensities[i] * 0.4);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    return geo;
  }, [positions, intensities]);

  return (
    <points ref={meshRef} geometry={geometry}>
      <pointsMaterial
        size={0.015}
        vertexColors
        transparent
        opacity={0.4}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
});

// Neural activity particles - works in both light and dark mode - memoized
const NeuralParticles = React.memo(function NeuralParticles() {
  const particlesRef = useRef<THREE.Points>(null);
  const count = 200;

  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const color = new THREE.Color();

    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.3 + Math.random() * 0.4;

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.8;
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Purple/violet colors that work on both backgrounds
      const hue = 0.75 + (Math.random() - 0.5) * 0.1;
      color.setHSL(hue, 0.7, 0.5); // More saturated, medium lightness
      col[i * 3] = color.r;
      col[i * 3 + 1] = color.g;
      col[i * 3 + 2] = color.b;
    }

    return { positions: pos, colors: col };
  }, []);

  useFrame((state) => {
    if (particlesRef.current) {
      particlesRef.current.rotation.y += 0.0005;
      const mat = particlesRef.current.material as THREE.PointsMaterial;
      mat.opacity = 0.6 + Math.sin(state.clock.elapsedTime * 1.2) * 0.2;
    }
  });

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return geo;
  }, [positions, colors]);

  return (
    <points ref={particlesRef} geometry={geometry}>
      <pointsMaterial
        size={0.02}
        vertexColors
        transparent
        opacity={0.7}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
});

// Loading fallback
function LoadingFallback() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.02;
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1, 2]} />
      <meshBasicMaterial color="#8b5cf6" wireframe transparent opacity={0.3} />
    </mesh>
  );
}

// Main brain scene
function BrainScene({
  onHoveredRegion,
  showParticles = true,
  showStreamlines = true,
  showNeuron = true,
  showGeneExpression = true,
}: {
  onHoveredRegion?: (region: BrainRegionKey | null) => void;
  showParticles?: boolean;
  showStreamlines?: boolean;
  showNeuron?: boolean;
  showGeneExpression?: boolean;
}) {
  const [hoveredRegion, setHoveredRegion] = useState<BrainRegionKey | null>(null);

  const handleHover = (region: BrainRegionKey | null) => {
    setHoveredRegion(region);
    onHoveredRegion?.(region);
  };

  return (
    <>
      {showParticles && <NeuralParticles />}
      {showStreamlines && <ProjectionStreamlines />}
      {showNeuron && <NeuronMorphology />}
      {showGeneExpression && <GeneExpressionOverlay hoveredRegion={hoveredRegion} />}
      <Suspense fallback={<LoadingFallback />}>
        <SegmentedBrain hoveredRegion={hoveredRegion} onHover={handleHover} />
      </Suspense>
    </>
  );
}

// Post-processing effects - wrapped in try/catch for SSR safety
function Effects() {
  try {
    return (
      <EffectComposer>
        <Bloom
          luminanceThreshold={0.2}
          luminanceSmoothing={0.9}
          intensity={0.6}
          radius={0.7}
        />
        <Vignette eskil={false} offset={0.1} darkness={0.3} />
      </EffectComposer>
    );
  } catch {
    return null;
  }
}

// Export types
export type BrainLabelKey = BrainRegionKey;
export const BRAIN_LABELS = BRAIN_REGIONS;

// Export: Full-featured Brain3D component
export interface Brain3DProps {
  className?: string;
  onHoveredRegion?: (region: BrainRegionKey | null) => void;
  showLabels?: boolean;
  showParticles?: boolean;
  showStreamlines?: boolean;
  showNeuron?: boolean;
  showGeneExpression?: boolean;
  enableZoom?: boolean;
  enablePan?: boolean;
  floatIntensity?: number;
  autoRotate?: boolean;
  regionOpacity?: number;
  showNetwork?: boolean;
}

export function Brain3D({
  className = "",
  onHoveredRegion,
  showParticles = true,
  showStreamlines = false,  // Disabled by default - can enable for detailed view
  showNeuron = false,       // Disabled by default - can enable for detailed view
  showGeneExpression = false, // Disabled by default - can enable for detailed view
  enableZoom = false,
  enablePan = false,
  floatIntensity = 0.3,
}: Brain3DProps) {
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 4], fov: 45 }}
        dpr={[1, 2]} // Limit pixel ratio to max 2x for performance
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
          stencil: false, // Disable stencil buffer if not needed
          depth: true,
        }}
        style={{ background: "transparent" }}
        performance={{ min: 0.5 }} // Allow adaptive performance
      >
        {/* Fog for depth */}
        <fog attach="fog" args={["#000000", 5, 12]} />

        {/* Lighting - purple-tinted for cohesive look */}
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 5, 5]} intensity={0.6} color="#ffffff" />
        <directionalLight position={[-5, -2, 5]} intensity={0.4} color="#c084fc" />
        <directionalLight position={[0, -5, -5]} intensity={0.3} color="#a78bfa" />
        <pointLight position={[0, 2, 2]} intensity={0.4} color="#f0abfc" distance={10} />
        <pointLight position={[2, 0, 0]} intensity={0.2} color="#818cf8" distance={8} />

        {/* Brain with floating effect */}
        <Float
          speed={1.5}
          rotationIntensity={0.1}
          floatIntensity={floatIntensity}
        >
          <BrainScene
            onHoveredRegion={onHoveredRegion}
            showParticles={showParticles}
            showStreamlines={showStreamlines}
            showNeuron={showNeuron}
            showGeneExpression={showGeneExpression}
          />
        </Float>

        {/* Post-processing disabled for stability */}
        {/* <Effects /> */}

        {/* Controls */}
        <OrbitControls
          enableZoom={enableZoom}
          enablePan={enablePan}
          autoRotate={false}
          minPolarAngle={Math.PI / 5}
          maxPolarAngle={(Math.PI * 4) / 5}
          minDistance={2.5}
          maxDistance={6}
        />
      </Canvas>
    </div>
  );
}

export default Brain3D;
