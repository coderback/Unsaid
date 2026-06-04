"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchDiff } from "@/lib/api";
import type { DiffResult, Classification } from "@/lib/types";
import { SummaryBar } from "@/components/SummaryBar";
import { ChangeCard } from "@/components/ChangeCard";
import { SIGNAL_ORDER } from "@/lib/constants";

type SectionFilter = "ALL" | "1A" | "7A";

export default function DiffPage() {
  const params = useParams();
  const router = useRouter();
  const ticker = (params.ticker as string).toUpperCase();

  const [data, setData] = useState<DiffResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [classFilter, setClassFilter] = useState<Classification | "ALL">("ALL");
  const [sectionFilter, setSectionFilter] = useState<SectionFilter>("ALL");

  useEffect(() => {
    fetchDiff(ticker)
      .then(setData)
      .catch((err) => setError(err.message ?? "Failed to load analysis"));
  }, [ticker]);

  if (error) {
    return (
      <main className="min-h-screen bg-[#0a0a0a] font-mono flex flex-col">
        <TopBar ticker={ticker} />
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="max-w-lg text-center">
            <p className="text-red-400 text-sm mb-2 tracking-widest">ERROR</p>
            <p className="text-zinc-300 text-sm mb-6">{error}</p>
            <p className="text-zinc-600 text-xs mb-6">
              This ticker may not be in the pre-computed cache. You can run the ingest
              pipeline via the API: <span className="text-zinc-400">POST /run</span>
            </p>
            <Link
              href="/"
              className="text-xs text-zinc-400 border border-zinc-700 px-4 py-2 hover:border-zinc-500 transition-colors"
            >
              ← BACK
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="min-h-screen bg-[#0a0a0a] font-mono flex flex-col">
        <TopBar ticker={ticker} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-zinc-600 text-xs animate-pulse tracking-widest">
            LOADING ANALYSIS…
          </p>
        </div>
      </main>
    );
  }

  // Sort changes by signal priority, then filter
  const sortedChanges = [...data.changes].sort((a, b) => {
    const ia = SIGNAL_ORDER.indexOf(a.classification as Classification);
    const ib = SIGNAL_ORDER.indexOf(b.classification as Classification);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const filteredChanges = sortedChanges.filter((c) => {
    const matchClass = classFilter === "ALL" || c.classification === classFilter;
    const matchSection = sectionFilter === "ALL" || c.section === sectionFilter;
    return matchClass && matchSection;
  });

  // Separate signals from noise
  const signalChanges = filteredChanges.filter((c) =>
    ["REMOVED", "SOFTENED", "NEW", "ABSORBED"].includes(c.classification)
  );
  const noiseChanges = filteredChanges.filter((c) =>
    ["REWORDED", "RETAINED"].includes(c.classification)
  );

  return (
    <main className="min-h-screen bg-[#0a0a0a] font-mono">
      <TopBar ticker={ticker} />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
        {/* Company header */}
        <div className="mb-5 pb-4 border-b border-zinc-800">
          <div className="flex flex-wrap items-baseline gap-3 mb-1">
            <span className="text-2xl font-bold text-zinc-100">[{data.ticker}]</span>
            <span className="text-zinc-400 text-sm">{data.company_name}</span>
          </div>
          <p className="text-xs text-zinc-500 tracking-wider">
            COMPARING FY{data.year1}&nbsp;→&nbsp;FY{data.year2}&nbsp;·&nbsp;
            ITEM 1A (RISK FACTORS) + ITEM 7A (MARKET RISK)
          </p>
        </div>

        {/* Summary bar + filters */}
        <SummaryBar
          counts={data.summary_counts}
          activeFilter={classFilter}
          onFilter={setClassFilter}
        />

        {/* Section filter tabs */}
        <div className="flex gap-2 py-3 border-b border-zinc-800 mb-6">
          {(["ALL", "1A", "7A"] as SectionFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setSectionFilter(s)}
              className={`font-mono text-xs px-3 py-1.5 border transition-colors ${
                sectionFilter === s
                  ? "border-zinc-400 text-zinc-100 bg-zinc-800"
                  : "border-zinc-700 text-zinc-500 hover:border-zinc-600"
              }`}
            >
              {s === "ALL" ? "ALL SECTIONS" : `ITEM ${s}`}
            </button>
          ))}
        </div>

        {/* Signal changes (REMOVED, SOFTENED, NEW, ABSORBED) */}
        {signalChanges.length > 0 ? (
          <div className="mb-8">
            {signalChanges.map((c, i) => (
              <ChangeCard
                key={c.id ?? i}
                change={c}
                defaultExpanded={c.classification === "REMOVED" || i < 3}
              />
            ))}
          </div>
        ) : (
          <p className="text-zinc-600 text-xs py-8 text-center">
            No signal changes for the current filter.
          </p>
        )}

        {/* Noise changes (REWORDED, RETAINED) — collapsed by default */}
        {noiseChanges.length > 0 && (
          <details className="group">
            <summary className="cursor-pointer text-xs text-zinc-600 tracking-wider py-3 border-t border-zinc-800 flex items-center gap-2 hover:text-zinc-400 transition-colors list-none">
              <span className="group-open:hidden">▶</span>
              <span className="hidden group-open:inline">▼</span>
              REWORDED / RETAINED ({noiseChanges.length}) — unchanged disclosures
            </summary>
            <div className="mt-4">
              {noiseChanges.map((c, i) => (
                <ChangeCard key={c.id ?? i} change={c} defaultExpanded={false} />
              ))}
            </div>
          </details>
        )}

        {/* Methodology note */}
        <div className="mt-10 pt-6 border-t border-zinc-900">
          <p className="text-xs text-zinc-700 leading-relaxed">
            <span className="text-zinc-600">Methodology:</span> Sections extracted from SEC
            EDGAR via edgartools. Disclosure units segmented by Claude Sonnet. Semantic
            alignment via all-mpnet-base-v2 (embeddings used for candidate recall only).
            Each classification made by Claude Opus — cosine similarity never determines
            the outcome. Based on the Lazy Prices anomaly (Cohen, Malloy &amp; Nguyen 2020).
          </p>
        </div>
      </div>
    </main>
  );
}

function TopBar({ ticker }: { ticker: string }) {
  return (
    <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between sticky top-0 bg-[#0a0a0a] z-10">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="text-zinc-600 text-xs hover:text-zinc-300 transition-colors tracking-wider"
        >
          ← UNSAID
        </Link>
        <span className="text-zinc-800">|</span>
        <span className="text-sm font-bold text-zinc-300 tracking-widest">{ticker}</span>
      </div>
      <span className="text-xs text-zinc-700 tracking-wider hidden sm:block">
        10-K DISCLOSURE DIFF
      </span>
    </div>
  );
}
