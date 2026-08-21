"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { pollJob } from "@/lib/api";
import type { JobProgressState } from "@/lib/types";

interface LiveRunModalProps {
  jobId: string;
  ticker: string;
  year1: number;
  year2: number;
  onClose: () => void;
}

const PIPELINE_STEPS = [
  { id: "fetching", label: "SEC EDGAR Retrieval", desc: "Fetching 10-K filings" },
  { id: "extracting", label: "Section Extraction", desc: "Extracting Item 1A & Item 7A" },
  { id: "segmenting", label: "Semantic Segmentation", desc: "Claude Sonnet unit splitting" },
  { id: "aligning", label: "Neural Alignment", desc: "Dense sentence-transformers" },
  { id: "judging", label: "LLM Risk Judgment", desc: "Claude Opus economic analysis" },
  { id: "completed", label: "Compilation & Cache", desc: "Summary & result ready" },
];

export function LiveRunModal({
  jobId,
  ticker,
  year1,
  year2,
  onClose,
}: LiveRunModalProps) {
  const [jobState, setJobState] = useState<JobProgressState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    let isCancelled = false;

    async function checkStatus() {
      try {
        const state = await pollJob(jobId);
        if (isCancelled) return;
        setJobState(state);

        if (state.status === "done" || state.status === "error") {
          clearInterval(intervalId);
        }
      } catch (err: any) {
        if (!isCancelled) {
          setError(err.message || "Failed to poll job status");
        }
      }
    }

    // Immediate poll + periodic poll
    checkStatus();
    intervalId = setInterval(checkStatus, 1500);

    return () => {
      isCancelled = true;
      clearInterval(intervalId);
    };
  }, [jobId]);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [jobState?.logs]);

  function getStepStatus(stepId: string) {
    if (!jobState) return "pending";
    if (jobState.status === "error") {
      if (jobState.step === stepId) return "error";
    }
    if (jobState.status === "done") return "completed";

    const stepOrder = ["fetching", "extracting", "segmenting", "aligning", "judging", "caching", "completed"];
    const currentIdx = stepOrder.indexOf(jobState.step);
    const targetIdx = stepOrder.indexOf(stepId);

    if (currentIdx > targetIdx) return "completed";
    if (currentIdx === targetIdx) return "active";
    return "pending";
  }

  const isDone = jobState?.status === "done";
  const isError = jobState?.status === "error" || Boolean(error);
  const progressPct = jobState?.pct ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-2xl bg-[#0e0e0e] border border-zinc-700 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between bg-zinc-950">
          <div className="flex items-center gap-3">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <div>
              <h3 className="text-sm font-bold text-zinc-100 tracking-wider">
                ANALYSIS IN PROGRESS: [{ticker}]
              </h3>
              <p className="text-xs text-zinc-500">
                FY{year1} → FY{year2} · Job ID: {jobId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xs px-2 py-1 border border-zinc-800 hover:border-zinc-600 transition-colors"
          >
            ✕ CLOSE
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Status Message */}
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-400">
              {isDone
                ? "✓ Analysis successfully completed"
                : isError
                ? "✕ Ingestion halted due to error"
                : jobState?.message || "Preparing ingest pipeline…"}
            </span>
            <span className="font-bold text-cyan-400">{progressPct}%</span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-zinc-900 border border-zinc-800 h-2.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                isDone
                  ? "bg-emerald-500"
                  : isError
                  ? "bg-red-500"
                  : "bg-cyan-500"
              }`}
              style={{ width: `${Math.max(5, progressPct)}%` }}
            />
          </div>

          {/* Step Tracker */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border border-zinc-800 p-3 bg-zinc-950/40">
            {PIPELINE_STEPS.map((step, idx) => {
              const status = getStepStatus(step.id);
              return (
                <div
                  key={step.id}
                  className={`flex items-start gap-2.5 p-2 text-xs border ${
                    status === "active"
                      ? "border-cyan-700/60 bg-cyan-950/20 text-cyan-200"
                      : status === "completed"
                      ? "border-emerald-900/40 bg-emerald-950/10 text-zinc-300"
                      : status === "error"
                      ? "border-red-800/60 bg-red-950/20 text-red-300"
                      : "border-zinc-900 bg-transparent text-zinc-600"
                  }`}
                >
                  <span className="shrink-0 mt-0.5">
                    {status === "completed" && "✓"}
                    {status === "active" && "▶"}
                    {status === "error" && "✕"}
                    {status === "pending" && `${idx + 1}.`}
                  </span>
                  <div className="min-w-0">
                    <p className="font-semibold truncate">{step.label}</p>
                    <p className="text-[10px] text-zinc-500 truncate">{step.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Real-time execution logs console */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-zinc-500 uppercase tracking-widest">
                EXECUTION CONSOLE LOGS
              </span>
              <span className="text-[10px] text-zinc-600">
                {jobState?.logs?.length || 0} events
              </span>
            </div>
            <div
              ref={logContainerRef}
              className="bg-black border border-zinc-800 p-3 h-40 overflow-y-auto text-xs font-mono space-y-1"
            >
              {jobState?.logs && jobState.logs.length > 0 ? (
                jobState.logs.map((log, i) => (
                  <div key={i} className="flex gap-2 text-zinc-400 leading-relaxed">
                    <span className="text-zinc-600 select-none shrink-0">
                      {log.time ? log.time.split("T")[1]?.slice(0, 8) : "--:--:--"}
                    </span>
                    <span className="text-zinc-500 select-none shrink-0">
                      [{log.step.toUpperCase()}]
                    </span>
                    <span className="text-zinc-300">{log.msg}</span>
                  </div>
                ))
              ) : (
                <p className="text-zinc-600 italic">Waiting for pipeline events…</p>
              )}
            </div>
          </div>

          {/* Error notice if failed */}
          {isError && (
            <div className="p-3 bg-red-950/30 border border-red-800 text-red-300 text-xs">
              <p className="font-bold mb-1">Pipeline Execution Failed</p>
              <p className="text-red-400">{jobState?.message || error}</p>
              <p className="text-zinc-500 mt-2 text-[11px]">
                Tip: If this is an Anthropic rate limit or missing API key issue, make sure your ANTHROPIC_API_KEY is configured in your environment or provided in Advanced Options.
              </p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-zinc-800 px-6 py-4 bg-zinc-950 flex items-center justify-between">
          <span className="text-xs text-zinc-500">
            {isDone ? "Ready for review" : "Running background worker…"}
          </span>

          <div className="flex gap-3">
            {isDone ? (
              <button
                onClick={() => {
                  onClose();
                  router.push(`/diff/${ticker}`);
                }}
                className="bg-cyan-500 text-black font-bold text-xs px-5 py-2.5 hover:bg-cyan-400 transition-colors tracking-widest flex items-center gap-2"
              >
                VIEW ANALYSIS RESULTS →
              </button>
            ) : (
              <button
                onClick={onClose}
                className="border border-zinc-700 text-zinc-300 hover:border-zinc-500 text-xs px-4 py-2 transition-colors"
              >
                Run in Background
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
