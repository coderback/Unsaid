export type Classification =
  | "REMOVED"
  | "SOFTENED"
  | "NEW"
  | "REWORDED"
  | "RETAINED"
  | "ABSORBED";

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
  generated_at: string;
  summary_counts: SummaryCounts;
  changes: DisclosureChange[];
}

export interface DemoMeta {
  ticker: string;
  company_name: string;
  year1: number;
  year2: number;
  summary_counts: SummaryCounts;
}
