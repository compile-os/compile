"use client";

import React, { useMemo } from "react";
import type { ThreeLayerMap } from "@/types/compile";

interface ThreeLayerStatsProps {
  threeLayerMap: ThreeLayerMap | null;
  selectedBehaviors: string[];
}

export function ThreeLayerStats({
  threeLayerMap,
  selectedBehaviors,
}: ThreeLayerStatsProps) {
  const stats = threeLayerMap?.hardware_stats;

  const osCount = threeLayerMap?.os_layer.length ?? 0;

  const appCount = useMemo(() => {
    if (!threeLayerMap) return 0;
    let count = 0;
    for (const behavior of selectedBehaviors) {
      const pairs = threeLayerMap.app_layer[behavior];
      if (pairs) count += pairs.length;
    }
    return count;
  }, [threeLayerMap, selectedBehaviors]);

  if (!stats) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-white/5 rounded" />
        <div className="h-8 bg-white/5 rounded" />
      </div>
    );
  }

  // Compute percentages from raw counts (the pct fields use different bases)
  const total = stats.total_pairs || 2500;
  const frozenPct = ((stats.frozen_pairs + (total - stats.tested_pairs)) / total) * 100; // frozen + untested
  const evolvablePct = (stats.evolvable_pairs / total) * 100;
  const irrelevantPct = Math.max(0, 100 - frozenPct - evolvablePct);
  const programmablePct = evolvablePct;

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
        Three-Layer Architecture
      </h3>

      {/* Stacked bar */}
      <div className="relative h-6 rounded-full overflow-hidden bg-white/5">
        {/* Frozen */}
        <div
          className="absolute inset-y-0 left-0 bg-gray-600 transition-all"
          style={{ width: `${frozenPct}%` }}
          title={`Frozen: ${frozenPct.toFixed(1)}%`}
        />
        {/* Irrelevant */}
        <div
          className="absolute inset-y-0 bg-gray-800 transition-all"
          style={{ left: `${frozenPct}%`, width: `${irrelevantPct}%` }}
          title={`Irrelevant: ${irrelevantPct.toFixed(1)}%`}
        />
        {/* Programmable - glow effect */}
        <div
          className="absolute inset-y-0 transition-all"
          style={{
            left: `${frozenPct + irrelevantPct}%`,
            width: `${Math.max(programmablePct, 1.5)}%`,
            background: "linear-gradient(90deg, #a855f7, #c084fc)",
            boxShadow: "0 0 12px #a855f780, 0 0 4px #a855f7",
          }}
          title={`Programmable: ${programmablePct.toFixed(1)}%`}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-gray-600" />
          <span>Frozen {frozenPct.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-gray-800" />
          <span>Irrelevant {irrelevantPct.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-sm"
            style={{
              background: "#a855f7",
              boxShadow: "0 0 4px #a855f7",
            }}
          />
          <span className="text-purple-400 font-medium">
            Programmable {programmablePct.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Counts */}
      <div className="grid grid-cols-2 gap-3 pt-1">
        <div className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2">
          <div className="text-xs text-gray-500">OS Layer</div>
          <div className="text-lg font-semibold text-amber-400">
            {osCount}
            <span className="text-xs text-gray-500 font-normal ml-1">pairs</span>
          </div>
        </div>
        <div className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2">
          <div className="text-xs text-gray-500">
            APP Layer
            {selectedBehaviors.length > 0 && (
              <span className="text-purple-400 ml-1">
                ({selectedBehaviors.length} selected)
              </span>
            )}
          </div>
          <div className="text-lg font-semibold text-purple-400">
            {appCount}
            <span className="text-xs text-gray-500 font-normal ml-1">pairs</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ThreeLayerStats;
