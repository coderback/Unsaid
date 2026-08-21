"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { fetchDiff, startRun } from "@/lib/api";
import type { DiffResult, Classification } from "@/lib/types";
import { SummaryBar } from "@/components/SummaryBar";
import { ChangeCard } from "@/components/ChangeCard";
import { ExportModal } from "@/components/ExportModal";
import { LiveRunModal } from "@/components/LiveRunModal";
import { SIGNAL_ORDER } from "@/lib/constants";

type SectionFilter = "ALL" | "1A" | "7A";
type SortMode = "SEVERITY" | "CONFIDENCE_DESC" | "SECTION" | "ALPHABETICAL";

export default function DiffPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const ticker = (params.ticker as string).toUpperCase();
  const year1Param = searchParams.get("year1") ? Number(searchParams.get("year1")) : undefined;
  const year2Param = searchParams.get("year2") ? Number(searchParams.get("year2")) : undefined;

  const [data, setData] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting
  const [classFilter, setClassFilter] = useState<Classification | "ALL">("ALL");
  const [sectionFilter, setSectionFilter] = useState<SectionFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("SEVERITY");

  // Modals
  const [showExportModal, setShowExportModal] = useState(false);
  const [activeRerunJobId, setActiveRerunJobId] = useState<string | null>(null);
  const [rerunLoading, setRerunLoading] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    loadAnalysis();
  }, [ticker, year1Param, year2Param]);

  function loadAnalysis() {
    setLoading(true);
    setError(null);
    fetchDiff(ticker, year1Param, year2Param)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message ?? "Failed to load analysis");
        setLoading(false);
      });
  }

  async function handleLaunchRerun() {
    if (!data) return;
    setRerunLoading(true);
    try {
      const res = await startRun(data.ticker, data.year1, data.year2, {
        force: true,
      });
      setActiveRerunJobId(res.job_id);
    } catch (err: any) {
      alert(`Could not start re-run: ${err.message}`);
    } finally {
      setRerunLoading(false);
    }
  }

  function handleCopyShareLink() {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  }

  // Filter & Search & Sort logic
  const filteredChanges = useMemo(() => {
    if (!data?.changes) return [];

    let list = [...data.changes];

    // Filter by Classification
    if (classFilter !== "ALL") {
      list = list.filter((c) => c.classification === classFilter);
    }

    // Filter by Section
    if (sectionFilter !== "ALL") {
      list = list.filter((c) => c.section === sectionFilter);
    }

    // Filter by Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (c) =>
          (c.title && c.title.toLowerCase().includes(q)) ||
          (c.reasoning && c.reasoning.toLowerCase().includes(q)) ||
          (c.year1_quote && c.year1_quote.toLowerCase().includes(q)) ||
          (c.year2_quote_or_null && c.year2_quote_or_null.toLowerCase().includes(q))
      );
    }

    // Sorting
    list.sort((a, b) => {
      if (sortMode === "SEVERITY") {
        const ia = SIGNAL_ORDER.indexOf(a.classification as Classification);
        const ib = SIGNAL_ORDER.indexOf(b.classification as Classification);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      }
      if (sortMode === "CONFIDENCE_DESC") {
        return (b.confidence ?? 0) - (a.confidence ?? 0);
      }
      if (sortMode === "SECTION") {
        return (a.section || "").localeCompare(b.section || "");
      }
      if (sortMode === "ALPHABETICAL") {
        return (a.title || "").localeCompare(b.title || "");
      }
      return 0;
    });

    return list;
  }, [data?.changes, classFilter, sectionFilter, searchQuery, sortMode]);

  // Separate Signals vs Noise
  const signalChanges = filteredChanges.filter((c) =>
    ["REMOVED", "SOFTENED", "NEW", "ABSORBED"].includes(c.classification)
  );
  const noiseChanges = filteredChanges.filter((c) =>
    ["REWORDED", "RETAINED"].includes(c.classification)
  );

  if (error) {
    return (
      <main className="min-h-screen bg-[#09090b] font-mono flex flex-col text-zinc-100">
        <TopBar ticker={ticker} />
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="max-w-lg w-full text-center border border-zinc-800 bg-zinc-950 p-8 space-y-4">
            <span className="text-red-400 text-xs font-bold tracking-widest uppercase block">
              Analysis Not Available
            </span>
            <p className="text-zinc-200 text-sm font-semibold">{error}</p>
            <p className="text-zinc-500 text-xs leading-relaxed">
              This filing comparison has not been computed yet. You can launch an automated ingest run from the homepage terminal.
            </p>
            <div className="pt-4 flex justify-center gap-3">
              <Link
                href="/"
                className="text-xs bg-zinc-100 text-zinc-950 font-bold px-5 py-2.5 hover:bg-white transition-colors tracking-wider"
              >
                ← GO TO ANALYZER
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (loading || !data) {
    return (
      <main className="min-h-screen bg-[#09090b] font-mono flex flex-col text-zinc-100">
        <TopBar ticker={ticker} />
        <div className="flex-1 flex items-center justify-center py-20">
          <div className="text-center space-y-2">
            <span className="w-3 h-3 rounded-full bg-cyan-400 animate-ping inline-block mb-3" />
            <p className="text-zinc-400 text-xs tracking-widest">
              LOADING DISCLOSURE INTELLIGENCE…
            </p>
            <p className="text-zinc-600 text-[11px]">Querying cached comparisons for {ticker}</p>
          </div>
        </div>
      </main>
    );
  }

  const totalRisks = data.changes.length;
  const removedCount = data.summary_counts?.REMOVED ?? 0;
  const softenedCount = data.summary_counts?.SOFTENED ?? 0;
  const newCount = data.summary_counts?.NEW ?? 0;
  const absorbedCount = data.summary_counts?.ABSORBED ?? 0;
  const signalTotal = removedCount + softenedCount + newCount + absorbedCount;
  const signalPct = totalRisks > 0 ? Math.round((signalTotal / totalRisks) * 100) : 0;

  return (
    <main className="min-h-screen bg-[#09090b] font-mono text-zinc-100 flex flex-col selection:bg-cyan-500 selection:text-black">
      <TopBar
        ticker={data.ticker}
        onExport={() => setShowExportModal(true)}
        onRerun={handleLaunchRerun}
        onShare={handleCopyShareLink}
        rerunLoading={rerunLoading}
        copiedLink={copiedLink}
      />

      <div className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Company Header & Risk Meter Card */}
        <div className="border border-zinc-800 bg-zinc-950/80 p-6 space-y-5 shadow-xl">
          <div className="flex flex-wrap items-baseline justify-between gap-4 border-b border-zinc-850 pb-4">
            <div>
              <div className="flex items-baseline gap-3">
                <span className="text-2xl sm:text-3xl font-bold text-white tracking-wide">
                  [{data.ticker}]
                </span>
                <span className="text-sm text-zinc-300 font-medium truncate">
                  {data.company_name}
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-1 tracking-wider">
                COMPARING <strong className="text-zinc-300">FY{data.year1}</strong> ➔{" "}
                <strong className="text-zinc-300">FY{data.year2}</strong> · ITEM 1A (RISK FACTORS) + ITEM 7A (MARKET RISK)
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowExportModal(true)}
                className="text-xs bg-zinc-900 border border-zinc-700 hover:border-zinc-500 text-zinc-200 px-3 py-1.5 transition-colors font-medium flex items-center gap-1.5"
              >
                📥 EXPORT
              </button>
              <button
                onClick={handleLaunchRerun}
                disabled={rerunLoading}
                className="text-xs bg-zinc-900 border border-zinc-700 hover:border-zinc-500 text-zinc-200 px-3 py-1.5 transition-colors font-medium flex items-center gap-1.5"
              >
                🔄 RE-RUN
              </button>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 border border-zinc-850 bg-zinc-900/40">
              <span className="text-[10px] text-zinc-500 block uppercase">Signal Disclosures</span>
              <span className="text-lg font-bold text-red-400">
                {signalTotal} <span className="text-xs text-zinc-500 font-normal">({signalPct}%)</span>
              </span>
            </div>
            <div className="p-3 border border-zinc-850 bg-zinc-900/40">
              <span className="text-[10px] text-zinc-500 block uppercase">Removed Risks</span>
              <span className="text-lg font-bold text-red-400">{removedCount}</span>
            </div>
            <div className="p-3 border border-zinc-850 bg-zinc-900/40">
              <span className="text-[10px] text-zinc-500 block uppercase">Softened / Hedged</span>
              <span className="text-lg font-bold text-amber-400">{softenedCount}</span>
            </div>
            <div className="p-3 border border-zinc-850 bg-zinc-900/40">
              <span className="text-[10px] text-zinc-500 block uppercase">Total Disclosures</span>
              <span className="text-lg font-bold text-zinc-200">{totalRisks}</span>
            </div>
          </div>
        </div>

        {/* Filters and Search Command Bar */}
        <div className="space-y-3 bg-zinc-950/60 border border-zinc-800 p-4">
          {/* Classification Filter Bar */}
          <SummaryBar
            counts={data.summary_counts}
            activeFilter={classFilter}
            onFilter={setClassFilter}
          />

          {/* Secondary Controls: Section tabs, Search query, and Sorting */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            {/* Section tabs */}
            <div className="flex gap-1.5">
              {(["ALL", "1A", "7A"] as SectionFilter[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setSectionFilter(s)}
                  className={`text-xs px-3 py-1.5 border transition-colors ${
                    sectionFilter === s
                      ? "border-cyan-400 text-cyan-300 bg-cyan-950/40 font-bold"
                      : "border-zinc-800 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300"
                  }`}
                >
                  {s === "ALL" ? "ALL SECTIONS" : `ITEM ${s}`}
                </button>
              ))}
            </div>

            {/* Search Input & Sort Dropdown */}
            <div className="flex items-center gap-2 flex-1 sm:flex-initial sm:w-80">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search quotes, terms, reasoning…"
                className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-1.5 text-zinc-200 focus:outline-none focus:border-cyan-400 placeholder:text-zinc-600"
              />

              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as SortMode)}
                className="bg-zinc-900 border border-zinc-750 text-xs px-2 py-1.5 text-zinc-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="SEVERITY">Sort: Severity</option>
                <option value="CONFIDENCE_DESC">Sort: Confidence</option>
                <option value="SECTION">Sort: Section</option>
                <option value="ALPHABETICAL">Sort: Title</option>
              </select>
            </div>
          </div>
        </div>

        {/* Results Stream */}
        <div className="space-y-6">
          {/* Signal Findings (REMOVED, SOFTENED, NEW, ABSORBED) */}
          {signalChanges.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-zinc-400 uppercase tracking-widest font-semibold flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  Primary Risk Signals ({signalChanges.length})
                </span>
                <span className="text-[11px] text-zinc-600">Expanded by default</span>
              </div>

              {signalChanges.map((c, i) => (
                <ChangeCard
                  key={c.id ?? i}
                  change={c}
                  defaultExpanded={c.classification === "REMOVED" || i < 3}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-10 border border-zinc-850 text-zinc-600 text-xs">
              No signal changes matching your current filters.
            </div>
          )}

          {/* Noise Disclosures (REWORDED, RETAINED) */}
          {noiseChanges.length > 0 && (
            <details className="group border border-zinc-850 bg-zinc-950/40 p-3">
              <summary className="cursor-pointer text-xs text-zinc-500 tracking-wider flex items-center justify-between hover:text-zinc-300 transition-colors list-none select-none">
                <span className="flex items-center gap-2 font-semibold">
                  <span className="group-open:hidden">▶</span>
                  <span className="hidden group-open:inline">▼</span>
                  UNCHANGED / REWORDED DISCLOSURES ({noiseChanges.length})
                </span>
                <span className="text-[10px] text-zinc-600">
                  Cosmetic or retained risks without material economic shift
                </span>
              </summary>
              <div className="mt-4 pt-3 border-t border-zinc-850 space-y-3">
                {noiseChanges.map((c, i) => (
                  <ChangeCard key={c.id ?? i} change={c} defaultExpanded={false} />
                ))}
              </div>
            </details>
          )}
        </div>

        {/* Methodology Footer Note */}
        <div className="mt-12 pt-6 border-t border-zinc-900 text-xs text-zinc-600 leading-relaxed">
          <p>
            <strong className="text-zinc-400 font-semibold">Methodology:</strong> 10-K sections extracted from SEC EDGAR. Disclosure units segmented via Claude Sonnet. Dense neural alignment computed via all-mpnet-base-v2 (used for top-5 candidate recall only). Every risk shift evaluated by Claude Opus judge based on economic substance rather than stylistic phrasing (Lazy Prices anomaly, Cohen et al. 2020).
          </p>
        </div>
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <ExportModal data={data} onClose={() => setShowExportModal(false)} />
      )}

      {/* Live Run Re-run Modal */}
      {activeRerunJobId && (
        <LiveRunModal
          jobId={activeRerunJobId}
          ticker={data.ticker}
          year1={data.year1}
          year2={data.year2}
          onClose={() => {
            setActiveRerunJobId(null);
            loadAnalysis();
          }}
        />
      )}
    </main>
  );
}

