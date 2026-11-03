import type {
  DiffResult,
  DemoMeta,
  AnalysisLibraryItem,
  CompanyFilingMeta,
  JobProgressState,
  HealthStatus,
  RunOptions,
} from "./types";
import { DEMO_MODE, DEMO_DISABLED_MESSAGE } from "./demo";

async function demoIndex(): Promise<AnalysisLibraryItem[]> {
  const res = await fetch("/demo-data/index.json");
  if (!res.ok) throw new Error(`Could not load saved analyses: HTTP ${res.status}`);
  return res.json();
}

// In the browser, use Next.js rewrites proxy (/api/*) to avoid CORS issues.
// For SSR / server components, call FastAPI directly.
const API_BASE =
  typeof window !== "undefined"
    ? "/api"
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

export async function fetchHealth(): Promise<HealthStatus> {
  if (DEMO_MODE) {
    return { status: "demo", has_api_key: false, version: "demo", embed_model: "all-mpnet-base-v2" };
  }
  const res = await fetch(`${API_BASE}/health`, { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}

export async function fetchFilingYears(
  ticker: string,
  cik?: string
): Promise<CompanyFilingMeta> {
  if (DEMO_MODE) {
    const t = ticker.toUpperCase();
    const pairs = (await demoIndex()).filter((i) => i.ticker === t);
    if (pairs.length === 0) {
      throw new Error(`No saved analysis for '${t}' in this demo. ${DEMO_DISABLED_MESSAGE}`);
    }
    const years = [...new Set(pairs.flatMap((p) => [p.year1, p.year2]))].sort((a, b) => b - a);
    return {
      ticker: t,
      company_name: pairs[0].company_name,
      cik: "",
      filings: years.map((year) => ({ year, period_of_report: "", filing_date: "", accession_no: "", form: "10-K" })),
      total_available: pairs.length,
    };
  }
  const q = cik ? `?cik=${encodeURIComponent(cik)}` : "";
  const res = await fetch(`${API_BASE}/filings/${encodeURIComponent(ticker.toUpperCase())}${q}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to look up company filings" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchLibrary(): Promise<AnalysisLibraryItem[]> {
  if (DEMO_MODE) return demoIndex();
  const res = await fetch(`${API_BASE}/library`, {
    next: { revalidate: 0 },
    cache: "no-store",
  });
  if (!res.ok) {
    // Fallback to /demos
    const fallbackRes = await fetch(`${API_BASE}/demos`);
    if (!fallbackRes.ok) throw new Error(`HTTP ${fallbackRes.status}`);
    return fallbackRes.json();
  }
  return res.json();
}

export async function fetchDemos(): Promise<DemoMeta[]> {
  return fetchLibrary();
}

export async function fetchDiff(
  ticker: string,
  year1?: number,
  year2?: number
): Promise<DiffResult> {
  if (DEMO_MODE) {
    const t = ticker.toUpperCase();
    let y1 = year1;
    let y2 = year2;
    if (!y1 || !y2) {
      const pairs = (await demoIndex()).filter((i) => i.ticker === t);
      const last = pairs[pairs.length - 1];
      if (!last) throw new Error(`No saved analysis for '${t}' in this demo.`);
      y1 = last.year1;
      y2 = last.year2;
    }
    const res = await fetch(`/demo-data/${encodeURIComponent(t)}_${y1}_${y2}.json`);
    if (!res.ok) throw new Error(`No saved analysis for ${t} (FY${y1} to FY${y2}) in this demo.`);
    return res.json();
  }
  const params = new URLSearchParams();
  if (year1) params.set("year1", String(year1));
  if (year2) params.set("year2", String(year2));
  const queryStr = params.toString() ? `?${params.toString()}` : "";

  const res = await fetch(`${API_BASE}/diff/${ticker.toUpperCase()}${queryStr}`, {
    next: { revalidate: 0 },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis not found" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function startRun(
  ticker: string,
  year1: number,
  year2: number,
  options?: RunOptions
): Promise<{ job_id: string; status: string; ticker: string; provider?: string }> {
  if (DEMO_MODE) throw new Error(DEMO_DISABLED_MESSAGE);
  const res = await fetch(`${API_BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      year1,
      year2,
      cik: options?.cik || undefined,
      provider: options?.provider || "anthropic",
      model_judge: options?.model_judge || undefined,
      model_segmenter: options?.model_segmenter || undefined,
      api_key: options?.apiKey || undefined,
      azure_endpoint: options?.azureEndpoint || undefined,
      azure_api_version: options?.azureApiVersion || undefined,
      force: options?.force ?? false,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to start ingest run" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function pollJob(jobId: string): Promise<JobProgressState> {
  if (DEMO_MODE) throw new Error(DEMO_DISABLED_MESSAGE);
  const res = await fetch(`${API_BASE}/run/${jobId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Job status poll failed: HTTP ${res.status}`);
  return res.json();
}

export async function deleteAnalysis(
  ticker: string,
  year1?: number,
  year2?: number
): Promise<void> {
  if (DEMO_MODE) throw new Error(DEMO_DISABLED_MESSAGE);
  const params = new URLSearchParams();
  if (year1) params.set("year1", String(year1));
  if (year2) params.set("year2", String(year2));
  const queryStr = params.toString() ? `?${params.toString()}` : "";

  const res = await fetch(`${API_BASE}/cache/${ticker.toUpperCase()}${queryStr}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to delete analysis" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
}

export async function testConnection(options: {
  provider: string;
  model?: string;
  apiKey?: string;
  azureEndpoint?: string;
  azureApiVersion?: string;
}): Promise<{
  success: boolean;
  provider: string;
  model: string;
  latency_ms: number;
  message?: string;
  error?: string;
}> {
  if (DEMO_MODE) throw new Error(DEMO_DISABLED_MESSAGE);
  const res = await fetch(`${API_BASE}/health/test-connection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider: options.provider,
      model: options.model || undefined,
      api_key: options.apiKey || undefined,
      azure_endpoint: options.azureEndpoint || undefined,
      azure_api_version: options.azureApiVersion || undefined,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    return {
      success: false,
      provider: options.provider,
      model: options.model || "default",
      latency_ms: 0,
      error: err.error || err.detail || `HTTP ${res.status}`,
    };
  }
  return res.json();
}

