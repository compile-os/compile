"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

// ---------------------------------------------------------------------------
// Organic blob with vertex displacement
// ---------------------------------------------------------------------------
function Blob({
  position = [0, 0, 0] as [number, number, number],
  scale = 1,
  color = "#7C3AED",
  speed = 1,
  detail = 4,
  distortion = 0.15,
  emissiveIntensity = 0.15,
}: {
  position?: [number, number, number];
  scale?: number;
  color?: string;
  speed?: number;
  detail?: number;
  distortion?: number;
  emissiveIntensity?: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const originalPositions = useRef<Float32Array | null>(null);

  const geometry = useMemo(() => new THREE.IcosahedronGeometry(1, detail), [detail]);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const geo = meshRef.current.geometry;
    const positions = geo.attributes.position;

    if (!originalPositions.current) {
      originalPositions.current = new Float32Array(positions.array);
    }

    const t = clock.elapsedTime * speed;
    const orig = originalPositions.current;

    for (let i = 0; i < positions.count; i++) {
      const ox = orig[i * 3];
      const oy = orig[i * 3 + 1];
      const oz = orig[i * 3 + 2];

      const n1 = Math.sin(ox * 2.5 + t * 0.7) * Math.cos(oy * 3.1 + t * 0.5) * distortion;
      const n2 = Math.sin(oz * 1.8 + t * 1.1) * Math.cos(ox * 2.2 - t * 0.3) * distortion * 0.7;
      const n3 = Math.sin((ox + oy + oz) * 1.5 + t * 0.9) * distortion * 0.5;
      const pulse = 1 + Math.sin(t * 0.6) * 0.04;

      const displacement = n1 + n2 + n3;
      const len = Math.sqrt(ox * ox + oy * oy + oz * oz) || 1;

      positions.setXYZ(
        i,
        ox * pulse + (ox / len) * displacement,
        oy * pulse + (oy / len) * displacement,
        oz * pulse + (oz / len) * displacement,
      );
    }

    positions.needsUpdate = true;
    geo.computeVertexNormals();
    meshRef.current.rotation.y += 0.002 * speed;
  });

  return (
    <mesh ref={meshRef} geometry={geometry} position={position} scale={scale}>
      <meshPhysicalMaterial
        color={color}
        roughness={0.2}
        metalness={0.1}
        transmission={0.5}
        thickness={1.5}
        ior={1.4}
        transparent
        opacity={0.85}
        emissive={color}
        emissiveIntensity={emissiveIntensity}
      />
    </mesh>
  );
}

// Small floating particles
function Particles({ count = 15, color = "#a855f7", spread = 2.5 }: { count?: number; color?: string; spread?: number }) {
  const groupRef = useRef<THREE.Group>(null);

  const particles = useMemo(() =>
    Array.from({ length: count }, () => ({
      pos: [(Math.random() - 0.5) * spread, (Math.random() - 0.5) * spread, (Math.random() - 0.5) * spread] as [number, number, number],
      size: 0.03 + Math.random() * 0.06,
      speed: 0.3 + Math.random() * 0.7,
      phase: Math.random() * Math.PI * 2,
    })), [count, spread]);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    groupRef.current.children.forEach((child, i) => {
      const p = particles[i];
      const t = clock.elapsedTime * p.speed;
      child.position.y = p.pos[1] + Math.sin(t + p.phase) * 0.4;
      child.position.x = p.pos[0] + Math.sin(t * 0.7 + p.phase) * 0.2;
      child.position.z = p.pos[2] + Math.cos(t * 0.5 + p.phase) * 0.2;
      (child as THREE.Mesh).scale.setScalar(p.size * (1 + Math.sin(t * 2 + p.phase) * 0.3));
    });
  });

  return (
    <group ref={groupRef}>
      {particles.map((p, i) => (
        <mesh key={i} position={p.pos}>
          <sphereGeometry args={[1, 6, 6]} />
          <meshPhysicalMaterial color={color} emissive={color} emissiveIntensity={0.5} transparent opacity={0.5} roughness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

// Tendril / connection line between two points
function Tendril({ from, to, color = "#7C3AED" }: { from: [number, number, number]; to: [number, number, number]; color?: string }) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const mat = ref.current.material as THREE.MeshStandardMaterial;
    mat.opacity = 0.15 + Math.sin(clock.elapsedTime * 2) * 0.1;
  });

  const points = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(...from),
      new THREE.Vector3(
        (from[0] + to[0]) / 2 + (Math.random() - 0.5) * 0.5,
        (from[1] + to[1]) / 2 + (Math.random() - 0.5) * 0.5,
        (from[2] + to[2]) / 2 + (Math.random() - 0.5) * 0.5,
      ),
      new THREE.Vector3(...to),
    ]);
    return new THREE.TubeGeometry(curve, 12, 0.015, 4, false);
  }, [from, to]);

  return (
    <mesh ref={ref} geometry={points}>
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} transparent opacity={0.2} />
    </mesh>
  );
}

