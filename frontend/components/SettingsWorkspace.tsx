"use client";

import { useState, useEffect } from "react";
import { loadSettings, saveSettings, resetSettings, type AppSettings, DEFAULT_SETTINGS } from "@/lib/settings";
import { testConnection, deleteAnalysis } from "@/lib/api";
import type { HealthStatus, AnalysisLibraryItem, ModelProvider } from "@/lib/types";

interface SettingsWorkspaceProps {
  health: HealthStatus | null;
  library: AnalysisLibraryItem[];
  onSettingsUpdated?: () => void;
  onPurgeCache?: () => void;
}

type SettingsTab = "MODELS" | "CREDENTIALS" | "EDGAR" | "STORAGE";

interface PingStatus {
  testing: boolean;
  success?: boolean;
  latency_ms?: number;
  message?: string;
  error?: string;
}

export function SettingsWorkspace({
  health,
  library,
  onSettingsUpdated,
  onPurgeCache,
}: SettingsWorkspaceProps) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [activeTab, setActiveTab] = useState<SettingsTab>("MODELS");
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Connection testing states per provider
  const [azurePing, setAzurePing] = useState<PingStatus>({ testing: false });
  const [anthropicPing, setAnthropicPing] = useState<PingStatus>({ testing: false });
  const [openaiPing, setOpenaiPing] = useState<PingStatus>({ testing: false });

  // Purge cache state
  const [purgingCache, setPurgingCache] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  function handleSave() {
    saveSettings(settings);
    setSaveSuccess(true);
    if (onSettingsUpdated) onSettingsUpdated();
    setTimeout(() => setSaveSuccess(false), 2500);
  }

  function handleReset() {
    if (confirm("Reset all settings to default values?")) {
      const def = resetSettings();
      setSettings(def);
      if (onSettingsUpdated) onSettingsUpdated();
    }
  }

  async function handleTestAzure() {
    setAzurePing({ testing: true });
    try {
      const res = await testConnection({
        provider: "azure_foundry",
        model: settings.azureModelJudge,
        apiKey: settings.azureApiKey || undefined,
        azureEndpoint: settings.azureEndpoint || undefined,
        azureApiVersion: settings.azureApiVersion || undefined,
      });
      setAzurePing({
        testing: false,
        success: res.success,
        latency_ms: res.latency_ms,
        message: res.message,
        error: res.error,
      });
    } catch (err: any) {
      setAzurePing({
        testing: false,
        success: false,
        error: err.message || "Failed to reach backend diagnostics",
      });
    }
  }

  async function handleTestAnthropic() {
    setAnthropicPing({ testing: true });
    try {
      const res = await testConnection({
        provider: "anthropic",
        model: settings.anthropicModelJudge,
        apiKey: settings.anthropicApiKey || undefined,
      });
      setAnthropicPing({
        testing: false,
        success: res.success,
        latency_ms: res.latency_ms,
        message: res.message,
        error: res.error,
      });
    } catch (err: any) {
      setAnthropicPing({
        testing: false,
        success: false,
        error: err.message || "Failed to reach backend diagnostics",
      });
    }
  }

  async function handleTestOpenAI() {
    setOpenaiPing({ testing: true });
    try {
      const res = await testConnection({
        provider: "openai",
        model: settings.openaiModelJudge,
        apiKey: settings.openaiApiKey || undefined,
      });
      setOpenaiPing({
        testing: false,
        success: res.success,
        latency_ms: res.latency_ms,
        message: res.message,
        error: res.error,
      });
    } catch (err: any) {
      setOpenaiPing({
        testing: false,
        success: false,
        error: err.message || "Failed to reach backend diagnostics",
      });
    }
  }

  async function handlePurgeAllCache() {
    if (!confirm(`Are you sure you want to delete all ${library.length} cached analysis reports from disk?`)) return;
    setPurgingCache(true);
    try {
      for (const item of library) {
        await deleteAnalysis(item.ticker, item.year1, item.year2);
      }
      if (onPurgeCache) onPurgeCache();
      alert("All cached analyses have been purged.");
    } catch (err: any) {
      alert(`Purge failed: ${err.message}`);
    } finally {
      setPurgingCache(false);
    }
  }

  function handleExportSettings() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(settings, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = "unsaid_settings.json";
    a.click();
  }

  function handleImportSettings(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const imported = JSON.parse(ev.target?.result as string);
        const merged = { ...DEFAULT_SETTINGS, ...imported };
        setSettings(merged);
        saveSettings(merged);
        alert("Settings imported successfully.");
        if (onSettingsUpdated) onSettingsUpdated();
      } catch (err) {
        alert("Invalid JSON settings file.");
      }
    };
    reader.readAsText(file);
  }

  return (
    <div className="space-y-6">
      {/* Settings Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-2">
            <span>⚙️ System Configuration &amp; Inference Settings</span>
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Manage model inference providers (Azure AI Foundry, Anthropic, OpenAI), API keys, SEC identity, and disk cache.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {saveSuccess && (
            <span className="text-xs text-emerald-400 font-bold animate-pulse">
              ✓ Settings Saved
            </span>
          )}
          <button
            onClick={handleReset}
            className="text-xs border border-zinc-800 hover:border-zinc-600 text-zinc-400 px-3 py-1.5 transition-colors"
          >
            Reset Defaults
          </button>
          <button
            onClick={handleSave}
            className="text-xs bg-cyan-400 hover:bg-cyan-300 text-black font-bold px-4 py-1.5 transition-colors tracking-wider shadow"
          >
            SAVE CHANGES
          </button>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex gap-2 border-b border-zinc-850 pb-2">
        {[
          { id: "MODELS", label: "⚡ Model Inference Profiles" },
          { id: "CREDENTIALS", label: "🔑 API Keys & Live Ping" },
          { id: "EDGAR", label: "🏛️ SEC EDGAR Identity" },
          { id: "STORAGE", label: `💾 Disk Cache (${library.length} reports)` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as SettingsTab)}
            className={`text-xs px-3.5 py-2 font-mono transition-all border ${
              activeTab === tab.id
                ? "border-cyan-400 bg-cyan-950/30 text-cyan-300 font-bold"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===================================================================== */}
      {/* TAB 1: MODEL INFERENCE PROFILES */}
      {/* ===================================================================== */}
      {activeTab === "MODELS" && (
        <div className="space-y-6">
          {/* Primary Provider Selector */}
          <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
            <div>
              <label className="text-xs text-zinc-200 font-bold tracking-wider uppercase block mb-1">
                Active Default Model Provider
              </label>
              <p className="text-[11px] text-zinc-400">
                Determines which inference backend is used by default during 10-K risk disclosure analysis.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                {
                  id: "azure_foundry",
                  label: "🔷 Azure AI Foundry",
                  desc: "Supports GPT-5.6 Luna & custom Azure deployments",
                  available: health?.providers?.azure_foundry?.available || Boolean(settings.azureApiKey),
                },
                {
                  id: "anthropic",
                  label: "🟣 Anthropic Claude",
                  desc: "Claude Opus 4.8 (Judge) & Sonnet 4.6 (Segmenter)",
                  available: health?.providers?.anthropic?.available || Boolean(settings.anthropicApiKey),
                },
                {
                  id: "openai",
                  label: "🟢 OpenAI Direct",
                  desc: "GPT-4o & GPT-4o-mini",
                  available: health?.providers?.openai?.available || Boolean(settings.openaiApiKey),
                },
              ].map((prov) => (
                <button
                  key={prov.id}
                  type="button"
                  onClick={() => setSettings({ ...settings, defaultProvider: prov.id as ModelProvider })}
                  className={`p-4 border text-left transition-all ${
                    settings.defaultProvider === prov.id
                      ? "border-cyan-400 bg-cyan-950/30 text-white shadow-lg"
                      : "border-zinc-850 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-xs">{prov.label}</span>
                    {prov.available ? (
                      <span className="text-[9px] text-emerald-400 bg-emerald-950/40 border border-emerald-800 px-1.5 py-0.2">
                        READY
                      </span>
                    ) : (
                      <span className="text-[9px] text-zinc-500 border border-zinc-800 px-1.5 py-0.2">
                        NO KEY
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500">{prov.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Model Deployment Names Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Azure Foundry Models */}
            <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
              <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-2">
                <span>🔷 Azure AI Foundry Deployments</span>
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                    JUDGE MODEL DEPLOYMENT
                  </label>
                  <input
                    value={settings.azureModelJudge}
                    onChange={(e) => setSettings({ ...settings, azureModelJudge: e.target.value })}
                    placeholder="gpt-5.6-luna"
                    className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                  />
                  <p className="text-[10px] text-zinc-600 mt-1">
                    Evaluates economic substance &amp; risk severity (e.g. gpt-5.6-luna).
                  </p>
                </div>

                <div>
                  <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                    SEGMENTER MODEL DEPLOYMENT
                  </label>
                  <input
                    value={settings.azureModelSegmenter}
                    onChange={(e) => setSettings({ ...settings, azureModelSegmenter: e.target.value })}
                    placeholder="gpt-5.6-luna"
                    className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                  />
                  <p className="text-[10px] text-zinc-600 mt-1">
                    Segments monolithic Item 1A/7A text into units.
                  </p>
                </div>
              </div>
            </div>

            {/* Anthropic Models */}
            <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
              <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-2">
                <span>🟣 Anthropic Claude Models</span>
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                    JUDGE MODEL
                  </label>
                  <input
                    value={settings.anthropicModelJudge}
                    onChange={(e) => setSettings({ ...settings, anthropicModelJudge: e.target.value })}
                    placeholder="claude-opus-4-8"
                    className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                  />
                  <p className="text-[10px] text-zinc-600 mt-1">
                    Defaults to Claude Opus 4.8.
                  </p>
                </div>

                <div>
                  <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                    SEGMENTER MODEL
                  </label>
                  <input
                    value={settings.anthropicModelSegmenter}
                    onChange={(e) => setSettings({ ...settings, anthropicModelSegmenter: e.target.value })}
                    placeholder="claude-sonnet-4-6"
                    className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                  />
                  <p className="text-[10px] text-zinc-600 mt-1">
                    Defaults to Claude Sonnet 4.6.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Alignment & Ingestion Tunables */}
          <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
            <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
              Alignment &amp; Candidate Recall Parameters
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-400 font-semibold">CANDIDATE SIMILARITY THRESHOLD</span>
                  <span className="text-cyan-400 font-mono">{settings.candidateSimilarityThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.60"
                  step="0.05"
                  value={settings.candidateSimilarityThreshold}
                  onChange={(e) => setSettings({ ...settings, candidateSimilarityThreshold: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <p className="text-[10px] text-zinc-600">
                  Minimum dense embedding similarity for a Year-2 candidate to be presented to the judge.
                </p>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-400 font-semibold">MAX CANDIDATES PER UNIT</span>
                  <span className="text-cyan-400 font-mono">{settings.maxCandidates}</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="10"
                  step="1"
                  value={settings.maxCandidates}
                  onChange={(e) => setSettings({ ...settings, maxCandidates: parseInt(e.target.value, 10) })}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <p className="text-[10px] text-zinc-600">
                  Number of top semantic matches retrieved per Year-1 disclosure unit.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 2: API CREDENTIALS & LIVE DIAGNOSTICS */}
      {/* ===================================================================== */}
      {activeTab === "CREDENTIALS" && (
        <div className="space-y-6">
          {/* Azure AI Foundry Credentials */}
          <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-850 pb-3">
              <div>
                <h3 className="text-sm font-bold text-blue-400 flex items-center gap-2">
                  <span>🔷 Azure AI Foundry Configuration</span>
                </h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Connect to Azure AI Model Inference or Azure OpenAI endpoints.
                </p>
              </div>
              <button
                type="button"
                onClick={handleTestAzure}
                disabled={azurePing.testing}
                className="text-xs bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 transition-colors disabled:opacity-50"
              >
                {azurePing.testing ? "TESTING PING…" : "⚡ TEST AZURE CONNECTION"}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                  ENDPOINT URL
                </label>
                <input
                  value={settings.azureEndpoint}
                  onChange={(e) => setSettings({ ...settings, azureEndpoint: e.target.value })}
                  placeholder="https://models.inference.ai.azure.com"
                  className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                />
                <p className="text-[10px] text-zinc-600 mt-1">
                  Azure AI Inference or Azure OpenAI resource URL.
                </p>
              </div>

              <div>
                <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                  AZURE API KEY
                </label>
                <input
                  type="password"
                  value={settings.azureApiKey}
                  onChange={(e) => setSettings({ ...settings, azureApiKey: e.target.value })}
                  placeholder="Paste Azure key…"
                  className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
                />
                <p className="text-[10px] text-zinc-600 mt-1">
                  {health?.providers?.azure_foundry?.available ? "Server env key detected; custom key overrides." : "Stored securely in session storage."}
                </p>
              </div>
            </div>

            {/* Diagnostics Response Banner */}
            {azurePing.message && (
              <div className="p-3 bg-emerald-950/30 border border-emerald-800 text-emerald-300 text-xs flex items-center justify-between">
                <span>✓ {azurePing.message}</span>
                <span className="font-mono text-[11px]">{azurePing.latency_ms}ms</span>
              </div>
            )}
            {azurePing.error && (
              <div className="p-3 bg-red-950/30 border border-red-800 text-red-300 text-xs space-y-1">
                <p className="font-bold">✕ Azure Connection Test Failed ({azurePing.latency_ms}ms)</p>
                <p className="text-red-400 text-[11px]">{azurePing.error}</p>
              </div>
            )}
          </div>

          {/* Anthropic Claude Credentials */}
          <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-850 pb-3">
              <div>
                <h3 className="text-sm font-bold text-purple-400 flex items-center gap-2">
                  <span>🟣 Anthropic Claude API</span>
                </h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Direct API key for Claude Opus and Sonnet models.
                </p>
              </div>
              <button
                type="button"
                onClick={handleTestAnthropic}
                disabled={anthropicPing.testing}
                className="text-xs bg-purple-600 hover:bg-purple-500 text-white font-bold px-3 py-1.5 transition-colors disabled:opacity-50"
              >
                {anthropicPing.testing ? "TESTING PING…" : "⚡ TEST ANTHROPIC CONNECTION"}
              </button>
            </div>

            <div>
              <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                ANTHROPIC API KEY
              </label>
              <input
                type="password"
                value={settings.anthropicApiKey}
                onChange={(e) => setSettings({ ...settings, anthropicApiKey: e.target.value })}
                placeholder="sk-ant-..."
                className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <p className="text-[10px] text-zinc-600 mt-1">
                {health?.providers?.anthropic?.available ? "Server ANTHROPIC_API_KEY detected; custom key overrides." : "Stored securely in session storage."}
              </p>
            </div>

            {anthropicPing.message && (
              <div className="p-3 bg-emerald-950/30 border border-emerald-800 text-emerald-300 text-xs flex items-center justify-between">
                <span>✓ {anthropicPing.message}</span>
                <span className="font-mono text-[11px]">{anthropicPing.latency_ms}ms</span>
              </div>
            )}
            {anthropicPing.error && (
              <div className="p-3 bg-red-950/30 border border-red-800 text-red-300 text-xs space-y-1">
                <p className="font-bold">✕ Anthropic Test Failed ({anthropicPing.latency_ms}ms)</p>
                <p className="text-red-400 text-[11px]">{anthropicPing.error}</p>
              </div>
            )}
          </div>

          {/* OpenAI Direct Credentials */}
          <div className="border border-zinc-800 bg-zinc-950 p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-850 pb-3">
              <div>
                <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
                  <span>🟢 OpenAI Direct API</span>
                </h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Direct API key for standard OpenAI endpoints.
                </p>
              </div>
              <button
                type="button"
                onClick={handleTestOpenAI}
                disabled={openaiPing.testing}
                className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 transition-colors disabled:opacity-50"
              >
                {openaiPing.testing ? "TESTING PING…" : "⚡ TEST OPENAI CONNECTION"}
              </button>
            </div>

            <div>
              <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
                OPENAI API KEY
              </label>
              <input
                type="password"
                value={settings.openaiApiKey}
                onChange={(e) => setSettings({ ...settings, openaiApiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
            </div>

            {openaiPing.message && (
              <div className="p-3 bg-emerald-950/30 border border-emerald-800 text-emerald-300 text-xs flex items-center justify-between">
                <span>✓ {openaiPing.message}</span>
                <span className="font-mono text-[11px]">{openaiPing.latency_ms}ms</span>
              </div>
            )}
            {openaiPing.error && (
              <div className="p-3 bg-red-950/30 border border-red-800 text-red-300 text-xs space-y-1">
                <p className="font-bold">✕ OpenAI Test Failed ({openaiPing.latency_ms}ms)</p>
                <p className="text-red-400 text-[11px]">{openaiPing.error}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 3: SEC EDGAR IDENTITY */}
      {/* ===================================================================== */}
      {activeTab === "EDGAR" && (
        <div className="border border-zinc-800 bg-zinc-950 p-6 space-y-5">
          <div>
            <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wider mb-1">
              SEC EDGAR User-Agent Identity Header
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed max-w-2xl">
              The SEC requires all automated tools declaring access to the EDGAR system to transmit a specific user-agent string including contact information (e.g. &ldquo;Sample Company Name AdminContact@domain.com&rdquo;).
            </p>
          </div>

          <div>
            <label className="text-[11px] text-zinc-400 font-semibold block mb-1">
              USER-AGENT DECLARATION STRING
            </label>
            <input
              value={settings.edgarIdentity}
              onChange={(e) => setSettings({ ...settings, edgarIdentity: e.target.value })}
              placeholder="Unsaid/1.0 user@domain.com"
              className="w-full bg-zinc-900 border border-zinc-750 text-xs px-3 py-2.5 text-zinc-200 focus:outline-none focus:border-cyan-400 font-mono"
            />
            <p className="text-[10px] text-zinc-600 mt-1.5">
              Current default: <code className="text-zinc-400 font-mono">Unsaid/1.0 tobiojebiyi@gmail.com</code>
            </p>
          </div>

          <div className="p-4 border border-zinc-850 bg-black/40 space-y-2 text-xs text-zinc-400">
            <p className="font-bold text-zinc-200">Compliance &amp; Rate Limiting Rules:</p>
            <ul className="list-disc list-inside space-y-1 pl-1 text-[11px]">
              <li>Unsaid throttles requests to SEC EDGAR at &le; 10 requests per second.</li>
              <li>Filings are automatically cached locally after initial extraction to prevent redundant downloads.</li>
            </ul>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 4: STORAGE & BACKUP */}
      {/* ===================================================================== */}
      {activeTab === "STORAGE" && (
        <div className="space-y-6">
          {/* Disk Cache Management */}
          <div className="border border-zinc-800 bg-zinc-950 p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-850 pb-4">
              <div>
                <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wider">
                  Disk Cache Inspection &amp; Purge
                </h3>
                <p className="text-xs text-zinc-400 mt-1">
                  Currently holding <strong>{library.length}</strong> disclosure comparison reports in <code className="text-zinc-300 font-mono">cache/</code>.
                </p>
              </div>

              <button
                type="button"
                onClick={handlePurgeAllCache}
                disabled={purgingCache || library.length === 0}
                className="text-xs bg-red-950 border border-red-800 hover:border-red-600 text-red-300 px-4 py-2 font-bold transition-colors disabled:opacity-40"
              >
                {purgingCache ? "PURGING…" : "🗑 PURGE ALL CACHED ANALYSES"}
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {library.slice(0, 6).map((item) => (
                <div key={`${item.ticker}_${item.year1}_${item.year2}`} className="p-3 border border-zinc-850 bg-zinc-900/30 text-xs">
                  <div className="flex justify-between font-bold text-zinc-200">
                    <span>[{item.ticker}]</span>
                    <span className="text-zinc-500 font-normal">FY{item.year1}→FY{item.year2}</span>
                  </div>
                  <p className="text-zinc-400 text-[11px] truncate mt-1">{item.company_name}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Backup / Export Settings */}
          <div className="border border-zinc-800 bg-zinc-950 p-6 space-y-4">
            <h3 className="text-sm font-bold text-zinc-100 uppercase tracking-wider">
              Settings Backup &amp; Portability
            </h3>
            <p className="text-xs text-zinc-400">
              Export your configuration to a portable JSON profile or load an existing profile.
            </p>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleExportSettings}
                className="text-xs border border-zinc-700 hover:border-zinc-500 text-zinc-200 px-4 py-2 font-mono transition-colors"
              >
                📥 EXPORT SETTINGS JSON
              </button>

              <label className="text-xs border border-zinc-700 hover:border-zinc-500 text-zinc-200 px-4 py-2 font-mono transition-colors cursor-pointer inline-flex items-center">
                <span>📤 IMPORT SETTINGS JSON</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportSettings}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
