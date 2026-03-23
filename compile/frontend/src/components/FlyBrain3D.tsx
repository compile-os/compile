"use client";

import React, {
  useRef,
  useState,
  useMemo,
  useEffect,
  useCallback,
  Suspense,
} from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls, Html, Float } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";

import { fetchModules, fetchThreeLayerMap, fetchFitnessFunctions } from "@/lib/api";
import type {
  CompileModule,
  ThreeLayerMap,
  FitnessFunction,
  OSLayerPair,
  AppLayerPair,
} from "@/types/compile";
import { ROLE_COLORS, BEHAVIOR_COLORS } from "@/types/compile";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface FlyBrain3DProps {
  className?: string;
  selectedBehaviors: string[];
  onModuleClick?: (moduleId: number) => void;
  onModuleHover?: (moduleId: number | null) => void;
  autoRotate?: boolean;
  enableZoom?: boolean;
  enablePan?: boolean;
}

// ---------------------------------------------------------------------------
// Deterministic seeded random (mulberry32)
// ---------------------------------------------------------------------------

function seededRandom(seed: number) {
  let t = (seed + 0x6d2b79f5) | 0;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

// ---------------------------------------------------------------------------
// Position generation: place modules according to fly brain anatomy
// ---------------------------------------------------------------------------

function computeModulePosition(mod: CompileModule): [number, number, number] {
  const rng1 = seededRandom(mod.id * 137 + 1);
  const rng2 = seededRandom(mod.id * 137 + 2);
  const rng3 = seededRandom(mod.id * 137 + 3);

  const jx = (rng1 - 0.5) * 0.6;
  const jy = (rng2 - 0.5) * 0.6;
  const jz = (rng3 - 0.5) * 0.6;

  const group = mod.top_group || "";

  // Scale everything to fit inside the brain mesh (~3 unit radius)
  const s = 0.4; // global scale-down

  // Optic lobe modules - spread laterally (left/right)
  if (group.startsWith("ME") || group.startsWith("LO")) {
    const side = mod.id % 2 === 0 ? 1 : -1;
    const spread = 1.2 + rng1 * 1.2;
    return [side * spread * s, jy * 0.5 * s, jz * 0.4 * s];
  }

  // Central modules
  if (
    group.includes("AL") ||
    group.includes("FB") ||
    group.includes("AVLP") ||
    group.includes("GNG")
  ) {
    return [jx * 0.6 * s, jy * 0.6 * s, jz * 0.6 * s];
  }

  // Core sensory modules - bottom layer
  if (mod.role === "core" && mod.top_super_class === "sensory") {
    return [jx * 1.5 * s, (-1.0 + jy * 0.4) * s, jz * 0.6 * s];
  }

  // Source modules - upper back
  if (mod.role === "source") {
    return [jx * 1.8 * s, (0.6 + jy * 0.5) * s, (-0.8 + jz * 0.3) * s];
  }

  // Sink modules - lower front
  if (mod.role === "sink") {
    return [jx * 1.8 * s, (-0.6 + jy * 0.5) * s, (0.8 + jz * 0.3) * s];
  }

  // Default spread
  const angle = seededRandom(mod.id * 53) * Math.PI * 2;
  const r = 0.8 + rng1 * 0.8;
  return [
    Math.cos(angle) * r * s + jx * 0.3 * s,
    jy * s,
    Math.sin(angle) * r * s + jz * 0.3 * s,
  ];
}

// ---------------------------------------------------------------------------
// ModuleSphere sub-component
// ---------------------------------------------------------------------------

const ModuleSphere = React.memo(function ModuleSphere({
  module: mod,
  position,
  isHovered,
  onHover,
  onClick,
}: {
  module: CompileModule;
  position: [number, number, number];
  isHovered: boolean;
  onHover: (id: number | null) => void;
  onClick: (id: number) => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const targetScale = useRef(new THREE.Vector3(1, 1, 1));
  const roleColor = ROLE_COLORS[mod.role] || "#6b7280";
  const radius = 0.06 + Math.sqrt(mod.n_neurons) / 500;

  const baseMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: roleColor,
        transparent: true,
        opacity: 0.92,
        roughness: 0.35,
        metalness: 0.15,
        emissive: roleColor,
        emissiveIntensity: 0.08,
      }),
    [roleColor]
  );

  const hoverMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: roleColor,
        transparent: true,
        opacity: 1,
        roughness: 0.2,
        metalness: 0.2,
        emissive: roleColor,
        emissiveIntensity: 0.45,
      }),
    [roleColor]
  );

  useFrame((state) => {
    if (!meshRef.current) return;
    const s = isHovered ? 1.15 : 1;
    targetScale.current.set(s, s, s);
    meshRef.current.scale.lerp(targetScale.current, 0.15);

    if (isHovered) {
      const pulse = 0.45 + Math.sin(state.clock.elapsedTime * 4) * 0.2;
      (meshRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity = pulse;
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={position}
      material={isHovered ? hoverMaterial : baseMaterial}
      onPointerEnter={(e) => {
        e.stopPropagation();
        onHover(mod.id);
        document.body.style.cursor = "pointer";
      }}
      onPointerLeave={(e) => {
        e.stopPropagation();
        onHover(null);
        document.body.style.cursor = "auto";
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClick(mod.id);
      }}
    >
      <sphereGeometry args={[radius, 24, 24]} />
    </mesh>
  );
});

// ---------------------------------------------------------------------------
// ConnectionLine sub-component (tube geometry via CatmullRomCurve3)
// ---------------------------------------------------------------------------

const ConnectionLine = React.memo(function ConnectionLine({
  start,
  end,
  color,
  thickness,
  pulse,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  color: string;
  thickness: number;
  pulse: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    const mid = start.clone().add(end).multiplyScalar(0.5);
    const dist = start.distanceTo(end);
    mid.y += dist * 0.35;

    const curve = new THREE.CatmullRomCurve3([
      start.clone(),
      mid,
      end.clone(),
    ]);
    return new THREE.TubeGeometry(curve, 16, thickness, 6, false);
  }, [start, end, thickness]);

  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: pulse ? 0.75 : 0.25,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    [color, pulse]
  );

  useFrame((state) => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshBasicMaterial;
    if (pulse) {
      mat.opacity = 0.5 + Math.sin(state.clock.elapsedTime * 3) * 0.25;
    }
  });

  return <mesh ref={meshRef} geometry={geometry} material={material} />;
});