interface TopBarProps {
  ticker: string;
  onExport?: () => void;
  onRerun?: () => void;
  onShare?: () => void;
  rerunLoading?: boolean;
  copiedLink?: boolean;
}

function TopBar({
  ticker,
  onExport,
  onRerun,
  onShare,
  rerunLoading,
  copiedLink,
}: TopBarProps) {
  return (
    <div className="border-b border-zinc-800 px-4 sm:px-6 py-3.5 flex items-center justify-between sticky top-0 bg-[#0a0a0a]/95 backdrop-blur z-20 font-mono">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="text-zinc-400 text-xs hover:text-white transition-colors tracking-wider font-semibold flex items-center gap-1"
        >
          ← TERMINAL
        </Link>
        <span className="text-zinc-800">|</span>
        <span className="text-sm font-bold text-white tracking-widest">[{ticker}]</span>
      </div>

      <div className="flex items-center gap-2">
        {onShare && (
          <button
            onClick={onShare}
            className="text-[11px] border border-zinc-800 hover:border-zinc-600 text-zinc-400 hover:text-zinc-200 px-2.5 py-1 transition-colors"
          >
            {copiedLink ? "✓ LINK COPIED" : "🔗 SHARE"}
          </button>
        )}
        {onExport && (
          <button
            onClick={onExport}
            className="text-[11px] border border-zinc-800 hover:border-zinc-600 text-zinc-300 px-2.5 py-1 transition-colors"
          >
            📄 EXPORT
          </button>
        )}
      </div>
    </div>
  );
}
