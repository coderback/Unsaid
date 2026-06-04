"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { DemoCard } from "@/components/DemoCard";
import { fetchDemos } from "@/lib/api";
import type { DemoMeta } from "@/lib/types";

export default function LandingPage() {
  const [ticker, setTicker] = useState("");
  const [demos, setDemos] = useState<DemoMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDemos()
      .then(setDemos)
      .catch(() => setDemos([]))
      .finally(() => setLoading(false));
  }, []);

  function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    router.push(`/diff/${t}`);
  }

  const heroDemo = demos.find((d) => d.ticker === "SIVB");
  const otherDemos = demos.filter((d) => d.ticker !== "SIVB");

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-zinc-100 font-mono">
      {/* Header bar */}
      <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-xl font-bold tracking-[0.3em] text-zinc-100">UNSAID</span>
          <span className="text-xs text-zinc-600 tracking-wider hidden sm:block">
            SEMANTIC 10-K DISCLOSURE ANALYSIS
          </span>
        </div>
        <span className="text-xs text-zinc-700 tracking-wider">v1.0</span>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-16">
        {/* Hero copy */}
        <div className="mb-14">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-zinc-100 mb-4 leading-tight">
            What did they
            <br />
            <span className="text-red-400">stop saying?</span>
          </h1>
          <p className="text-sm text-zinc-400 leading-relaxed max-w-xl mb-2">
            Companies broadcast good news loudly. They bury emerging risk quietly — by removing
            or softening disclosures in their annual 10-K filings.
          </p>
          <p className="text-sm text-zinc-500 leading-relaxed max-w-xl">
            Unsaid fetches two consecutive 10-K filings, semantically compares every risk
            disclosure in Item&nbsp;1A (Risk Factors) and Item&nbsp;7A (Market Risk), and
            surfaces what was quietly removed or downgraded — using Claude as the judge, not
            keyword matching.
          </p>

          {/* Honest framing */}
          <p className="mt-4 text-xs text-zinc-600 border-l-2 border-zinc-800 pl-3 max-w-xl leading-relaxed">
            Based on the &ldquo;Lazy Prices&rdquo; anomaly (Cohen, Malloy &amp; Nguyen 2020).
            This tool democratises a disclosure-diffing capability available in institutional
            platforms like AlphaSense. It surfaces changes in language — it does not make
            return predictions.
          </p>
        </div>

        {/* Ticker input */}
        <form onSubmit={handleAnalyze} className="mb-14">
          <p className="text-xs text-zinc-500 tracking-wider mb-3 uppercase">
            Analyze a company
          </p>
          <div className="flex gap-0 max-w-sm">
            <input
              ref={inputRef}
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
              maxLength={10}
              className="flex-1 bg-zinc-900 border border-zinc-700 border-r-0 text-zinc-100
                         font-mono text-sm px-4 py-3 focus:outline-none focus:border-zinc-500
                         placeholder:text-zinc-700 tracking-widest"
            />
            <button
              type="submit"
              disabled={!ticker.trim()}
              className="bg-zinc-100 text-zinc-900 font-mono font-bold text-sm px-6 py-3
                         hover:bg-white transition-colors disabled:opacity-30
                         disabled:cursor-not-allowed tracking-widest shrink-0"
            >
              ANALYZE&nbsp;→
            </button>
          </div>
          <p className="text-xs text-zinc-700 mt-2">
            Pre-cached tickers load instantly. New tickers run the full pipeline (~5 min).
          </p>
        </form>

        {/* Demo cards */}
        {!loading && demos.length > 0 && (
          <div>
            <p className="text-xs text-zinc-500 tracking-wider mb-4 uppercase">
              Featured Analyses
            </p>

            {heroDemo && (
              <div className="mb-5">
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <span className="text-xs text-red-500 tracking-wider font-bold">
                    ★ HEADLINE DEMO
                  </span>
                  <span className="text-xs text-zinc-600">
                    FY2022 10-K filed 24 Feb 2023 · Bank collapsed 10 Mar 2023
                  </span>
                </div>
                <DemoCard demo={heroDemo} hero />
              </div>
            )}

            {otherDemos.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {otherDemos.map((d) => (
                  <DemoCard key={d.ticker} demo={d} />
                ))}
              </div>
            )}
          </div>
        )}

        {loading && (
          <p className="text-xs text-zinc-600 font-mono animate-pulse">
            Loading demo analyses…
          </p>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-zinc-900 px-6 py-4 mt-auto">
        <p className="text-xs text-zinc-700 font-mono text-center">
          UNSAID · Semantic 10-K Disclosure Analysis · SEC EDGAR · Claude (Anthropic)
        </p>
      </footer>
    </main>
  );
}
