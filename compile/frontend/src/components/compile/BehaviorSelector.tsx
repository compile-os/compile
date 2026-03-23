"use client";

import React from "react";
import type { FitnessFunction } from "@/types/compile";
import { BEHAVIOR_COLORS } from "@/types/compile";

interface BehaviorSelectorProps {
  selectedBehaviors: string[];
  onChange: (behaviors: string[]) => void;
  fitnessFunctions: FitnessFunction[];
}

export function BehaviorSelector({
  selectedBehaviors,
  onChange,
  fitnessFunctions,
}: BehaviorSelectorProps) {
  const toggle = (name: string) => {
    if (selectedBehaviors.includes(name)) {
      onChange(selectedBehaviors.filter((b) => b !== name));
    } else {
      onChange([...selectedBehaviors, name]);
    }
  };

  return (
    <div className="space-y-1.5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
        Behaviors
      </h3>
      {fitnessFunctions.map((ff) => {
        const isSelected = selectedBehaviors.includes(ff.name);
        const color = BEHAVIOR_COLORS[ff.name] || "#8b5cf6";
        const pairCount = ff.evolvable_pairs.length;

        return (
          <button
            key={ff.name}
            onClick={() => toggle(ff.name)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-all text-sm ${
              isSelected
                ? "bg-white/10 border border-white/20"
                : "bg-white/[0.03] border border-transparent hover:bg-white/[0.06]"
            }`}
          >
            {/* Color indicator / checkbox */}
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0 border"
              style={{
                backgroundColor: isSelected ? color : "transparent",
                borderColor: color,
                boxShadow: isSelected ? `0 0 6px ${color}50` : "none",
              }}
            />

            {/* Name */}
            <span
              className={`flex-1 capitalize ${
                isSelected ? "text-white font-medium" : "text-gray-400"
              }`}
            >
              {ff.name}
            </span>

            {/* Pair count badge */}
            <span
              className="text-xs px-1.5 py-0.5 rounded-full"
              style={{
                backgroundColor: isSelected ? color + "25" : "rgba(255,255,255,0.05)",
                color: isSelected ? color : "rgb(156,163,175)",
              }}
            >
              {pairCount} pairs
            </span>
          </button>
        );
      })}

      {fitnessFunctions.length === 0 && (
        <p className="text-xs text-gray-500 italic">Loading behaviors...</p>
      )}
    </div>
  );
}

export default BehaviorSelector;
