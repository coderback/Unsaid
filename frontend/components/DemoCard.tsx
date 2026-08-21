import Link from "next/link";
import type { DemoMeta, AnalysisLibraryItem } from "@/lib/types";

interface DemoCardProps {
  demo: DemoMeta | AnalysisLibraryItem;
  hero?: boolean;
}

export function DemoCard({ demo, hero = false }: DemoCardProps) {
  const removedCount = demo.summary_counts?.REMOVED ?? 0;
  const softenedCount = demo.summary_counts?.SOFTENED ?? 0;
  const newCount = demo.summary_counts?.NEW ?? 0;
  const absorbedCount = demo.summary_counts?.ABSORBED ?? 0;
  const totalSignals = removedCount + softenedCount + newCount + absorbedCount;

  return (
    <Link href={`/diff/${demo.ticker}?year1=${demo.year1}&year2=${demo.year2}`}>
      <div
        className={`border border-zinc-800 bg-zinc-900/60 hover:border-zinc-500 hover:bg-zinc-850/70
                    transition-all cursor-pointer group flex flex-col justify-between ${
                      hero ? "p-6 bg-gradient-to-b from-zinc-900/90 to-zinc-950" : "p-4"
                    }`}
      >
        <div>
          {/* Ticker + Name */}
          <div className="flex items-baseline gap-3 mb-2">
            <span
              className={`font-mono font-bold text-zinc-100 group-hover:text-cyan-400 transition-colors ${
                hero ? "text-2xl" : "text-lg"
              }`}
            >
              [{demo.ticker}]
            </span>
            <span className={`font-mono text-zinc-400 truncate ${hero ? "text-sm" : "text-xs"}`}>
              {demo.company_name}
            </span>
          </div>

          {/* Period */}
          <div className="flex items-center justify-between text-xs text-zinc-500 mb-3 tracking-wider font-mono">
            <span>
              FY{demo.year1}&nbsp;→&nbsp;FY{demo.year2}
            </span>
            {totalSignals > 0 ? (
              <span className="text-[11px] text-zinc-400 font-semibold">
                {totalSignals} {totalSignals === 1 ? "Signal" : "Signals"}
              </span>
            ) : (
              <span className="text-[11px] text-zinc-600">No shifts</span>
            )}
          </div>

          {/* Signal counts */}
          <div className="flex gap-2 flex-wrap mb-2">
            {removedCount > 0 && (
              <span className="font-mono text-xs text-red-400 border border-red-900 bg-red-950/30 px-2 py-0.5 font-medium">
                {removedCount} REMOVED
              </span>
            )}
            {softenedCount > 0 && (
              <span className="font-mono text-xs text-amber-400 border border-amber-900 bg-amber-950/30 px-2 py-0.5 font-medium">
                {softenedCount} SOFTENED
              </span>
            )}
            {newCount > 0 && (
              <span className="font-mono text-xs text-blue-400 border border-blue-900 bg-blue-950/30 px-2 py-0.5 font-medium">
                {newCount} NEW
              </span>
            )}
            {absorbedCount > 0 && (
              <span className="font-mono text-xs text-purple-400 border border-purple-900 bg-purple-950/30 px-2 py-0.5 font-medium">
                {absorbedCount} ABSORBED
              </span>
            )}
          </div>
        </div>

        {/* CTA */}
        <p className="font-mono text-xs text-zinc-600 mt-3 group-hover:text-cyan-400 transition-colors flex items-center gap-1.5 font-semibold">
          VIEW FULL ANALYSIS →
        </p>
      </div>
    </Link>
  );
}