// ---------------------------------------------------------------------------
// BrainMesh – loads the real fly brain OBJ as a transparent ghost
// ---------------------------------------------------------------------------

const BrainMesh = React.memo(function BrainMesh() {
  const obj = useLoader(OBJLoader, "/models/fly-brain.obj");
  const material = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: "#a855f7",
        transparent: true,
        opacity: 0.06,
        roughness: 0.8,
        metalness: 0.1,
        wireframe: false,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    []
  );

  const group = useMemo(() => {
    const clone = obj.clone();
    clone.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        (child as THREE.Mesh).material = material;
      }
    });
    // Center and scale the brain mesh to fit the scene
    const box = new THREE.Box3().setFromObject(clone);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 6 / maxDim; // fit within ~6 units
    clone.scale.setScalar(scale);
    clone.position.sub(center.multiplyScalar(scale));
    return clone;
  }, [obj, material]);

  return <primitive object={group} />;
});

// ---------------------------------------------------------------------------
// ModuleTooltip
// ---------------------------------------------------------------------------

function ModuleTooltip({
  mod,
  position,
}: {
  mod: CompileModule;
  position: [number, number, number];
}) {
  const tooltipPos: [number, number, number] = [
    position[0],
    position[1] + 0.06 + Math.sqrt(mod.n_neurons) / 500 + 0.15,
    position[2],
  ];

  return (
    <Html
      position={tooltipPos}
      center
      style={{ pointerEvents: "none", whiteSpace: "nowrap" }}
    >
      <div className="bg-black/90 backdrop-blur-xl px-5 py-3 rounded-xl border border-white/20 shadow-2xl min-w-56">
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: ROLE_COLORS[mod.role] }}
          />
          <span className="text-white font-semibold text-sm">
            Module {mod.id}
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded-full"
            style={{
              backgroundColor: ROLE_COLORS[mod.role] + "30",
              color: ROLE_COLORS[mod.role],
            }}
          >
            {mod.role}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-300">
          <span className="text-gray-500">Neurons</span>
          <span>{mod.n_neurons.toLocaleString()}</span>
          <span className="text-gray-500">Cell type</span>
          <span>{mod.top_super_class}</span>
          <span className="text-gray-500">NT</span>
          <span>{mod.top_nt}</span>
          <span className="text-gray-500">Region</span>
          <span>{mod.top_group}</span>
        </div>
      </div>
    </Html>
  );
}

