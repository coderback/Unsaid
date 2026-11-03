// Read-only demo switch. When set at build time the frontend replays saved
// pipeline output from /demo-data and never contacts the API, SEC EDGAR or any LLM.
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "1";
export const GITHUB_URL = "https://github.com/coderback/Unsaid";
export const DEMO_DISABLED_MESSAGE =
  "Live runs are disabled in this read-only demo. It only replays saved results.";
