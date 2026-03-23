"use client";

import { Player } from "@remotion/player";
import { BandwidthGap } from "./BandwidthGap";
import { NeuralPipeline } from "./NeuralPipeline";
import { DataFlywheel } from "./DataFlywheel";
import { FiveWalls } from "./FiveWalls";
import { StatsOrbit } from "./StatsOrbit";
import { HeroAnimation } from "./HeroAnimation";
import { MarketOpportunity } from "./MarketOpportunity";
import { SignalCompression } from "./SignalCompression";

interface RemotionPlayerProps {
  composition: "bandwidth" | "pipeline" | "flywheel" | "walls" | "stats" | "hero" | "market" | "compression";
  width?: number;
  height?: number;
  loop?: boolean;
  className?: string;
}

const compositions = {
  bandwidth: { component: BandwidthGap, duration: 180 },
  pipeline: { component: NeuralPipeline, duration: 150 },
  flywheel: { component: DataFlywheel, duration: 300 },
  walls: { component: FiveWalls, duration: 120 },
  stats: { component: StatsOrbit, duration: 120 },
  hero: { component: HeroAnimation, duration: 300 },
  market: { component: MarketOpportunity, duration: 150 },
  compression: { component: SignalCompression, duration: 150 },
};

export function RemotionPlayer({
  composition,
  width = 600,
  height = 400,
  loop = true,
  className = "",
}: RemotionPlayerProps) {
  const { component: Component, duration } = compositions[composition];

  return (
    <div className={`w-full h-full ${className}`} style={{ minHeight: height }}>
      <Player
        component={Component}
        durationInFrames={duration}
        fps={30}
        compositionWidth={width}
        compositionHeight={height}
        style={{
          width: "100%",
          height: "100%",
        }}
        loop={loop}
        autoPlay
        controls={false}
        inputProps={{}}
      />
    </div>
  );
}

export { BandwidthGap, NeuralPipeline, DataFlywheel, FiveWalls, StatsOrbit, HeroAnimation, MarketOpportunity, SignalCompression };
