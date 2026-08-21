import type { ModelProvider } from "./types";

export interface AppSettings {
  defaultProvider: ModelProvider;
  
  // Azure AI Foundry
  azureEndpoint: string;
  azureModelJudge: string;
  azureModelSegmenter: string;
  azureApiKey: string;
  azureApiVersion: string;

  // Anthropic Claude
  anthropicModelJudge: string;
  anthropicModelSegmenter: string;
  anthropicApiKey: string;

  // OpenAI
  openaiModelJudge: string;
  openaiModelSegmenter: string;
  openaiApiKey: string;

  // SEC EDGAR Identity
  edgarIdentity: string;

  // Algorithm / Ingestion Tunables
  candidateSimilarityThreshold: number;
  maxCandidates: number;
}

export const DEFAULT_SETTINGS: AppSettings = {
  defaultProvider: "anthropic",
  
  azureEndpoint: "https://models.inference.ai.azure.com",
  azureModelJudge: "gpt-5.6-luna",
  azureModelSegmenter: "gpt-5.6-luna",
  azureApiKey: "",
  azureApiVersion: "2024-05-01-preview",

  anthropicModelJudge: "claude-opus-4-8",
  anthropicModelSegmenter: "claude-sonnet-4-6",
  anthropicApiKey: "",

  openaiModelJudge: "gpt-4o",
  openaiModelSegmenter: "gpt-4o-mini",
  openaiApiKey: "",

  edgarIdentity: "Unsaid/1.0 tobiojebiyi@gmail.com",
  candidateSimilarityThreshold: 0.20,
  maxCandidates: 5,
};

const SETTINGS_KEY = "unsaid_app_settings_v1";

export function loadSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: AppSettings): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    // Also sync keys to sessionStorage for active API callers
    if (settings.azureApiKey) sessionStorage.setItem("unsaid_azure_foundry_key", settings.azureApiKey);
    if (settings.anthropicApiKey) sessionStorage.setItem("unsaid_anthropic_key", settings.anthropicApiKey);
    if (settings.openaiApiKey) sessionStorage.setItem("unsaid_openai_key", settings.openaiApiKey);
    sessionStorage.setItem("unsaid_provider", settings.defaultProvider);
    sessionStorage.setItem("unsaid_azure_endpoint", settings.azureEndpoint);
  } catch (e) {
    console.error("Failed to save settings to localStorage:", e);
  }
}

export function resetSettings(): AppSettings {
  if (typeof window !== "undefined") {
    localStorage.removeItem(SETTINGS_KEY);
  }
  return DEFAULT_SETTINGS;
}
