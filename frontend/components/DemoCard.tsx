import Link from "next/link";
import type { DemoMeta } from "@/lib/types";
import { CLASS_CONFIG } from "@/lib/constants";

interface DemoCardProps {
  demo: DemoMeta;
  hero?: boolean;
}

export function DemoCard({ demo, hero = false }: DemoCardProps) {
  const removedCount = demo.summary_counts?.REMOVED ?? 0;
  const softenedCount = demo.summary_counts?.SOFTENED ?? 0;
  const newCount = demo.summary_counts?.NEW ?? 0;

  return (
    <Link href={`/diff/${demo.ticker}`}>
      <div
        className={`border border-zinc-800 bg-zinc-900/60 hover:border-zinc-600 hover:bg-zinc-800/60
                    transition-all cursor-pointer group ${hero ? "p-6" : "p-4"}`}
      >
        {/* Ticker + Name */}
        <div className="flex items-baseline gap-3 mb-2">
          <span
            className={`font-mono font-bold text-zinc-100 ${hero ? "text-2xl" : "text-lg"}`}
          >
            [{demo.ticker}]
          </span>
          <span className={`font-mono text-zinc-400 ${hero ? "text-sm" : "text-xs"}`}>
            {demo.company_name}
          </span>
        </div>

        {/* Period */}
        <p className="font-mono text-xs text-zinc-500 mb-3 tracking-wider">
          FY{demo.year1}&nbsp;→&nbsp;FY{demo.year2}
        </p>

        {/* Signal counts */}
        <div className="flex gap-3 flex-wrap">
          {removedCount > 0 && (
            <span className="font-mono text-xs text-red-400 border border-red-900 px-2 py-0.5">
              {removedCount} REMOVED
            </span>
          )}
          {softenedCount > 0 && (
            <span className="font-mono text-xs text-amber-400 border border-amber-900 px-2 py-0.5">
              {softenedCount} SOFTENED
            </span>
          )}
          {newCount > 0 && (
            <span className="font-mono text-xs text-blue-400 border border-blue-900 px-2 py-0.5">
              {newCount} NEW
            </span>
          )}
        </div>

        {/* CTA */}
        <p className="font-mono text-xs text-zinc-600 mt-3 group-hover:text-zinc-400 transition-colors">
          VIEW ANALYSIS →
        </p>
      </div>
    </Link>
  );
}
