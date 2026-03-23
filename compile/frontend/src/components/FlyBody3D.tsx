"use client";

import React, { Suspense, useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls, ContactShadows, Grid } from "@react-three/drei";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import * as THREE from "three";

// ---------------------------------------------------------------------------
// Fly body parts
// ---------------------------------------------------------------------------

// Tripod gait: T1L+T2R+T3L (phase 0), T1R+T2L+T3R (phase π)
const P0 = 0;
const P1 = Math.PI;
const LEG_AMP = 0.15; // radians of oscillation

const FLY_PARTS: { file: string; color: string; phase?: number; amp?: number; isWing?: boolean }[] = [
  // Static body parts
  { file: "thorax_body.obj", color: "#A0784A" },
  { file: "head_body.obj", color: "#8B6940" },
  { file: "abdomen_1_body.obj", color: "#B08050" },
  { file: "abdomen_2_body.obj", color: "#A87848" },
  { file: "abdomen_3_body.obj", color: "#A07040" },
  { file: "abdomen_4_body.obj", color: "#986838" },
  { file: "abdomen_5_body.obj", color: "#906030" },
  { file: "abdomen_6_body.obj", color: "#885828" },
  { file: "abdomen_7_body.obj", color: "#805020" },
  { file: "abdomen_8_body.obj", color: "#784818" },
  { file: "wing_left_membrane.obj", color: "#C0C0D0", phase: 0, amp: 0.08, isWing: true },
  { file: "wing_right_membrane.obj", color: "#C0C0D0", phase: Math.PI, amp: 0.08, isWing: true },
  { file: "antenna_left_body.obj", color: "#604020" },
  { file: "antenna_right_body.obj", color: "#604020" },
  // Legs — animated with tripod gait
  { file: "coxa_T1_left_body.obj", color: "#907050", phase: P0, amp: LEG_AMP },
  { file: "coxa_T1_right_body.obj", color: "#907050", phase: P1, amp: LEG_AMP },
  { file: "coxa_T2_left_body.obj", color: "#907050", phase: P1, amp: LEG_AMP },
  { file: "coxa_T2_right_body.obj", color: "#907050", phase: P0, amp: LEG_AMP },
  { file: "coxa_T3_left_body.obj", color: "#907050", phase: P0, amp: LEG_AMP },
  { file: "coxa_T3_right_body.obj", color: "#907050", phase: P1, amp: LEG_AMP },
  { file: "femur_T1_left_body.obj", color: "#806040", phase: P0, amp: LEG_AMP * 0.7 },
  { file: "femur_T1_right_body.obj", color: "#806040", phase: P1, amp: LEG_AMP * 0.7 },
  { file: "femur_T2_left_body.obj", color: "#806040", phase: P1, amp: LEG_AMP * 0.7 },
  { file: "femur_T2_right_body.obj", color: "#806040", phase: P0, amp: LEG_AMP * 0.7 },
  { file: "femur_T3_left_body.obj", color: "#806040", phase: P0, amp: LEG_AMP * 0.7 },
  { file: "femur_T3_right_body.obj", color: "#806040", phase: P1, amp: LEG_AMP * 0.7 },
  { file: "tibia_T1_left_body.obj", color: "#705030", phase: P0, amp: LEG_AMP * 0.5 },
  { file: "tibia_T1_right_body.obj", color: "#705030", phase: P1, amp: LEG_AMP * 0.5 },
  { file: "tibia_T2_left_body.obj", color: "#705030", phase: P1, amp: LEG_AMP * 0.5 },
  { file: "tibia_T2_right_body.obj", color: "#705030", phase: P0, amp: LEG_AMP * 0.5 },
  { file: "tibia_T3_left_body.obj", color: "#705030", phase: P0, amp: LEG_AMP * 0.5 },
  { file: "tibia_T3_right_body.obj", color: "#705030", phase: P1, amp: LEG_AMP * 0.5 },
];

