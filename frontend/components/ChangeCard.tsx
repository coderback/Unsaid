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
  const [copiedQuote, setCopiedQuote] = useState(false);
  const cfg = CLASS_CONFIG[change.classification] ?? CLASS_CONFIG.RETAINED;
  const isRemoved = change.classification === "REMOVED";
  const isSoftened = change.classification === "SOFTENED";
  const isNew = change.classification === "NEW";
  const confPct = Math.round((change.confidence ?? 0) * 100);

  function handleCopyQuote(e: React.MouseEvent) {
    e.stopPropagation();
    const textToCopy = `[${change.classification}] Item ${change.section}: ${change.title}\n\nYear-1 Disclosure:\n"${change.year1_quote || 'N/A'}"\n\nYear-2 Status:\n"${change.year2_quote_or_null || 'No corresponding disclosure found.'}"\n\nAnalysis:\n${change.reasoning}`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedQuote(true);
    setTimeout(() => setCopiedQuote(false), 2000);
  }

  return (
    <div
      className={`border-l-[4px] border border-zinc-800/80 ${cfg.bg} mb-3.5 transition-all hover:border-zinc-700 font-mono`}
      style={{ borderLeftColor: cfg.color }}
    >
      {/* Card Header */}
      <button
        className="w-full text-left px-4 py-3.5 flex items-start gap-3 select-text cursor-pointer focus:outline-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <span
              className="font-mono text-xs font-bold tracking-widest px-2.5 py-0.5 border"
              style={{ color: cfg.color, borderColor: cfg.color }}
            >
              {change.classification}
            </span>
            <SectionTag section={change.section} />
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 bg-zinc-900/60 px-2 py-0.5 border border-zinc-800">
              <span>conf</span>
              <span
                className={`font-semibold ${
                  confPct >= 85 ? "text-emerald-400" : confPct >= 70 ? "text-zinc-300" : "text-amber-400"
                }`}
              >
                {confPct}%
              </span>
            </div>
          </div>
          <p className="font-mono text-sm text-zinc-100 font-medium truncate">{change.title}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0 mt-0.5">
          <button
            onClick={handleCopyQuote}
            title="Copy disclosure quote and reasoning"
            className="text-[11px] text-zinc-500 hover:text-zinc-300 border border-zinc-800 hover:border-zinc-600 px-2 py-1 transition-colors"
          >
            {copiedQuote ? "✓ COPIED" : "📋 COPY"}
          </button>
          <span className="font-mono text-zinc-500 text-xs px-1">
            {expanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {/* Expanded Body: Comparative Disclosure Box */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3.5 border-t border-zinc-800/80 bg-black/30">
          {/* Side by side or stacked comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3">
            {/* Year-1 Disclosure */}
            <div className="flex flex-col">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-zinc-400 tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-zinc-500" />
                  YEAR-1 DISCLOSURE
                </span>
                {change.year1_quote && (
                  <span className="text-[10px] text-zinc-600">Verbatim Excerpt</span>
                )}
              </div>
              {change.year1_quote ? (
                <blockquote
                  className={`flex-1 text-xs leading-relaxed p-3.5 border-l-2 bg-zinc-950/80 ${
                    isRemoved
                      ? "border-red-500 text-red-200/90 bg-red-950/20"
                      : isSoftened
                      ? "border-amber-500/80 text-amber-200/90 bg-amber-950/20"
                      : "border-zinc-600 text-zinc-300"
                  }`}
                >
                  {change.year1_quote}
                </blockquote>
              ) : (
                <div className="flex-1 p-3.5 border border-zinc-850 bg-zinc-950/50 text-xs text-zinc-600 italic flex items-center justify-center">
                  — No Year-1 disclosure (first disclosed in Year-2) —
                </div>
              )}
            </div>

            {/* Year-2 Status */}
            <div className="flex flex-col">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-semibold text-zinc-400 tracking-wider flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      change.year2_quote_or_null ? "bg-cyan-400" : "bg-red-500"
                    }`}
                  />
                  YEAR-2 STATUS
                </span>
                {change.year2_quote_or_null && (
                  <span className="text-[10px] text-zinc-600">Verbatim Excerpt</span>
                )}
              </div>
              {change.year2_quote_or_null ? (
                <blockquote className="flex-1 text-xs leading-relaxed p-3.5 border-l-2 border-cyan-600 bg-cyan-950/15 text-zinc-200">
                  {change.year2_quote_or_null}
                </blockquote>
              ) : (
                <div className="flex-1 p-3.5 border border-red-900/60 bg-red-950/30 text-xs text-red-300 flex flex-col justify-center gap-1">
                  <p className="font-bold flex items-center gap-1.5 text-red-400">
                    ✕ DISCLOSURE REMOVED
                  </p>
                  <p className="text-[11px] text-red-400/80">
                    No corresponding risk disclosure found anywhere in the Year-2 filing.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* AI Analysis Reasoning Box */}
          {change.reasoning && (
            <div className="p-3.5 border border-zinc-800 bg-zinc-900/40 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold text-zinc-400 tracking-wider uppercase">
                  AI JUDGE RATIONALE
                </span>
                <span className="text-[10px] text-zinc-600">Claude Opus Economic Evaluation</span>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                {change.reasoning}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

