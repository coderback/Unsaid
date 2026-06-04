"use client";

import { useState } from "react";
import type { DisclosureChange } from "@/lib/types";
import { CLASS_CONFIG } from "@/lib/constants";
import { SectionTag } from "./SectionTag";

interface ChangeCardProps {
  change: DisclosureChange;
  defaultExpanded?: boolean;
}

export function ChangeCard({ change, defaultExpanded = false }: ChangeCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const cfg = CLASS_CONFIG[change.classification] ?? CLASS_CONFIG.RETAINED;
  const isSignal = ["REMOVED", "SOFTENED", "NEW"].includes(change.classification);

  return (
    <div
      className={`border-l-[3px] border border-zinc-800 ${cfg.bg} mb-3 transition-all`}
      style={{ borderLeftColor: cfg.color }}
    >
      {/* Header */}
      <button
        className="w-full text-left px-4 py-3 flex items-start gap-3"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span
              className={`font-mono text-xs font-bold tracking-widest px-2 py-0.5 border`}
              style={{ color: cfg.color, borderColor: cfg.color }}
            >
              {change.classification}
            </span>
            <SectionTag section={change.section} />
            <span className="font-mono text-xs text-zinc-500">
              conf&nbsp;{Math.round((change.confidence ?? 0) * 100)}%
            </span>
          </div>
          <p className="font-mono text-sm text-zinc-200 truncate">{change.title}</p>
        </div>
        <span className="font-mono text-zinc-600 text-xs mt-1 shrink-0">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Body */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-zinc-800/60">
          {/* Year-1 quote */}
          {change.year1_quote && (
            <div>
              <p className="font-mono text-xs text-zinc-500 mb-1 tracking-wider">
                YEAR-1 DISCLOSURE
              </p>
              <blockquote
                className={`font-mono text-xs leading-relaxed p-3 border-l-2 ${
                  change.classification === "REMOVED"
                    ? "border-red-600 bg-red-950/30 text-red-200"
                    : "border-zinc-600 bg-zinc-900/60 text-zinc-300"
                }`}
              >
                {change.year1_quote}
              </blockquote>
            </div>
          )}

          {/* Year-2 quote or removal notice */}
          <div>
            <p className="font-mono text-xs text-zinc-500 mb-1 tracking-wider">
              YEAR-2 STATUS
            </p>
            {change.year2_quote_or_null ? (
              <blockquote className="font-mono text-xs leading-relaxed p-3 border-l-2 border-zinc-600 bg-zinc-900/60 text-zinc-300">
                {change.year2_quote_or_null}
              </blockquote>
            ) : (
              <p className="font-mono text-xs text-red-400 italic p-3 border border-red-900/60 bg-red-950/20">
                ✕&nbsp; No corresponding disclosure found in Year-2 filing
              </p>
            )}
          </div>

          {/* Reasoning */}
          {change.reasoning && (
            <div>
              <p className="font-mono text-xs text-zinc-500 mb-1 tracking-wider">
                ANALYSIS
              </p>
              <p className="font-mono text-xs text-zinc-400 italic leading-relaxed">
                {change.reasoning}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