const BodyPart = React.memo(function BodyPart({
  file,
  color,
  animationPhase,
  animationAmplitude,
  legsMoving,
  isWing,
}: {
  file: string;
  color: string;
  animationPhase?: number;
  animationAmplitude?: number;
  legsMoving?: boolean;
  isWing?: boolean;
}) {
  const obj = useLoader(OBJLoader, `/models/fly/${file}`);
  const groupRef = useRef<THREE.Group>(null);
  const material = useMemo(
    () => new THREE.MeshStandardMaterial({
      color,
      roughness: isWing ? 0.3 : 0.5,
      metalness: isWing ? 0.05 : 0.1,
      transparent: isWing ? true : false,
      opacity: isWing ? 0.6 : 1,
      side: THREE.DoubleSide,
    }),
    [color, isWing]
  );
  const group = useMemo(() => {
    const clone = obj.clone();
    clone.traverse((child) => { if ((child as THREE.Mesh).isMesh) (child as THREE.Mesh).material = material; });
    return clone;
  }, [obj, material]);

  useFrame(({ clock }) => {
    if (!groupRef.current || !animationAmplitude) return;

    if (isWing) {
      // Wings: constant gentle flutter (high freq, small amplitude)
      // Plus a slight fold-back tilt
      const t = clock.elapsedTime;
      const phase = animationPhase || 0;
      const flutter = Math.sin(t * 25 + phase) * animationAmplitude;
      groupRef.current.rotation.z = flutter;
      groupRef.current.rotation.x = 0.05; // slight fold back
      return;
    }

    // Legs
    if (!legsMoving) {
      groupRef.current.rotation.x *= 0.9;
      return;
    }
    const t = clock.elapsedTime;
    const phase = animationPhase || 0;
    groupRef.current.rotation.x = Math.sin(t * 12 + phase) * animationAmplitude;
  });

  return (
    <group ref={groupRef}>
      <primitive object={group} />
    </group>
  );
});

// ---------------------------------------------------------------------------
// Food marker (for navigation preset)
// ---------------------------------------------------------------------------

function FoodMarker({ position }: { position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.position.y = position[1] + Math.sin(clock.elapsedTime * 2) * 0.05;
    }
  });
  return (
    <group position={position}>
      <mesh ref={ref}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={0.5} transparent opacity={0.8} />
      </mesh>
      {/* Glow ring on ground */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.1, 0.15, 32]} />
        <meshBasicMaterial color="#22c55e" transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function ThreatMarker({ position }: { position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.scale.setScalar(1 + Math.sin(clock.elapsedTime * 6) * 0.15);
    }
  });
  return (
    <group position={position}>
      <mesh ref={ref}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.8} transparent opacity={0.7} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.15, 0.22, 32]} />
        <meshBasicMaterial color="#ef4444" transparent opacity={0.15} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Behavior animation
// ---------------------------------------------------------------------------

// The fly OBJ has head at x=-0.84, tail at x=+1.65
// It faces in the -X direction in local space
// After the -PI/2 X rotation (Z-up to Y-up), the fly lies flat
// The fly's forward direction in world space is -X (before heading rotation)

// Behaviors that play once and stop (vs looping)
const ONE_SHOT_BEHAVIORS = new Set(["navigation", "escape"]);

