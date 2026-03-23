"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  OrbitControls,
  Sphere,
  MeshDistortMaterial,
  Float,
  Trail,
  Sparkles,
  Environment,
} from "@react-three/drei";
import * as THREE from "three";

// Neural pulse traveling along connections
function NeuralPulse({
  startPoint,
  endPoint,
  delay = 0
}: {
  startPoint: THREE.Vector3;
  endPoint: THREE.Vector3;
  delay?: number;
}) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = ((clock.getElapsedTime() + delay) % 2) / 2;
    ref.current.position.lerpVectors(startPoint, endPoint, t);
    ref.current.scale.setScalar(Math.sin(t * Math.PI) * 0.5 + 0.5);
  });

  return (
    <Trail
      width={2}
      length={6}
      color="#a855f7"
      attenuation={(t) => t * t}
    >
      <mesh ref={ref}>
        <sphereGeometry args={[0.03, 8, 8]} />
        <meshBasicMaterial color="#c084fc" transparent opacity={0.9} />
      </mesh>
    </Trail>
  );
}

// Wireframe brain mesh
function BrainMesh() {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireframeRef = useRef<THREE.LineSegments>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.rotation.y = t * 0.1;
      meshRef.current.rotation.x = Math.sin(t * 0.2) * 0.1;
    }
    if (wireframeRef.current) {
      wireframeRef.current.rotation.y = t * 0.1;
      wireframeRef.current.rotation.x = Math.sin(t * 0.2) * 0.1;
    }
    if (innerRef.current) {
      innerRef.current.rotation.y = -t * 0.15;
      innerRef.current.rotation.x = Math.sin(t * 0.3) * 0.15;
    }
  });

  // Create brain-like geometry (deformed sphere with bumps)
  const brainGeometry = useMemo(() => {
    const geo = new THREE.IcosahedronGeometry(1.5, 4);
    const positions = geo.attributes.position.array as Float32Array;

    // Deform to look more brain-like
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const y = positions[i + 1];
      const z = positions[i + 2];

      // Add wrinkles/folds
      const noise = Math.sin(x * 8) * Math.cos(y * 6) * Math.sin(z * 7) * 0.1;
      const stretch = y > 0 ? 1.1 : 0.95; // Slightly elongated top

      positions[i] *= 1 + noise;
      positions[i + 1] *= stretch + noise * 0.5;
      positions[i + 2] *= 1 + noise;
    }

    geo.computeVertexNormals();
    return geo;
  }, []);

  // Create edges for wireframe
  const edgesGeometry = useMemo(() => {
    return new THREE.EdgesGeometry(brainGeometry, 15);
  }, [brainGeometry]);

  // Generate neural connection points
  const connections = useMemo(() => {
    const conns: { start: THREE.Vector3; end: THREE.Vector3 }[] = [];
    const positions = brainGeometry.attributes.position.array;

    for (let i = 0; i < 30; i++) {
      const idx1 = Math.floor(Math.random() * (positions.length / 3)) * 3;
      const idx2 = Math.floor(Math.random() * (positions.length / 3)) * 3;

      conns.push({
        start: new THREE.Vector3(positions[idx1], positions[idx1 + 1], positions[idx1 + 2]),
        end: new THREE.Vector3(positions[idx2], positions[idx2 + 1], positions[idx2 + 2]),
      });
    }

    return conns;
  }, [brainGeometry]);

  return (
    <group>
      {/* Inner glowing core */}
      <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
        <mesh ref={innerRef}>
          <icosahedronGeometry args={[0.8, 2]} />
          <meshBasicMaterial
            color="#7c3aed"
            transparent
            opacity={0.15}
            wireframe
          />
        </mesh>
      </Float>

      {/* Main brain surface - semi-transparent */}
      <mesh ref={meshRef} geometry={brainGeometry}>
        <meshPhysicalMaterial
          color="#1a1a2e"
          transparent
          opacity={0.3}
          roughness={0.2}
          metalness={0.8}
          envMapIntensity={1}
        />
      </mesh>

      {/* Wireframe overlay - the x-ray effect */}
      <lineSegments ref={wireframeRef} geometry={edgesGeometry}>
        <lineBasicMaterial
          color="#a855f7"
          transparent
          opacity={0.8}
          linewidth={1}
        />
      </lineSegments>

      {/* Outer glow wireframe */}
      <mesh geometry={brainGeometry} scale={1.02}>
        <meshBasicMaterial
          color="#c084fc"
          transparent
          opacity={0.1}
          wireframe
        />
      </mesh>

      {/* Neural pulses */}
      {connections.map((conn, i) => (
        <NeuralPulse
          key={i}
          startPoint={conn.start}
          endPoint={conn.end}
          delay={i * 0.2}
        />
      ))}

      {/* Sparkles around the brain */}
      <Sparkles
        count={100}
        scale={4}
        size={2}
        speed={0.4}
        color="#a855f7"
        opacity={0.5}
      />
    </group>
  );
}