// ---------------------------------------------------------------------------
// Architecture-specific scenes
// ---------------------------------------------------------------------------

function HubAndSpokeScene({ color }: { color: string }) {
  // Central large hub with smaller nodes connected to it
  return (
    <>
      <Float speed={0.5} rotationIntensity={0.03} floatIntensity={0.1}>
        <Blob scale={0.9} color={color} speed={0.8} distortion={0.12} emissiveIntensity={0.2} />
      </Float>
      {[0, 1, 2, 3, 4, 5].map((i) => {
        const angle = (i / 6) * Math.PI * 2;
        const r = 2.2;
        const pos: [number, number, number] = [Math.cos(angle) * r, Math.sin(angle) * r * 0.6, Math.sin(angle) * 0.5];
        return (
          <group key={i}>
            <Float speed={0.3 + i * 0.1} rotationIntensity={0.02} floatIntensity={0.05}>
              <Blob position={pos} scale={0.25 + Math.random() * 0.15} color={color} speed={0.5 + i * 0.1} detail={3} distortion={0.2} />
            </Float>
            <Tendril from={[0, 0, 0]} to={pos} color={color} />
          </group>
        );
      })}
      <Particles count={12} color={color} spread={3} />
    </>
  );
}

function ReservoirScene({ color }: { color: string }) {
  // Many small blobs swirling chaotically — no center
  return (
    <>
      {Array.from({ length: 18 }, (_, i) => {
        const pos: [number, number, number] = [
          (Math.random() - 0.5) * 3,
          (Math.random() - 0.5) * 3,
          (Math.random() - 0.5) * 2,
        ];
        return (
          <Float key={i} speed={0.5 + Math.random()} rotationIntensity={0.05} floatIntensity={0.15}>
            <Blob position={pos} scale={0.15 + Math.random() * 0.2} color={color} speed={0.5 + Math.random()} detail={3} distortion={0.25} />
          </Float>
        );
      })}
      <Particles count={20} color={color} spread={3.5} />
    </>
  );
}

function HierarchicalScene({ color }: { color: string }) {
  // Three tiers stacked vertically, each tier smaller
  return (
    <>
      {/* Tier 1 (bottom — motor) */}
      <Float speed={0.4} floatIntensity={0.05}>
        <Blob position={[0, -1.5, 0]} scale={0.7} color={color} speed={0.6} distortion={0.1} emissiveIntensity={0.25} />
      </Float>
      {/* Tier 2 (middle — selection) */}
      <Float speed={0.5} floatIntensity={0.08}>
        <Blob position={[-0.6, 0, 0]} scale={0.45} color="#a855f7" speed={0.7} detail={3} distortion={0.15} />
      </Float>
      <Float speed={0.5} floatIntensity={0.08}>
        <Blob position={[0.6, 0, 0]} scale={0.45} color="#a855f7" speed={0.7} detail={3} distortion={0.15} />
      </Float>
      {/* Tier 3 (top — meta-control) */}
      <Float speed={0.6} floatIntensity={0.1}>
        <Blob position={[0, 1.5, 0]} scale={0.3} color="#c084fc" speed={0.8} detail={3} distortion={0.2} emissiveIntensity={0.3} />
      </Float>
      <Tendril from={[0, -1.5, 0]} to={[-0.6, 0, 0]} color={color} />
      <Tendril from={[0, -1.5, 0]} to={[0.6, 0, 0]} color={color} />
      <Tendril from={[-0.6, 0, 0]} to={[0, 1.5, 0]} color="#a855f7" />
      <Tendril from={[0.6, 0, 0]} to={[0, 1.5, 0]} color="#a855f7" />
      <Particles count={10} color={color} spread={2.5} />
    </>
  );
}

