// Copies the saved pipeline results from ../cache into public/demo-data so the
// read-only demo can replay them as static files. Files are copied byte for byte.
import { copyFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const cacheDir = join(root, "..", "cache");
const outDir = join(root, "public", "demo-data");
mkdirSync(outDir, { recursive: true });

const index = [];
for (const name of readdirSync(cacheDir).sort()) {
  if (!name.endsWith(".json") || name.startsWith(".")) continue;
  const src = join(cacheDir, name);
  const d = JSON.parse(readFileSync(src, "utf8"));
  const c = d.summary_counts ?? {};
  copyFileSync(src, join(outDir, name));
  index.push({
    ticker: d.ticker,
    company_name: d.company_name,
    year1: d.year1,
    year2: d.year2,
    model_provider: d.model_provider,
    model_judge: d.model_judge,
    model_segmenter: d.model_segmenter,
    embed_backend: d.embed_backend,
    pipeline_version: d.pipeline_version,
    generated_at: d.generated_at,
    summary_counts: c,
    total_changes: (d.changes ?? []).length,
    signals_count: (c.REMOVED ?? 0) + (c.SOFTENED ?? 0) + (c.NEW ?? 0) + (c.ABSORBED ?? 0),
    sections: [...new Set((d.changes ?? []).map((x) => x.section))].sort(),
  });
}
writeFileSync(join(outDir, "index.json"), JSON.stringify(index));
console.log(`demo-data: ${index.length} saved analyses`);
