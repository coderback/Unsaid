interface SectionTagProps {
  section: string;
}

export function SectionTag({ section }: SectionTagProps) {
  const label = section === "7A" ? "ITEM 7A" : section === "1A" ? "ITEM 1A" : `ITEM ${section}`;
  const color =
    section === "7A"
      ? "text-cyan-400 border-cyan-700 bg-cyan-950/40"
      : "text-purple-400 border-purple-700 bg-purple-950/40";

  return (
    <span
      className={`inline-block font-mono text-xs px-2 py-0.5 border ${color} tracking-widest`}
    >
      {label}
    </span>
  );
}