function RingScene({ color }: { color: string }) {
  const n = 8;
  const nodes = Array.from({ length: n }, (_, i) => {
    const angle = (i / n) * Math.PI * 2;
    return [Math.cos(angle) * 1.8, Math.sin(angle) * 1.8, 0] as [number, number, number];
  });
  return (
    <>
      {nodes.map((pos, i) => (
        <group key={i}>
          <Float speed={0.3} floatIntensity={0.05}>
            <Blob position={pos} scale={0.25} color={color} speed={0.5} detail={3} distortion={0.2} />
          </Float>
          <Tendril from={pos} to={nodes[(i + 1) % n]} color={color} />
        </group>
      ))}
      <Particles count={8} color={color} spread={2.5} />
    </>
  );
}

function PredictiveCodingScene({ color }: { color: string }) {
  // Paired layers — prediction and error — with up/down connections
  return (
    <>
      {/* Prediction layers (left) */}
      <Float speed={0.4} floatIntensity={0.05}>
        <Blob position={[-1, -1, 0]} scale={0.4} color={color} speed={0.6} detail={3} />
      </Float>
      <Float speed={0.4} floatIntensity={0.05}>
        <Blob position={[-1, 1, 0]} scale={0.35} color={color} speed={0.7} detail={3} />
      </Float>
      {/* Error layers (right) */}
      <Float speed={0.5} floatIntensity={0.08}>
        <Blob position={[1, -1, 0]} scale={0.35} color="#ef4444" speed={0.6} detail={3} distortion={0.2} />
      </Float>
      <Float speed={0.5} floatIntensity={0.08}>
        <Blob position={[1, 1, 0]} scale={0.3} color="#ef4444" speed={0.7} detail={3} distortion={0.2} />
      </Float>
      {/* Cross connections */}
      <Tendril from={[-1, -1, 0]} to={[1, -1, 0]} color={color} />
      <Tendril from={[-1, 1, 0]} to={[1, 1, 0]} color={color} />
      <Tendril from={[1, -1, 0]} to={[-1, 1, 0]} color="#ef4444" />
      <Tendril from={[-1, 1, 0]} to={[-1, -1, 0]} color="#a855f7" />
      <Particles count={10} color={color} spread={2} />
    </>
  );
}

function SubsumptionScene({ color }: { color: string }) {
  // Stacked layers — bottom (escape) overrides top (navigation)
  return (
    <>
      <Float speed={0.3} floatIntensity={0.03}>
        <Blob position={[0, -1.8, 0]} scale={0.6} color="#ef4444" speed={0.5} distortion={0.1} emissiveIntensity={0.25} />
      </Float>
      <Float speed={0.4} floatIntensity={0.05}>
        <Blob position={[0, 0, 0]} scale={0.5} color={color} speed={0.6} distortion={0.12} />
      </Float>
      <Float speed={0.5} floatIntensity={0.08}>
        <Blob position={[0, 1.6, 0]} scale={0.35} color="#06b6d4" speed={0.7} detail={3} distortion={0.15} />
      </Float>
      <Tendril from={[0, -1.8, 0]} to={[0, 0, 0]} color="#ef4444" />
      <Tendril from={[0, 0, 0]} to={[0, 1.6, 0]} color={color} />
      <Particles count={8} color={color} spread={2} />
    </>
  );
}