// Floating data particles
function DataParticles() {
  const count = 200;
  const particlesRef = useRef<THREE.Points>(null);

  const [positions, velocities] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const vel = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2.5 + Math.random() * 1.5;

      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);

      vel[i * 3] = (Math.random() - 0.5) * 0.01;
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.01;
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.01;
    }

    return [pos, vel];
  }, []);

  useFrame(() => {
    if (!particlesRef.current) return;
    const posArray = particlesRef.current.geometry.attributes.position.array as Float32Array;

    for (let i = 0; i < count; i++) {
      posArray[i * 3] += velocities[i * 3];
      posArray[i * 3 + 1] += velocities[i * 3 + 1];
      posArray[i * 3 + 2] += velocities[i * 3 + 2];

      // Keep particles in bounds
      const dist = Math.sqrt(
        posArray[i * 3] ** 2 +
        posArray[i * 3 + 1] ** 2 +
        posArray[i * 3 + 2] ** 2
      );

      if (dist > 4 || dist < 2) {
        velocities[i * 3] *= -1;
        velocities[i * 3 + 1] *= -1;
        velocities[i * 3 + 2] *= -1;
      }
    }

    particlesRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.02}
        color="#c084fc"
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

// Scanning rings effect
function ScanningRings() {
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = t * 0.5;
      ring1Ref.current.rotation.y = t * 0.3;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x = -t * 0.4;
      ring2Ref.current.rotation.z = t * 0.2;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.y = t * 0.6;
      ring3Ref.current.rotation.z = -t * 0.3;
    }
  });

  return (
    <>
      <mesh ref={ring1Ref}>
        <torusGeometry args={[2.2, 0.01, 16, 100]} />
        <meshBasicMaterial color="#a855f7" transparent opacity={0.4} />
      </mesh>
      <mesh ref={ring2Ref}>
        <torusGeometry args={[2.4, 0.01, 16, 100]} />
        <meshBasicMaterial color="#ec4899" transparent opacity={0.3} />
      </mesh>
      <mesh ref={ring3Ref}>
        <torusGeometry args={[2.6, 0.01, 16, 100]} />
        <meshBasicMaterial color="#8b5cf6" transparent opacity={0.2} />
      </mesh>
    </>
  );
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.2} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#a855f7" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ec4899" />
      <spotLight
        position={[0, 5, 0]}
        angle={0.5}
        penumbra={1}
        intensity={1}
        color="#c084fc"
      />

      <BrainMesh />
      <DataParticles />
      <ScanningRings />

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.5}
        maxPolarAngle={Math.PI / 1.5}
        minPolarAngle={Math.PI / 3}
      />
    </>
  );
}

export default function WireframeBrain({ className = "" }: { className?: string }) {
  return (
    <div className={`w-full h-full ${className}`} style={{ background: "transparent" }}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <Scene />
      </Canvas>
    </div>
  );
}
