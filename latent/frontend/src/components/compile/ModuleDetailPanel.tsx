"use client";

import React from "react";
import type { CompileModule, OSLayerPair, AppLayerPair } from "@/types/compile";
import { ROLE_COLORS, BEHAVIOR_COLORS } from "@/types/compile";

interface ConnectionInfo {
  src: number;
  tgt: number;
  layer: "os" | "app";
  behavior?: string;
}

interface ModuleDetailPanelProps {
  module: CompileModule | null;
  connections: ConnectionInfo[];
  onClose: () => void;
}

export function ModuleDetailPanel({
  module: mod,
  connections,
  onClose,
}: ModuleDetailPanelProps) {
  if (!mod) return null;

  const roleColor = ROLE_COLORS[mod.role] || "#6b7280";

  // Group connections by layer
  const osConns = connections.filter((c) => c.layer === "os");
  const appConns = connections.filter((c) => c.layer === "app");

  return (
    <div className="bg-black/80 backdrop-blur-xl border border-white/15 rounded-2xl p-5 shadow-2xl w-80 relative">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-gray-500 hover:text-white transition-colors w-6 h-6 flex items-center justify-center rounded-full hover:bg-white/10"
        aria-label="Close"
      >
        x
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: roleColor + "20",
            color: roleColor,
            boxShadow: `0 0 12px ${roleColor}30`,
          }}
        >
          {mod.id}
        </div>
        <div>
          <h3 className="text-white font-semibold text-base">Module {mod.id}</h3>
          <span
            className="text-xs px-2 py-0.5 rounded-full capitalize"
            style={{
              backgroundColor: roleColor + "25",
              color: roleColor,
            }}
          >
            {mod.role}
          </span>
        </div>
      </div>

      {/* Properties grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-sm mb-5">
        <div>
          <div className="text-gray-500 text-xs">Neurons</div>
          <div className="text-white font-medium">
            {mod.n_neurons.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Cell Type</div>
          <div className="text-white font-medium capitalize">
            {mod.top_super_class}
          </div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Neurotransmitter</div>
          <div className="text-white font-medium uppercase">{mod.top_nt}</div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Brain Region</div>
          <div className="text-white font-medium">{mod.top_group}</div>
        </div>
      </div>

      {/* Connections */}
      <div className="border-t border-white/10 pt-4 space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Connections ({connections.length})
        </h4>

        {/* OS connections */}
        {osConns.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: "#f59e0b" }}
              />
              <span className="text-xs text-amber-400 font-medium">
                OS Layer ({osConns.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {osConns.slice(0, 12).map((c, i) => {
                const other = c.src === mod.id ? c.tgt : c.src;
                const direction = c.src === mod.id ? "->" : "<-";
                return (
                  <span
                    key={`os-${i}`}
                    className="text-xs bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded"
                  >
                    {direction} {other}
                  </span>
                );
              })}
              {osConns.length > 12 && (
                <span className="text-xs text-gray-500">
                  +{osConns.length - 12} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* APP connections */}
        {appConns.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: "#a855f7" }}
              />
              <span className="text-xs text-purple-400 font-medium">
                APP Layer ({appConns.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {appConns.slice(0, 12).map((c, i) => {
                const other = c.src === mod.id ? c.tgt : c.src;
                const direction = c.src === mod.id ? "->" : "<-";
                const color = c.behavior
                  ? BEHAVIOR_COLORS[c.behavior] || "#8b5cf6"
                  : "#8b5cf6";
                return (
                  <span
                    key={`app-${i}`}
                    className="text-xs px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: color + "15",
                      color: color,
                    }}
                  >
                    {direction} {other}
                    {c.behavior && (
                      <span className="opacity-60 ml-1 text-[10px]">
                        ({c.behavior})
                      </span>
                    )}
                  </span>
                );
              })}
              {appConns.length > 12 && (
                <span className="text-xs text-gray-500">
                  +{appConns.length - 12} more
                </span>
              )}
            </div>
          </div>
        )}

        {connections.length === 0 && (
          <p className="text-xs text-gray-500 italic">
            No connections for this module
          </p>
        )}
      </div>
    </div>
  );
}

export default ModuleDetailPanel;
