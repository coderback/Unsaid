import { DEMO_MODE, GITHUB_URL } from "@/lib/demo";

export function DemoBanner() {
  if (!DEMO_MODE) return null;
  return (
    <div
      role="note"
      className="border-b border-amber-700 bg-amber-950/60 px-4 sm:px-6 py-2 text-[11px] leading-relaxed text-amber-200 font-mono"
    >
      <strong className="font-bold tracking-wider">READ-ONLY DEMO.</strong>{" "}
      Replays saved pipeline results committed in the repo. This site makes no SEC EDGAR or LLM
      calls. Classifications are model output, not investment advice.{" "}
      <a href={GITHUB_URL} className="underline hover:text-amber-100">
        Source on GitHub
      </a>
    </div>
  );
}