function DefaultScene({ color }: { color: string }) {
  // Generic organic form for architectures without a specific visualization
  return (
    <>
      <Float speed={0.5} rotationIntensity={0.03} floatIntensity={0.1}>
        <Blob scale={0.7} color={color} speed={0.8} distortion={0.18} emissiveIntensity={0.2} />
      </Float>
      <Float speed={0.3} floatIntensity={0.1}>
        <Blob position={[1.2, 0.8, -0.5]} scale={0.25} color="#a855f7" speed={0.6} detail={3} distortion={0.2} />
      </Float>
      <Float speed={0.4} floatIntensity={0.08}>
        <Blob position={[-1, -0.6, 0.3]} scale={0.3} color="#06b6d4" speed={0.7} detail={3} distortion={0.2} />
      </Float>
      <Particles count={15} color={color} spread={3} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Scene router
// ---------------------------------------------------------------------------

function ArchitectureScene({ architecture, color }: { architecture: string; color: string }) {
  switch (architecture) {
    case "hub_and_spoke": return <HubAndSpokeScene color={color} />;
    case "hierarchical_hub": return <HierarchicalScene color={color} />;
    case "reservoir": return <ReservoirScene color={color} />;
    case "ring": return <RingScene color={color} />;
    case "predictive_coding": return <PredictiveCodingScene color={color} />;
    case "subsumption": return <SubsumptionScene color={color} />;
    default: return <DefaultScene color={color} />;
  }
}

// Colors for composite regions
const REGION_COLORS = ["#7C3AED", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444", "#ec4899"];

function BioScene({ architectures, color }: { architectures: string[]; color: string }) {
  const isComposite = architectures.length > 1;
  // For composites: spread regions horizontally, scale them down, add interface tendrils
  const regionScale = isComposite ? 0.55 / Math.sqrt(architectures.length) + 0.3 : 1;
  const spacing = isComposite ? 3.5 : 0;

  return (
    <>
      <ambientLight intensity={0.15} />
      <directionalLight position={[3, 5, 3]} intensity={0.4} color="#ffffff" />
      <directionalLight position={[-2, -3, 2]} intensity={0.25} color="#7c3aed" />
      <pointLight position={[0, 2, 2]} intensity={0.4} color="#06b6d4" distance={10} />
      <pointLight position={[0, -1, -2]} intensity={0.3} color="#a855f7" distance={8} />

      {architectures.map((arch, i) => {
        const x = isComposite ? (i - (architectures.length - 1) / 2) * spacing : 0;
        const regionColor = isComposite ? REGION_COLORS[i % REGION_COLORS.length] : color;
        return (
          <group key={arch + i} position={[x, 0, 0]} scale={[regionScale, regionScale, regionScale]}>
            <ArchitectureScene architecture={arch} color={regionColor} />
          </group>
        );
      })}

      {/* Interface tendrils between composite regions */}
      {isComposite && architectures.slice(0, -1).map((_, i) => {
        const x1 = (i - (architectures.length - 1) / 2) * spacing;
        const x2 = (i + 1 - (architectures.length - 1) / 2) * spacing;
        return (
          <Tendril
            key={`interface-${i}`}
            from={[x1, 0, 0]}
            to={[x2, 0, 0]}
            color="#7C3AED"
          />
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Exported component
// ---------------------------------------------------------------------------

export interface BioTubeProps {
  className?: string;
  color?: string;
  speed?: number;
  architecture?: string;
  architectures?: string[];
}

export default function BioTube({ className = "", color = "#7C3AED", speed = 1, architecture = "hub_and_spoke", architectures }: BioTubeProps) {
  const archList = architectures || [architecture];
  return (
    <div className={`${className} relative`}>
      <Canvas
        camera={{ position: [0, 0, archList.length > 1 ? 10 + archList.length * 2 : 8], fov: 40 }}
        dpr={[1, 2]}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        style={{ background: "transparent" }}
      >
        <fog attach="fog" args={["#0a0a0f", 8, 18]} />
        <BioScene architectures={archList} color={color} />
      </Canvas>
    </div>
  );
}