function FlyScene({
  activePreset,
  playing,
  replayKey,
  onFinished,
}: {
  activePreset: string | null;
  playing: boolean;
  replayKey: number;
  onFinished?: () => void;
}) {
  const flyRef = useRef<THREE.Group>(null);
  const [legsMoving, setLegsMoving] = useState(false);
  const posRef = useRef({ x: 0, z: 0 });
  const headingRef = useRef(Math.PI);  // radians, PI = facing +X (180°)
  const timeRef = useRef(0);
  const finishedRef = useRef(false);

  useEffect(() => {
    posRef.current = { x: 0, z: 0 };
    headingRef.current = Math.PI;
    timeRef.current = 0;
    finishedRef.current = false;
  }, [activePreset, replayKey]);

  useFrame((_, delta) => {
    if (!flyRef.current) return;
    if (!playing || !activePreset) {
      flyRef.current.position.set(posRef.current.x, 0, posRef.current.z);
      flyRef.current.rotation.set(0, headingRef.current, 0);
      setLegsMoving(false);
      return;
    }

    timeRef.current += delta;
    const t = timeRef.current;

    // Behavior-specific animation
    let fwdSpeed = 0;
    let turnRate = 0;
    let bob = 0;

    switch (activePreset) {
      case "navigation": {
        // Walk toward food at (3, 0, 0)
        const dx = 3 - posRef.current.x;
        const dz = 0 - posRef.current.z;
        const targetAngle = Math.atan2(-dz, -dx); // -X is forward
        let angleDiff = targetAngle - headingRef.current;
        while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
        turnRate = angleDiff * 2; // Steer toward food
        fwdSpeed = 0.5;
        bob = Math.sin(t * 12) * 0.02;
        // Stop near food
        if (Math.sqrt(dx * dx + dz * dz) < 0.3) {
          fwdSpeed = 0; turnRate = 0; bob = 0;
          if (!finishedRef.current) { finishedRef.current = true; onFinished?.(); }
        }
        break;
      }
      case "escape": {
        // Quick dart backward then freeze
        if (t < 0.5) {
          fwdSpeed = -3.0; // fast backward
          bob = Math.sin(t * 30) * 0.04;
        } else if (t < 0.8) {
          turnRate = 8; // spin
        }
        // Then freeze (escape is ballistic)
        if (t > 1.0 && !finishedRef.current) { finishedRef.current = true; onFinished?.(); }
        break;
      }
      case "turning": {
        // Steady turn in place
        fwdSpeed = 0.1;
        turnRate = 1.5;
        bob = Math.sin(t * 10) * 0.015;
        break;
      }
      case "arousal": {
        // Jittery, alert movement — random-walk style
        fwdSpeed = 0.4;
        turnRate = Math.sin(t * 3) * 1.0 + Math.sin(t * 7) * 0.5;
        bob = Math.sin(t * 15) * 0.025;
        break;
      }
      case "circles": {
        // Smooth, sustained circular walking
        fwdSpeed = 0.5;
        turnRate = 1.8;
        bob = Math.sin(t * 12) * 0.02;
        break;
      }
      case "rhythm": {
        // Walk 2s, stop 1s, repeat
        const cycle = t % 3;
        const active = cycle < 2;
        fwdSpeed = active ? 0.5 : 0;
        bob = active ? Math.sin(t * 12) * 0.02 : 0;
        break;
      }
      default: {
        // Unknown/custom behavior — gentle exploratory walk
        fwdSpeed = 0.3;
        turnRate = Math.sin(t * 2) * 0.5;
        bob = Math.sin(t * 10) * 0.015;
        break;
      }
    }

    // Track whether legs should be moving
    setLegsMoving(Math.abs(fwdSpeed) > 0.05 || Math.abs(turnRate) > 0.3);

    // Clamp turn rate
    turnRate = Math.max(-5, Math.min(5, turnRate));

    // Update state
    headingRef.current += turnRate * delta;
    const fwd = fwdSpeed * delta;
    // Fly faces -X in local space, heading 0 = -X direction
    posRef.current.x += Math.cos(headingRef.current + Math.PI) * fwd;
    posRef.current.z += Math.sin(headingRef.current + Math.PI) * fwd;

    // Bounds
    posRef.current.x = Math.max(-5, Math.min(5, posRef.current.x));
    posRef.current.z = Math.max(-5, Math.min(5, posRef.current.z));

    // Apply
    flyRef.current.position.set(posRef.current.x, bob, posRef.current.z);
    flyRef.current.rotation.set(0, headingRef.current, 0);
  });

  const scale = 0.6;

  return (
    <>
      <group ref={flyRef}>
        {/* Inner group: rotate OBJ from Z-up to Y-up, center it. Scale 0.5 so fly is small relative to world */}
        <group scale={[scale, scale, scale]} position={[-0.4 * scale, 0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <Suspense fallback={null}>
            {FLY_PARTS.map((part) => (
              <BodyPart
                key={part.file}
                file={part.file}
                color={part.color}
                animationPhase={part.phase}
                animationAmplitude={part.amp}
                legsMoving={legsMoving}
                isWing={part.isWing}
              />
            ))}
          </Suspense>
        </group>
      </group>

      {/* Food marker for navigation */}
      {activePreset === "navigation" && <FoodMarker position={[3, 0.15, 0]} />}
      {/* Threat marker for escape */}
      {activePreset === "escape" && <ThreatMarker position={[0.5, 0.15, 0]} />}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface FlyBody3DProps {
  className?: string;
  activePreset: string | null;
  playing?: boolean;
  replayKey?: number;
  onFinished?: () => void;
}

export default function FlyBody3D({ className, activePreset, playing = true, replayKey = 0, onFinished }: FlyBody3DProps) {

  return (
    <div className={`${className} relative`}>
      <Canvas camera={{ position: [3, 4, 8], fov: 45 }} shadows dpr={[1, 2]}>
        <color attach="background" args={["#050508"]} />
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 8, 3]} intensity={0.8} castShadow />
        <directionalLight position={[-3, 4, -3]} intensity={0.2} color="#c084fc" />

        <Grid
          args={[20, 20]}
          position={[0, -0.01, 0]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#1a1a2e"
          sectionSize={2}
          sectionThickness={1}
          sectionColor="#2a2a4e"
          fadeDistance={15}
          fadeStrength={1}
          infiniteGrid
        />
        <ContactShadows position={[0, -0.005, 0]} opacity={0.4} scale={10} blur={2} far={4} />

        <FlyScene activePreset={activePreset} playing={playing} replayKey={replayKey} onFinished={onFinished} />

        <OrbitControls enableZoom enablePan minDistance={1} maxDistance={50} target={[1.5, 0.5, 0]} />
      </Canvas>



      {!activePreset && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          <div className="text-gray-600 text-xs bg-black/50 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/5">
            Select a preset to see compiled behavior
          </div>
        </div>
      )}
    </div>
  );
}
