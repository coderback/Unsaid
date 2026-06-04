import type { DiffResult, DemoMeta } from "./types";

// In the browser, use the Next.js rewrites proxy (/api/*) to avoid CORS.
// For SSR / server components, call FastAPI directly.
const API_BASE =
  typeof window !== "undefined"
    ? "/api"
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

export async function fetchDiff(ticker: string): Promise<DiffResult> {
  const res = await fetch(`${API_BASE}/diff/${ticker.toUpperCase()}`, {
    next: { revalidate: 0 },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchDemos(): Promise<DemoMeta[]> {
  const res = await fetch(`${API_BASE}/demos`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function startRun(
  ticker: string,
  year1: number,
  year2: number,
  cik?: string
): Promise<{ job_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, year1, year2, cik }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function pollJob(
  jobId: string
): Promise<{ status: string; message: string; ticker?: string }> {
  const res = await fetch(`${API_BASE}/run/${jobId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
