"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { DemoCard } from "@/components/DemoCard";
import { LiveRunModal } from "@/components/LiveRunModal";
import { SettingsWorkspace } from "@/components/SettingsWorkspace";
import { loadSettings } from "@/lib/settings";
import {
  fetchLibrary,
  fetchFilingYears,
  startRun,
  fetchHealth,
  deleteAnalysis,
} from "@/lib/api";
import type {
  AnalysisLibraryItem,
  CompanyFilingMeta,
  HealthStatus,
  ModelProvider,
} from "@/lib/types";

type TabView = "ANALYZER" | "LIBRARY" | "CASE_STUDIES" | "METHODOLOGY" | "SETTINGS";


const POPULAR_TICKERS = ["SIVB", "PTON", "META", "NVDA", "AAPL", "MSFT", "TSLA", "AMZN"];

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<TabView>("ANALYZER");
  const [ticker, setTicker] = useState("");
  const [cik, setCik] = useState("");
  const [forceRerun, setForceRerun] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Model & Provider configuration
  const [provider, setProvider] = useState<ModelProvider>("anthropic");
  const [modelJudge, setModelJudge] = useState<string>("claude-opus-4-8");
  const [modelSegmenter, setModelSegmenter] = useState<string>("claude-sonnet-4-6");
  const [azureEndpoint, setAzureEndpoint] = useState<string>("https://models.inference.ai.azure.com");
  const [azureApiVersion, setAzureApiVersion] = useState<string>("2024-05-01-preview");

  // API Keys per provider stored in state & session
  const [apiKey, setApiKey] = useState("");

  // Available filing years for selected ticker
  const [filingMeta, setFilingMeta] = useState<CompanyFilingMeta | null>(null);
  const [loadingFilings, setLoadingFilings] = useState(false);
  const [filingError, setFilingError] = useState<string | null>(null);
  const [year1, setYear1] = useState<number>(2021);
  const [year2, setYear2] = useState<number>(2022);

  // Library of cached analyses
  const [library, setLibrary] = useState<AnalysisLibraryItem[]>([]);
  const [librarySearch, setLibrarySearch] = useState("");
  const [loadingLibrary, setLoadingLibrary] = useState(true);

  // System status
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Live Ingest Modal state
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [startingRun, setStartingRun] = useState(false);

  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  // Load health & library on mount
  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        // Default to Azure if available and Anthropic is not
        if (!h.providers?.anthropic?.available && h.providers?.azure_foundry?.available) {
          selectProvider("azure_foundry");
        }
      })
      .catch(() => setHealth(null));

    loadLibrary();

    // Check sessionStorage for saved keys
    if (typeof window !== "undefined") {
      const savedProvider = (sessionStorage.getItem("unsaid_provider") as ModelProvider) || "anthropic";
      setProvider(savedProvider);
      loadSavedKeyForProvider(savedProvider);
      
      const savedEndpoint = sessionStorage.getItem("unsaid_azure_endpoint");
      if (savedEndpoint) setAzureEndpoint(savedEndpoint);

      const savedJudge = sessionStorage.getItem("unsaid_model_judge");
      if (savedJudge) setModelJudge(savedJudge);
    }
  }, []);

  function loadSavedKeyForProvider(p: ModelProvider) {
    if (typeof window === "undefined") return;
    const key = sessionStorage.getItem(`unsaid_${p}_key`) || "";
    setApiKey(key);
  }

  function selectProvider(p: ModelProvider) {
    setProvider(p);
    if (p === "azure_foundry") {
      setModelJudge("gpt-5.6-luna");
      setModelSegmenter("gpt-5.6-luna");
    } else if (p === "openai") {
      setModelJudge("gpt-4o");
      setModelSegmenter("gpt-4o-mini");
    } else {
      setModelJudge("claude-opus-4-8");
      setModelSegmenter("claude-sonnet-4-6");
    }

    if (typeof window !== "undefined") {
      sessionStorage.setItem("unsaid_provider", p);
    }
    loadSavedKeyForProvider(p);
  }

  function loadLibrary() {
    setLoadingLibrary(true);
    fetchLibrary()
      .then(setLibrary)
      .catch(() => setLibrary([]))
      .finally(() => setLoadingLibrary(false));
  }

  // When API key changes, persist to sessionStorage for current provider
  function handleApiKeyChange(val: string) {
    setApiKey(val);
    if (typeof window !== "undefined") {
      if (val) sessionStorage.setItem(`unsaid_${provider}_key`, val);
      else sessionStorage.removeItem(`unsaid_${provider}_key`);
    }
  }

  function handleEndpointChange(val: string) {
    setAzureEndpoint(val);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("unsaid_azure_endpoint", val);
    }
  }

  function handleJudgeChange(val: string) {
    setModelJudge(val);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("unsaid_model_judge", val);
    }
  }

  // Check if current ticker + year combo is already cached in library
  const isCached = Boolean(
    ticker &&
      library.some(
        (item) =>
          item.ticker.toUpperCase() === ticker.trim().toUpperCase() &&
          item.year1 === year1 &&
          item.year2 === year2
      )
  );

  // Lookup 10-K filing years on SEC EDGAR
  async function handleLookupFilings(targetTicker?: string) {
    const t = (targetTicker || ticker).trim().toUpperCase();
    if (!t) return;

    setLoadingFilings(true);
    setFilingError(null);

    try {
      const meta = await fetchFilingYears(t, cik || undefined);
      setFilingMeta(meta);

      // Auto set Year 1 and Year 2 to the latest consecutive years if available
      if (meta.filings && meta.filings.length >= 2) {
        const availableYears = meta.filings.map((f) => f.year).sort((a, b) => b - a);
        setYear2(availableYears[0]);
        setYear1(availableYears[1]);
      } else if (meta.filings && meta.filings.length === 1) {
        setYear2(meta.filings[0].year);
        setYear1(meta.filings[0].year - 1);
      }
    } catch (err: any) {
      setFilingError(err.message || "Could not retrieve filings from SEC EDGAR");
      setFilingMeta(null);
    } finally {
      setLoadingFilings(false);
    }
  }

  // Handle Ticker Selection
  function handleSelectTicker(sym: string) {
    setTicker(sym);
    if (sym === "SIVB") {
      setCik("0000719739");
    } else {
      setCik("");
    }
    handleLookupFilings(sym);
  }

  // Handle Analyze / Run submission
  async function handleAnalyzeSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (!t) return;

    if (year1 >= year2) {
      alert("Year-1 must be earlier than Year-2 (e.g. FY2021 → FY2022).");
      return;
    }

    // If already cached and not forcing re-run, navigate immediately
    if (isCached && !forceRerun) {
      router.push(`/diff/${t}?year1=${year1}&year2=${year2}`);
      return;
    }

    // Launch live ingest run
    setStartingRun(true);
    try {
      const res = await startRun(t, year1, year2, {
        cik: cik || undefined,
        provider,
        model_judge: modelJudge || undefined,
        model_segmenter: modelSegmenter || undefined,
        apiKey: apiKey || undefined,
        azureEndpoint: provider === "azure_foundry" ? azureEndpoint || undefined : undefined,
        azureApiVersion: provider === "azure_foundry" ? azureApiVersion || undefined : undefined,
        force: forceRerun,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      alert(`Could not start analysis run: ${err.message}`);
    } finally {
      setStartingRun(false);
    }
  }

  async function handleDeleteCacheItem(e: React.MouseEvent, t: string, y1: number, y2: number) {
    e.stopPropagation();
    e.preventDefault();
    if (!confirm(`Delete cached analysis for ${t} (FY${y1}→FY${y2})?`)) return;

    try {
      await deleteAnalysis(t, y1, y2);
      loadLibrary();
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`);
    }
  }

  // Filtered library results
  const filteredLibrary = library.filter((item) => {
    if (!librarySearch.trim()) return true;
    const q = librarySearch.toLowerCase();
    return (
      item.ticker.toLowerCase().includes(q) ||
      (item.company_name && item.company_name.toLowerCase().includes(q))
    );
  });

  const isCurrentProviderAvailable = Boolean(
    (provider === "anthropic" && health?.providers?.anthropic?.available) ||
    (provider === "azure_foundry" && health?.providers?.azure_foundry?.available) ||
    (provider === "openai" && health?.providers?.openai?.available) ||
    apiKey
  );

  return (
    <main className="min-h-screen bg-[#09090b] text-zinc-100 font-mono flex flex-col selection:bg-cyan-500 selection:text-black">
      {/* Top System Status Ribbon */}
      <div className="border-b border-zinc-800 bg-[#0c0c0e] px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between text-[11px] text-zinc-400 gap-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-zinc-300 font-semibold">SEC EDGAR API: Connected</span>
          </div>
          <span className="text-zinc-700">|</span>
          <div className="flex items-center gap-1.5 hidden sm:flex">
            <span className="text-zinc-500">Active Engine:</span>
            <span className="text-cyan-300 font-bold">
              {provider === "azure_foundry"
                ? `Azure AI Foundry (${modelJudge})`
                : provider === "openai"
                ? `OpenAI (${modelJudge})`
                : `Anthropic (${modelJudge})`}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isCurrentProviderAvailable ? (
            <span className="text-emerald-400 border border-emerald-900/60 bg-emerald-950/30 px-2 py-0.5 text-[10px]">
              ● Provider Ready
            </span>
          ) : (
            <span className="text-amber-400 border border-amber-900/60 bg-amber-950/30 px-2 py-0.5 text-[10px]">
              ⚠️ Needs API Key in Advanced Settings
            </span>
          )}
          <span className="text-zinc-600 text-[10px]">v1.2</span>
        </div>
      </div>

      {/* Main Header & Nav Tabs */}
      <header className="border-b border-zinc-800 px-4 sm:px-6 py-4 bg-[#0a0a0a]/90 backdrop-blur sticky top-0 z-20 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-[0.3em] text-white">UNSAID</span>
            <span className="text-[10px] text-cyan-400 uppercase tracking-widest hidden sm:inline">
              10-K Disclosure Intelligence Terminal
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex gap-1.5 bg-zinc-900/80 p-1 border border-zinc-800">
          {[
            { id: "ANALYZER", label: "⚡ ANALYZER" },
            { id: "LIBRARY", label: `📁 ARCHIVE (${library.length})` },
            { id: "CASE_STUDIES", label: "★ CASE STUDIES" },
            { id: "METHODOLOGY", label: "📖 METHODOLOGY" },
            { id: "SETTINGS", label: "⚙️ SETTINGS" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabView)}
              className={`text-xs px-3 py-1.5 font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-zinc-100 text-zinc-950 font-bold shadow"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8">
        {/* ========================================================================= */}
        {/* TAB 1: ANALYZER COMMAND CENTER */}
        {/* ========================================================================= */}
        {activeTab === "ANALYZER" && (
          <div className="space-y-8">
            {/* Hero Copy */}
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3 leading-tight">
                Semantic 10-K Disclosure-Removal <span className="text-red-400">Detector</span>
              </h1>
              <p className="text-sm text-zinc-300 leading-relaxed max-w-2xl">
                Companies announce good news loudly. They quietly bury bad news by removing or
                softening disclosures in Item 1A (Risk Factors) and Item 7A (Market Risk).
                Unsaid aligns units via semantic embeddings and evaluates shifts with frontier LLM judges.
              </p>
            </div>

            {/* Model Provider Selector Bar */}
            <div className="border border-zinc-800 bg-zinc-950/90 p-4 space-y-2.5">
              <span className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider block">
                Select Model Provider &amp; Inference Engine:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {/* Azure AI Foundry */}
                <button
                  type="button"
                  onClick={() => selectProvider("azure_foundry")}
                  className={`p-3 border text-left transition-all ${
                    provider === "azure_foundry"
                      ? "border-blue-500 bg-blue-950/30 text-blue-200 shadow-lg"
                      : "border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs">🔷 Azure AI Foundry</span>
                    {provider === "azure_foundry" && (
                      <span className="text-[10px] text-blue-400 font-mono">SELECTED</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    Model: <strong className="text-zinc-200">GPT-5.6 Luna</strong> (or custom deployment)
                  </p>
                </button>

                {/* Anthropic Claude */}
                <button
                  type="button"
                  onClick={() => selectProvider("anthropic")}
                  className={`p-3 border text-left transition-all ${
                    provider === "anthropic"
                      ? "border-purple-500 bg-purple-950/30 text-purple-200 shadow-lg"
                      : "border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs">🟣 Anthropic Claude</span>
                    {provider === "anthropic" && (
                      <span className="text-[10px] text-purple-400 font-mono">SELECTED</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    Judge: <strong className="text-zinc-200">Claude Opus 4.8</strong> · Sonnet 4.6
                  </p>
                </button>

                {/* Direct OpenAI */}
                <button
                  type="button"
                  onClick={() => selectProvider("openai")}
                  className={`p-3 border text-left transition-all ${
                    provider === "openai"
                      ? "border-emerald-500 bg-emerald-950/30 text-emerald-200 shadow-lg"
                      : "border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs">🟢 OpenAI Direct</span>
                    {provider === "openai" && (
                      <span className="text-[10px] text-emerald-400 font-mono">SELECTED</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    Model: <strong className="text-zinc-200">GPT-4o</strong>
                  </p>
                </button>
              </div>
            </div>

            {/* Quick-Pick Popular Tickers */}
            <div>
              <span className="text-[11px] text-zinc-500 tracking-wider uppercase mb-2 block">
                Quick Select Company / Case Study:
              </span>
              <div className="flex gap-2 flex-wrap">
                {POPULAR_TICKERS.map((t) => (
                  <button
                    key={t}
                    onClick={() => handleSelectTicker(t)}
                    className={`text-xs px-3 py-1.5 border font-mono transition-colors ${
                      ticker === t
                        ? "border-cyan-400 text-cyan-300 bg-cyan-950/40 font-bold"
                        : "border-zinc-800 bg-zinc-900/50 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200"
                    }`}
                  >
                    ${t}
                  </button>
                ))}
              </div>
            </div>

            {/* Main Interactive Analyzer Form */}
            <form
              onSubmit={handleAnalyzeSubmit}
              className="border border-zinc-800 bg-zinc-950/70 p-6 space-y-6 shadow-xl relative"
            >
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
                {/* Ticker Search Box */}
                <div className="md:col-span-5 space-y-1.5">
                  <label className="text-xs text-zinc-400 font-semibold tracking-wider flex items-center justify-between">
                    <span>STOCK TICKER / SYMBOL</span>
                    {loadingFilings && (
                      <span className="text-[11px] text-cyan-400 animate-pulse">
                        Querying EDGAR…
                      </span>
                    )}
                  </label>
                  <div className="flex gap-0">
                    <input
                      ref={inputRef}
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                      onBlur={() => handleLookupFilings()}
                      placeholder="e.g. NVDA, AAPL, SIVB"
                      maxLength={12}
                      className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm px-4 py-3 focus:outline-none focus:border-cyan-400 tracking-widest uppercase placeholder:text-zinc-700"
                    />
                    <button
                      type="button"
                      onClick={() => handleLookupFilings()}
                      className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs px-3 border border-zinc-700 border-l-0 transition-colors"
                      title="Inspect Available 10-K Years on EDGAR"
                    >
                      🔍
                    </button>
                  </div>
                </div>

                {/* Fiscal Year 1 */}
                <div className="md:col-span-3 space-y-1.5">
                  <label className="text-xs text-zinc-400 font-semibold tracking-wider">
                    BASE YEAR (FY-1)
                  </label>
                  {filingMeta?.filings && filingMeta.filings.length > 0 ? (
                    <select
                      value={year1}
                      onChange={(e) => setYear1(Number(e.target.value))}
                      className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm px-3 py-3 focus:outline-none focus:border-cyan-400"
                    >
                      {filingMeta.filings.map((f) => (
                        <option key={f.year} value={f.year}>
                          FY{f.year} ({f.period_of_report || f.filing_date})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      value={year1}
                      onChange={(e) => setYear1(Number(e.target.value))}
                      className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm px-4 py-3 focus:outline-none focus:border-cyan-400"
                    />
                  )}
                </div>

                {/* Fiscal Year 2 */}
                <div className="md:col-span-3 space-y-1.5">
                  <label className="text-xs text-zinc-400 font-semibold tracking-wider">
                    COMPARISON YEAR (FY-2)
                  </label>
                  {filingMeta?.filings && filingMeta.filings.length > 0 ? (
                    <select
                      value={year2}
                      onChange={(e) => setYear2(Number(e.target.value))}
                      className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm px-3 py-3 focus:outline-none focus:border-cyan-400"
                    >
                      {filingMeta.filings.map((f) => (
                        <option key={f.year} value={f.year}>
                          FY{f.year} ({f.period_of_report || f.filing_date})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      value={year2}
                      onChange={(e) => setYear2(Number(e.target.value))}
                      className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 font-mono text-sm px-4 py-3 focus:outline-none focus:border-cyan-400"
                    />
                  )}
                </div>

                {/* Submit Button */}
                <div className="md:col-span-1">
                  <button
                    type="submit"
                    disabled={!ticker.trim() || startingRun}
                    className={`w-full font-bold text-sm py-3.5 px-4 transition-all tracking-wider shrink-0 flex items-center justify-center ${
                      isCached && !forceRerun
                        ? "bg-cyan-400 text-black hover:bg-cyan-300"
                        : "bg-zinc-100 text-zinc-950 hover:bg-white"
                    } disabled:opacity-30 disabled:cursor-not-allowed`}
                  >
                    {startingRun ? "…" : "RUN →"}
                  </button>
                </div>
              </div>

              {/* Resolved Entity Banner */}
              {filingMeta && (
                <div className="p-3 border border-zinc-800 bg-zinc-900/60 flex flex-wrap items-center justify-between text-xs text-zinc-400 gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-200 font-semibold">{filingMeta.company_name}</span>
                    <span className="text-zinc-600">·</span>
                    <span className="text-zinc-500">CIK: {filingMeta.cik}</span>
                    <span className="text-zinc-600">·</span>
                    <span className="text-emerald-400">
                      {filingMeta.filings.length} 10-K Filings on EDGAR
                    </span>
                  </div>
                  {isCached && !forceRerun && (
                    <span className="text-cyan-400 font-bold bg-cyan-950/40 border border-cyan-800 px-2 py-0.5">
                      ⚡ PRE-COMPUTED CACHE AVAILABLE
                    </span>
                  )}
                </div>
              )}

              {filingError && (
                <div className="p-3 bg-amber-950/30 border border-amber-800 text-amber-300 text-xs">
                  ⚠️ {filingError}
                </div>
              )}

              {/* Advanced Settings Accordion */}
              <div className="pt-2 border-t border-zinc-850">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-2 focus:outline-none"
                >
                  <span>{showAdvanced ? "▼" : "▶"} Model &amp; Ingestion Configuration</span>
                  <span className="text-[10px] text-zinc-600">(Deployment name, Azure Endpoint, Custom API Key)</span>
                </button>

                {showAdvanced && (
                  <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 border border-zinc-800 bg-black/40">
                    {/* Model Deployment Name */}
                    <div className="space-y-1">
                      <label className="text-[11px] text-zinc-400 font-semibold">
                        MODEL / DEPLOYMENT NAME
                      </label>
                      <input
                        value={modelJudge}
                        onChange={(e) => handleJudgeChange(e.target.value)}
                        placeholder={provider === "azure_foundry" ? "gpt-5.6-luna" : "claude-opus-4-8"}
                        className="w-full bg-zinc-900 border border-zinc-700 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                      />
                      <p className="text-[10px] text-zinc-600">
                        Target model for risk judgments.
                      </p>
                    </div>

                    {/* Azure Endpoint (when Azure AI Foundry selected) */}
                    {provider === "azure_foundry" ? (
                      <div className="space-y-1">
                        <label className="text-[11px] text-zinc-400 font-semibold">
                          AZURE AI FOUNDRY ENDPOINT URL
                        </label>
                        <input
                          value={azureEndpoint}
                          onChange={(e) => handleEndpointChange(e.target.value)}
                          placeholder="https://models.inference.ai.azure.com"
                          className="w-full bg-zinc-900 border border-zinc-700 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                        />
                        <p className="text-[10px] text-zinc-600">
                          Azure AI Foundry or Serverless endpoint.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <label className="text-[11px] text-zinc-400 font-semibold">
                          SEC CIK NUMBER (OPTIONAL)
                        </label>
                        <input
                          value={cik}
                          onChange={(e) => setCik(e.target.value)}
                          placeholder="e.g. 0000719739"
                          className="w-full bg-zinc-900 border border-zinc-700 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                        />
                        <p className="text-[10px] text-zinc-600">
                          For delisted firms (e.g. SIVB).
                        </p>
                      </div>
                    )}

                    {/* API Key Input */}
                    <div className="space-y-1">
                      <label className="text-[11px] text-zinc-400 font-semibold">
                        {provider === "azure_foundry"
                          ? "AZURE AI FOUNDRY API KEY"
                          : provider === "openai"
                          ? "OPENAI API KEY"
                          : "ANTHROPIC API KEY"}
                      </label>
                      <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => handleApiKeyChange(e.target.value)}
                        placeholder="sk-..."
                        className="w-full bg-zinc-900 border border-zinc-700 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                      />
                      <p className="text-[10px] text-zinc-600">
                        Saved in browser session storage.
                      </p>
                    </div>

                    {/* Force Rerun & CIK for Azure */}
                    {provider === "azure_foundry" && (
                      <div className="space-y-1">
                        <label className="text-[11px] text-zinc-400 font-semibold">
                          SEC CIK NUMBER (OPTIONAL)
                        </label>
                        <input
                          value={cik}
                          onChange={(e) => setCik(e.target.value)}
                          placeholder="e.g. 0000719739"
                          className="w-full bg-zinc-900 border border-zinc-700 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                        />
                      </div>
                    )}

                    <div className="flex flex-col justify-center pt-2">
                      <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={forceRerun}
                          onChange={(e) => setForceRerun(e.target.checked)}
                          className="accent-cyan-500"
                        />
                        <span>Force Fresh Ingest</span>
                      </label>
                      <p className="text-[10px] text-zinc-600 mt-1">
                        Bypasses existing cache.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </form>

            {/* Quick Spotlight Case Studies Grid */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-zinc-400 uppercase tracking-widest font-semibold">
                  Featured Case Studies
                </span>
                <span className="text-xs text-zinc-600">Zero-Latency Instant Load</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {library.slice(0, 3).map((item) => (
                  <DemoCard key={`${item.ticker}_${item.year1}_${item.year2}`} demo={item} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: RESEARCH ARCHIVE / LIBRARY */}
        {/* ========================================================================= */}
        {activeTab === "LIBRARY" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
              <div>
                <h2 className="text-xl font-bold text-white tracking-wide">
                  Analysis Archive &amp; Research Library
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  All 10-K disclosure comparisons computed and cached on disk.
                </p>
              </div>

              {/* Search Filter */}
              <div className="w-full sm:w-64">
                <input
                  value={librarySearch}
                  onChange={(e) => setLibrarySearch(e.target.value)}
                  placeholder="Filter ticker / company…"
                  className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            {loadingLibrary ? (
              <p className="text-xs text-zinc-500 py-8 animate-pulse text-center">
                Loading research archive…
              </p>
            ) : filteredLibrary.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {filteredLibrary.map((item) => (
                  <div
                    key={`${item.ticker}_${item.year1}_${item.year2}`}
                    className="relative group border border-zinc-800 bg-zinc-950 p-4 hover:border-zinc-600 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-baseline justify-between mb-1">
                        <span className="text-lg font-bold text-zinc-100">
                          [{item.ticker}]
                        </span>
                        <div className="flex items-center gap-2">
                          {item.model_provider && (
                            <span className="text-[10px] text-zinc-500 border border-zinc-800 px-1.5 py-0.2">
                              {item.model_provider === "azure_foundry" ? "🔷 Azure" : "🟣 Claude"}
                            </span>
                          )}
                          <span className="text-xs text-zinc-500">
                            FY{item.year1} → FY{item.year2}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-400 truncate mb-3">{item.company_name}</p>

                      <div className="flex gap-2 flex-wrap mb-4">
                        {Boolean(item.summary_counts?.REMOVED) && (
                          <span className="text-xs text-red-400 border border-red-900 bg-red-950/20 px-2 py-0.5">
                            {item.summary_counts.REMOVED} REMOVED
                          </span>
                        )}
                        {Boolean(item.summary_counts?.SOFTENED) && (
                          <span className="text-xs text-amber-400 border border-amber-900 bg-amber-950/20 px-2 py-0.5">
                            {item.summary_counts.SOFTENED} SOFTENED
                          </span>
                        )}
                        {Boolean(item.summary_counts?.NEW) && (
                          <span className="text-xs text-blue-400 border border-blue-900 bg-blue-950/20 px-2 py-0.5">
                            {item.summary_counts.NEW} NEW
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between border-t border-zinc-900 pt-3 mt-2">
                      <button
                        onClick={() =>
                          router.push(`/diff/${item.ticker}?year1=${item.year1}&year2=${item.year2}`)
                        }
                        className="text-xs text-cyan-400 hover:text-cyan-300 font-bold tracking-wider"
                      >
                        OPEN REPORT →
                      </button>

                      <button
                        onClick={(e) =>
                          handleDeleteCacheItem(e, item.ticker, item.year1, item.year2)
                        }
                        title="Delete cached analysis"
                        className="text-[11px] text-zinc-600 hover:text-red-400 transition-colors"
                      >
                        🗑 Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-zinc-800 text-zinc-600 text-xs">
                No analyses found matching &quot;{librarySearch}&quot;.
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: CASE STUDIES */}
        {/* ========================================================================= */}
        {activeTab === "CASE_STUDIES" && (
          <div className="space-y-8">
            <div>
              <h2 className="text-xl font-bold text-white tracking-wide mb-1">
                Institutional Forensic Case Studies
              </h2>
              <p className="text-xs text-zinc-400">
                Verified historical disclosure shifts surfaced from real SEC filings.
              </p>
            </div>

            {/* SVB Case Study */}
            <div className="border-l-4 border-red-500 border border-zinc-800 bg-zinc-950 p-6 space-y-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-zinc-850 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-zinc-100">[SIVB] Silicon Valley Bank</h3>
                  <p className="text-xs text-red-400 font-semibold mt-0.5">
                    FY2021 vs FY2022 · 14 Days Before Failure · 4 REMOVED, 4 SOFTENED
                  </p>
                </div>
                <button
                  onClick={() => router.push("/diff/SIVB?year1=2021&year2=2022")}
                  className="bg-red-500 text-black text-xs font-bold px-4 py-2 hover:bg-red-400 tracking-wider"
                >
                  VIEW SIVB REPORT →
                </button>
              </div>

              <p className="text-xs text-zinc-300 leading-relaxed">
                On <strong>February 24, 2023</strong>, SVB filed its FY2022 10-K. On <strong>March 10, 2023</strong>, the bank collapsed in the second-largest bank failure in US history. Unsaid detected critical removals in <strong>Item 7A (Market Risk)</strong>:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 border border-zinc-800 bg-zinc-900/60 space-y-1.5">
                  <span className="text-red-400 font-bold uppercase text-[11px]">
                    1. Interest Rate Swap Termination (REMOVED)
                  </span>
                  <p className="text-zinc-400 text-[11px] leading-relaxed">
                    FY2021 disclosed active interest rate pay-fixed swaps reducing EVE sensitivity to -13.9%. FY2022 revealed hedges were terminated with zero replacement hedging disclosed.
                  </p>
                </div>
                <div className="p-3 border border-zinc-800 bg-zinc-900/60 space-y-1.5">
                  <span className="text-amber-400 font-bold uppercase text-[11px]">
                    2. -$5.7B EVE Table Elimination (SOFTENED)
                  </span>
                  <p className="text-zinc-400 text-[11px] leading-relaxed">
                    FY2021 quantified a catastrophic -27.7% / -$5,722M Economic Value of Equity loss on a +200bp rate hike. In FY2022, the EVE column was eliminated entirely from the filing table.
                  </p>
                </div>
              </div>
            </div>

            {/* Peloton Case Study */}
            <div className="border-l-4 border-amber-500 border border-zinc-800 bg-zinc-950 p-6 space-y-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-zinc-850 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-zinc-100">[PTON] Peloton Interactive</h3>
                  <p className="text-xs text-amber-400 font-semibold mt-0.5">
                    FY2021 vs FY2022 · Post-Pandemic Growth-to-Distress Transition
                  </p>
                </div>
                <button
                  onClick={() => router.push("/diff/PTON?year1=2021&year2=2022")}
                  className="border border-amber-500 text-amber-300 text-xs font-bold px-4 py-2 hover:bg-amber-950/40 tracking-wider"
                >
                  VIEW PTON REPORT →
                </button>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                Tracks the transition as pandemic hardware demand normalized. Identifies foreign currency exposure downgrades and credit agreement modification shifts in Item 7A.
              </p>
            </div>

            {/* Meta Case Study */}
            <div className="border-l-4 border-cyan-500 border border-zinc-800 bg-zinc-950 p-6 space-y-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-zinc-850 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-zinc-100">[META] Meta Platforms</h3>
                  <p className="text-xs text-cyan-400 font-semibold mt-0.5">
                    FY2021 vs FY2022 · Strategic Pivot toward Reality Labs &amp; Ad Restructuring
                  </p>
                </div>
                <button
                  onClick={() => router.push("/diff/META?year1=2021&year2=2022")}
                  className="border border-cyan-500 text-cyan-300 text-xs font-bold px-4 py-2 hover:bg-cyan-950/40 tracking-wider"
                >
                  VIEW META REPORT →
                </button>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                Highlights large-cap disclosure restructuring during the corporate rebranding and capital allocation shifts into virtual reality and AI compute infrastructure.
              </p>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: METHODOLOGY & ACADEMIC GROUNDING */}
        {/* ========================================================================= */}
        {activeTab === "METHODOLOGY" && (
          <div className="space-y-6 text-xs leading-relaxed text-zinc-300">
            <div className="border-b border-zinc-800 pb-4">
              <h2 className="text-xl font-bold text-white tracking-wide mb-1">
                Methodology &amp; Architecture Design
              </h2>
              <p className="text-zinc-500">
                How Unsaid overcomes semantic embedding limitations to perform deterministic disclosure diffing.
              </p>
            </div>

            <div className="p-4 border border-zinc-800 bg-zinc-950 space-y-3">
              <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider">
                1. The &ldquo;Lazy Prices&rdquo; Academic Foundation
              </h3>
              <p>
                Published in the <em>Journal of Finance</em> (Cohen, Malloy &amp; Nguyen 2020), the &ldquo;Lazy Prices&rdquo; research analyzed 20+ years of SEC 10-K filings. The findings:
              </p>
              <ul className="list-disc list-inside space-y-1 text-zinc-400 pl-2">
                <li>~86% of year-over-year textual changes in 10-Ks are negative in economic sentiment.</li>
                <li>Firms making significant disclosure changes subsequently underperform the market.</li>
                <li>Markets underprice language removals because diffing 100-page prose filings manually is computationally prohibitive for human analysts.</li>
              </ul>
            </div>

            <div className="p-4 border border-zinc-800 bg-zinc-950 space-y-3">
              <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider">
                2. Multi-Model Support &amp; Why Embeddings Alone Fail
              </h3>
              <p>
                Vector embeddings measure semantic closeness, but fail completely at <strong>negation</strong> and <strong>degree</strong>:
              </p>
              <div className="p-3 bg-black border border-zinc-800 space-y-2 text-[11px] font-mono">
                <p className="text-red-400">Sentence A: &ldquo;We are exposed to significant interest-rate risk.&rdquo;</p>
                <p className="text-emerald-400">Sentence B: &ldquo;We are no longer exposed to significant interest-rate risk.&rdquo;</p>
                <p className="text-zinc-500">→ Cosine Similarity: &gt;0.92 (High Match), yet economic meaning is 100% opposite.</p>
              </div>
              <p>
                In Unsaid, dense embeddings (`all-mpnet-base-v2`) are restricted strictly to <strong>candidate recall (Top-5)</strong>. Frontier judges (e.g. <strong>GPT-5.6 Luna on Azure AI Foundry</strong> or <strong>Claude Opus 4.8</strong>) evaluate the economic substance.
              </p>
            </div>

            <div className="p-4 border border-zinc-800 bg-zinc-950 space-y-3">
              <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider">
                3. The Critical Importance of Item 7A
              </h3>
              <p>
                Most risk diffing tools only extract Item 1A (Risk Factors). Crucial quantitative sensitivity tables, interest-rate swap disclosures, and market-value stress models reside in <strong>Item 7A (Market Risk)</strong>. SVB&apos;s EVE table elimination was entirely in Item 7A.
              </p>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: SYSTEM CONFIGURATION & SETTINGS */}
        {/* ========================================================================= */}
        {activeTab === "SETTINGS" && (
          <SettingsWorkspace
            health={health}
            library={library}
            onSettingsUpdated={() => {
              const loaded = loadSettings();
              setProvider(loaded.defaultProvider);
              if (loaded.defaultProvider === "azure_foundry") {
                setModelJudge(loaded.azureModelJudge);
                setModelSegmenter(loaded.azureModelSegmenter);
                setAzureEndpoint(loaded.azureEndpoint);
                setApiKey(loaded.azureApiKey);
              } else if (loaded.defaultProvider === "openai") {
                setModelJudge(loaded.openaiModelJudge);
                setModelSegmenter(loaded.openaiModelSegmenter);
                setApiKey(loaded.openaiApiKey);
              } else {
                setModelJudge(loaded.anthropicModelJudge);
                setModelSegmenter(loaded.anthropicModelSegmenter);
                setApiKey(loaded.anthropicApiKey);
              }
            }}
            onPurgeCache={() => {
              loadLibrary();
            }}
          />
        )}
      </div>

      {/* Live Run Ingestion Modal */}
      {activeJobId && (
        <LiveRunModal
          jobId={activeJobId}
          ticker={ticker.trim().toUpperCase()}
          year1={year1}
          year2={year2}
          onClose={() => {
            setActiveJobId(null);
            loadLibrary();
          }}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-zinc-900 px-6 py-4 mt-auto bg-[#070708]">
        <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between text-xs text-zinc-600 gap-2">
          <span>UNSAID · Multi-Model Disclosure Intelligence</span>
          <span>Azure AI Foundry (GPT-5.6 Luna) · Claude Opus · SEC EDGAR</span>
        </div>
      </footer>
    </main>
  );
}
