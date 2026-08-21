"use client";

import { useState } from "react";
import type { DiffResult } from "@/lib/types";

interface ExportModalProps {
  data: DiffResult;
  onClose: () => void;
}

type ExportType = "MARKDOWN" | "CSV" | "JSON";

export function ExportModal({ data, onClose }: ExportModalProps) {
  const [format, setFormat] = useState<ExportType>("MARKDOWN");
  const [copied, setCopied] = useState(false);

  function generateMarkdown(): string {
    const lines = [
      `# 10-K Disclosure Analysis: ${data.ticker} (${data.company_name})`,
      `**Comparison**: FY${data.year1} → FY${data.year2}`,
      `**Generated**: ${data.generated_at ? new Date(data.generated_at).toUTCString() : "N/A"}`,
      `**Engine**: Unsaid Semantic Disclosure Detector (Claude Opus Judge)`,
      "",
      "## Executive Summary",
      `| Metric | Count |`,
      `|---|---|`,
      `| REMOVED Disclosures | ${data.summary_counts?.REMOVED ?? 0} |`,
      `| SOFTENED Disclosures | ${data.summary_counts?.SOFTENED ?? 0} |`,
      `| NEW Disclosures | ${data.summary_counts?.NEW ?? 0} |`,
      `| ABSORBED Disclosures | ${data.summary_counts?.ABSORBED ?? 0} |`,
      `| REWORDED (Cosmetic) | ${data.summary_counts?.REWORDED ?? 0} |`,
      `| RETAINED (Unchanged) | ${data.summary_counts?.RETAINED ?? 0} |`,
      `| **Total Risks Evaluated** | **${data.changes.length}** |`,
      "",
      "---",
      "",
      "## Detailed Risk Classifications",
      "",
    ];

    data.changes.forEach((c, idx) => {
      lines.push(`### ${idx + 1}. [${c.classification}] ${c.title}`);
      lines.push(`- **Section**: Item ${c.section}`);
      lines.push(`- **Model Confidence**: ${Math.round((c.confidence ?? 0) * 100)}%`);
      lines.push("");
      if (c.year1_quote) {
        lines.push(`**Year-${data.year1} Verbatim Disclosure:**`);
        lines.push(`> ${c.year1_quote}`);
        lines.push("");
      }
      if (c.year2_quote_or_null) {
        lines.push(`**Year-${data.year2} Status:**`);
        lines.push(`> ${c.year2_quote_or_null}`);
        lines.push("");
      } else {
        lines.push(`**Year-${data.year2} Status:**`);
        lines.push(`> *No corresponding disclosure found in Year-${data.year2} filing.*`);
        lines.push("");
      }
      lines.push(`**AI Analytical Reasoning:**`);
      lines.push(`*${c.reasoning}*`);
      lines.push("");
      lines.push("---");
      lines.push("");
    });

    lines.push(
      "## Methodology Note",
      "Analysis produced by Unsaid. Disclosure units extracted from SEC EDGAR Item 1A & Item 7A, segmented via Claude Sonnet, aligned with all-mpnet-base-v2 embeddings, and evaluated by Claude Opus judge based on the Lazy Prices anomaly (Cohen, Malloy & Nguyen 2020)."
    );

    return lines.join("\n");
  }

  function generateCSV(): string {
    const headers = [
      "ID",
      "Ticker",
      "Section",
      "Title",
      "Classification",
      "Confidence",
      `Year_${data.year1}_Quote`,
      `Year_${data.year2}_Quote`,
      "AI_Reasoning",
    ];

    const rows = data.changes.map((c) => [
      `"${(c.id || "").replace(/"/g, '""')}"`,
      `"${data.ticker}"`,
      `"Item ${c.section}"`,
      `"${(c.title || "").replace(/"/g, '""')}"`,
      `"${c.classification}"`,
      `${c.confidence ?? 0}`,
      `"${(c.year1_quote || "").replace(/"/g, '""')}"`,
      `"${(c.year2_quote_or_null || "").replace(/"/g, '""')}"`,
      `"${(c.reasoning || "").replace(/"/g, '""')}"`,
    ]);

    return [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  }

  function generateJSON(): string {
    return JSON.stringify(data, null, 2);
  }

  const exportContent =
    format === "MARKDOWN"
      ? generateMarkdown()
      : format === "CSV"
      ? generateCSV()
      : generateJSON();

  function handleCopy() {
    navigator.clipboard.writeText(exportContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload() {
    const ext = format === "MARKDOWN" ? "md" : format === "CSV" ? "csv" : "json";
    const mime =
      format === "MARKDOWN"
        ? "text/markdown"
        : format === "CSV"
        ? "text/csv"
        : "application/json";
    const blob = new Blob([exportContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.ticker}_FY${data.year1}_FY${data.year2}_unsaid_analysis.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-3xl bg-[#0e0e0e] border border-zinc-700 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between bg-zinc-950">
          <div>
            <h3 className="text-sm font-bold text-zinc-100 tracking-wider">
              EXPORT ANALYSIS: [{data.ticker}]
            </h3>
            <p className="text-xs text-zinc-500">
              FY{data.year1} → FY{data.year2} · {data.changes.length} Disclosures
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xs px-2 py-1 border border-zinc-800 hover:border-zinc-600 transition-colors"
          >
            ✕ CLOSE
          </button>
        </div>

        {/* Format Selector Tabs */}
        <div className="flex border-b border-zinc-800 bg-zinc-950/60 px-6 pt-3 gap-2">
          {(["MARKDOWN", "CSV", "JSON"] as ExportType[]).map((f) => (
            <button
              key={f}
              onClick={() => setFormat(f)}
              className={`text-xs px-4 py-2 border-b-2 font-bold tracking-wider transition-colors ${
                format === f
                  ? "border-cyan-400 text-cyan-400 bg-zinc-900/50"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {f === "MARKDOWN" ? "📄 MARKDOWN REPORT" : f === "CSV" ? "📊 CSV SPREADSHEET" : "{ } RAW JSON"}
            </button>
          ))}
        </div>

        {/* Code Preview */}
        <div className="p-6 overflow-hidden flex-1 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-zinc-500 tracking-wider">
              PREVIEW ({format})
            </span>
            <span className="text-[11px] text-zinc-600">
              {exportContent.length.toLocaleString()} characters
            </span>
          </div>
          <pre className="flex-1 bg-black border border-zinc-800 p-4 text-xs text-zinc-300 overflow-y-auto whitespace-pre-wrap font-mono leading-relaxed select-all">
            {exportContent}
          </pre>
        </div>

        {/* Footer Actions */}
        <div className="border-t border-zinc-800 px-6 py-4 bg-zinc-950 flex items-center justify-between">
          <span className="text-xs text-zinc-500">
            Export ready for spreadsheet modeling or research memos
          </span>

          <div className="flex gap-3">
            <button
              onClick={handleCopy}
              className="border border-zinc-700 hover:border-zinc-500 text-zinc-300 text-xs px-4 py-2 transition-colors flex items-center gap-1.5"
            >
              {copied ? "✓ COPIED" : "📋 COPY TO CLIPBOARD"}
            </button>
            <button
              onClick={handleDownload}
              className="bg-zinc-100 text-zinc-950 font-bold text-xs px-5 py-2 hover:bg-white transition-colors tracking-wider"
            >
              ⬇ DOWNLOAD FILE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
