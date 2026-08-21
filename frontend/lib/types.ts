export type Classification =
  | "REMOVED"
  | "SOFTENED"
  | "NEW"
  | "REWORDED"
  | "RETAINED"
  | "ABSORBED";

export type ModelProvider = "anthropic" | "azure_foundry" | "openai";

export interface DisclosureChange {
  id: string;
  title: string;
  classification: Classification;
  year1_quote: string | null;
  year2_quote_or_null: string | null;
  reasoning: string;
  section: "1A" | "7A" | string;
  confidence: number;
}

export interface SummaryCounts {
  REMOVED?: number;
  SOFTENED?: number;
  NEW?: number;
  REWORDED?: number;
  RETAINED?: number;
  ABSORBED?: number;
  [key: string]: number | undefined;
}

export interface DiffResult {
  ticker: string;
  company_name: string;
  year1: number;
  year2: number;
  model_provider?: ModelProvider | string;
  model_judge?: string;
  model_segmenter?: string;
  generated_at: string;
  summary_counts: SummaryCounts;
  changes: DisclosureChange[];
}

export interface DemoMeta {
  ticker: string;
  company_name: string;
  year1: number;
  year2: number;
  model_provider?: string;
  model_judge?: string;
  summary_counts: SummaryCounts;
  total_changes?: number;
  signals_count?: number;
  generated_at?: string;
}

export interface AnalysisLibraryItem {
  ticker: string;
  company_name: string;
  year1: number;
  year2: number;
  model_provider?: string;
  model_judge?: string;
  model_segmenter?: string;
  generated_at?: string;
  summary_counts: SummaryCounts;
  total_changes?: number;
  signals_count?: number;
}

export interface FilingYearInfo {
  year: number;
  period_of_report: string;
  filing_date: string;
  accession_no: string;
  form: string;
}

export interface CompanyFilingMeta {
  ticker: string;
  company_name: string;
  cik: string;
  filings: FilingYearInfo[];
  total_available: number;
}

export interface JobLogEntry {
  time: string;
  step: string;
  pct: number;
  msg: string;
}

export interface JobProgressState {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  step: string;
  pct: number;
  ticker: string;
  year1: number;
  year2: number;
  provider?: string;
  model_judge?: string;
  model_segmenter?: string;
  message: string;
  details?: string | null;
  logs: JobLogEntry[];
  started_at: string;
  finished_at?: string | null;
  result_url?: string;
  result_path?: string;
}

export interface ProviderDetail {
  available: boolean;
  default_judge: string;
  default_segmenter: string;
}

export interface HealthStatus {
  status: string;
  has_api_key: boolean;
  version: string;
  providers?: {
    anthropic?: ProviderDetail;
    azure_foundry?: ProviderDetail;
    openai?: ProviderDetail;
    [key: string]: ProviderDetail | undefined;
  };
  embed_model: string;
}

export interface RunOptions {
  cik?: string;
  provider?: ModelProvider;
  model_judge?: string;
  model_segmenter?: string;
  apiKey?: string;
  azureEndpoint?: string;
  azureApiVersion?: string;
  force?: boolean;
}
