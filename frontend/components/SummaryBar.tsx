import type { SummaryCounts, Classification } from "@/lib/types";
import { CLASS_CONFIG, SIGNAL_ORDER } from "@/lib/constants";

interface SummaryBarProps {
  counts: SummaryCounts;
  activeFilter: Classification | "ALL";
  onFilter: (cls: Classification | "ALL") => void;
}

export function SummaryBar({ counts, activeFilter, onFilter }: SummaryBarProps) {
  const total = Object.values(counts).reduce((s, v) => (s ?? 0) + (v ?? 0), 0) ?? 0;

  return (
    <div className="flex flex-wrap items-center gap-2 py-3 border-b border-zinc-800">
      <button
        onClick={() => onFilter("ALL")}
        className={`font-mono text-xs px-3 py-1.5 border transition-colors ${
          activeFilter === "ALL"
            ? "border-zinc-400 text-zinc-100 bg-zinc-800"
            : "border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-300"
        }`}
      >
        ALL&nbsp;
        <span className="text-zinc-400">{total}</span>
      </button>

      {SIGNAL_ORDER.map((cls) => {
        const count = counts[cls] ?? 0;
        if (count === 0) return null;
        const cfg = CLASS_CONFIG[cls];
        const isActive = activeFilter === cls;
        return (
          <button
            key={cls}
            onClick={() => onFilter(cls)}
            style={isActive ? { borderColor: cfg.color } : {}}
            className={`font-mono text-xs px-3 py-1.5 border transition-colors ${
              isActive
                ? `${cfg.textColor}`
                : "border-zinc-700 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300"
            }`}
          >
            {cls}&nbsp;
            <span style={isActive ? { color: cfg.color } : {}} className="font-bold">
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