// ---------------------------------------------------------------------------
// FlyBrainScene (inner scene rendered inside Canvas)
// ---------------------------------------------------------------------------

function FlyBrainScene({
  modules,
  threeLayerMap,
  fitnessFunctions,
  selectedBehaviors,
  onModuleClick,
  onModuleHover,
  autoRotate,
}: {
  modules: CompileModule[];
  threeLayerMap: ThreeLayerMap;
  fitnessFunctions: FitnessFunction[];
  selectedBehaviors: string[];
  onModuleClick?: (moduleId: number) => void;
  onModuleHover?: (moduleId: number | null) => void;
  autoRotate?: boolean;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  // Compute positions map (module id -> position)
  const positionMap = useMemo(() => {
    const map = new Map<number, [number, number, number]>();
    for (const mod of modules) {
      map.set(mod.id, computeModulePosition(mod));
    }
    return map;
  }, [modules]);

  // Module lookup
  const moduleMap = useMemo(() => {
    const m = new Map<number, CompileModule>();
    for (const mod of modules) m.set(mod.id, mod);
    return m;
  }, [modules]);

  // Build connections arrays
  const { osConnections, appConnections } = useMemo(() => {
    const osPairs: { src: number; tgt: number; functions: string[] }[] = [];
    for (const pair of threeLayerMap.os_layer) {
      if (positionMap.has(pair.src) && positionMap.has(pair.tgt)) {
        osPairs.push({ src: pair.src, tgt: pair.tgt, functions: pair.functions });
      }
    }

    const appPairs: { src: number; tgt: number; behavior: string }[] = [];
    for (const [behavior, pairs] of Object.entries(threeLayerMap.app_layer)) {
      for (const pair of pairs) {
        if (positionMap.has(pair.src) && positionMap.has(pair.tgt)) {
          appPairs.push({ src: pair.src, tgt: pair.tgt, behavior });
        }
      }
    }
    return { osConnections: osPairs, appConnections: appPairs };
  }, [threeLayerMap, positionMap]);

  // Pre-compute THREE.Vector3 positions
  const vec3Map = useMemo(() => {
    const m = new Map<number, THREE.Vector3>();
    for (const [id, pos] of positionMap) {
      m.set(id, new THREE.Vector3(pos[0], pos[1], pos[2]));
    }
    return m;
  }, [positionMap]);

  const handleHover = useCallback(
    (id: number | null) => {
      setHoveredId(id);
      onModuleHover?.(id);
    },
    [onModuleHover]
  );

  const handleClick = useCallback(
    (id: number) => {
      onModuleClick?.(id);
    },
    [onModuleClick]
  );

  // Auto-rotate
  useFrame(() => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += 0.002;
    }
  });

  const hasBehavior = selectedBehaviors.length > 0;

  // Hovered module for tooltip
  const hoveredModule = hoveredId !== null ? moduleMap.get(hoveredId) : undefined;
  const hoveredPosition = hoveredId !== null ? positionMap.get(hoveredId) : undefined;

  return (
    <group ref={groupRef}>
      {/* Fly brain mesh (transparent ghost) */}
      <BrainMesh />

      {/* Module spheres */}
      {modules.map((mod) => {
        const pos = positionMap.get(mod.id);
        if (!pos) return null;
        return (
          <ModuleSphere
            key={mod.id}
            module={mod}
            position={pos}
            isHovered={hoveredId === mod.id}
            onHover={handleHover}
            onClick={handleClick}
          />
        );
      })}

      {/* OS layer connections - faint when no behavior selected, pulse when relevant behavior active */}
      {osConnections.map((conn, i) => {
        const s = vec3Map.get(conn.src);
        const t = vec3Map.get(conn.tgt);
        if (!s || !t) return null;
        const isActive = hasBehavior && conn.functions.some((f) => selectedBehaviors.includes(f));
        return (
          <ConnectionLine
            key={`os-${i}`}
            start={s}
            end={t}
            color="#f59e0b"
            thickness={isActive ? 0.025 : 0.008}
            pulse={isActive}
          />
        );
      })}

      {/* APP layer connections - only for selected behaviors, with pulse */}
      {hasBehavior &&
        appConnections
          .filter((c) => selectedBehaviors.includes(c.behavior))
          .map((conn, i) => {
            const s = vec3Map.get(conn.src);
            const t = vec3Map.get(conn.tgt);
            if (!s || !t) return null;
            const color = BEHAVIOR_COLORS[conn.behavior] || "#8b5cf6";
            return (
              <ConnectionLine
                key={`app-${conn.behavior}-${i}`}
                start={s}
                end={t}
                color={color}
                thickness={0.012}
                pulse={true}
              />
            );
          })}

      {/* Tooltip */}
      {hoveredModule && hoveredPosition && (
        <ModuleTooltip mod={hoveredModule} position={hoveredPosition} />
      )}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Post-processing effects
// ---------------------------------------------------------------------------

function Effects() {
  try {
    return (
      <EffectComposer>
        <Bloom
          luminanceThreshold={0.15}
          luminanceSmoothing={0.9}
          intensity={0.8}
          radius={0.6}
        />
      </EffectComposer>
    );
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Loading fallback
// ---------------------------------------------------------------------------

function LoadingFallback() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame(() => {
    if (meshRef.current) meshRef.current.rotation.y += 0.02;
  });
  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1, 2]} />
      <meshBasicMaterial color="#a855f7" wireframe transparent opacity={0.3} />
    </mesh>
  );
}

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export function FlyBrain3D({
  className = "",
  selectedBehaviors,
  onModuleClick,
  onModuleHover,
  autoRotate = true,
  enableZoom = true,
  enablePan = false,
}: FlyBrain3DProps) {
  const [modules, setModules] = useState<CompileModule[]>([]);
  const [threeLayerMap, setThreeLayerMap] = useState<ThreeLayerMap | null>(null);
  const [fitnessFunctions, setFitnessFunctions] = useState<FitnessFunction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [mods, tlm, ffs] = await Promise.all([
          fetchModules(),
          fetchThreeLayerMap(),
          fetchFitnessFunctions(),
        ]);
        if (!cancelled) {
          setModules(mods);
          setThreeLayerMap(tlm);
          setFitnessFunctions(ffs);
          setLoading(false);
        }
      } catch (err) {
        console.error("FlyBrain3D: Failed to load data", err);
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const emptyTLM: ThreeLayerMap = useMemo(
    () => ({
      os_layer: [],
      app_layer: {},
      hardware_stats: {
        total_pairs: 0,
        tested_pairs: 0,
        evolvable_pairs: 0,
        frozen_pairs: 0,
        frozen_pct: 0,
        irrelevant_pairs: 0,
        irrelevant_pct: 0,
      },
    }),
    []
  );

  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 12], fov: 45 }}
        dpr={[1, 2]}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
          stencil: false,
          depth: true,
        }}
        style={{ background: "transparent" }}
        performance={{ min: 0.5 }}
      >
        {/* Fog for depth */}
        <fog attach="fog" args={["#000000", 12, 28]} />

        {/* Lighting */}
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 5, 5]} intensity={0.6} color="#ffffff" />
        <directionalLight position={[-5, -2, 5]} intensity={0.4} color="#c084fc" />
        <directionalLight position={[0, -5, -5]} intensity={0.3} color="#a78bfa" />
        <pointLight position={[0, 3, 4]} intensity={0.4} color="#06b6d4" distance={15} />
        <pointLight position={[3, 0, 0]} intensity={0.2} color="#a855f7" distance={12} />

        <Float speed={1.2} rotationIntensity={0.05} floatIntensity={0.2}>
          <Suspense fallback={<LoadingFallback />}>
            {!loading && threeLayerMap && (
              <FlyBrainScene
                modules={modules}
                threeLayerMap={threeLayerMap}
                fitnessFunctions={fitnessFunctions}
                selectedBehaviors={selectedBehaviors}
                onModuleClick={onModuleClick}
                onModuleHover={onModuleHover}
                autoRotate={autoRotate}
              />
            )}
            {loading && <LoadingFallback />}
          </Suspense>
        </Float>

        <Effects />

        <OrbitControls
          enableZoom={enableZoom}
          enablePan={enablePan}
          autoRotate={false}
          minPolarAngle={Math.PI / 6}
          maxPolarAngle={(Math.PI * 5) / 6}
          minDistance={5}
          maxDistance={20}
        />
      </Canvas>
    </div>
  );
}

export default FlyBrain3D;
