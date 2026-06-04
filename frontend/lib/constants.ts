import type { Classification } from "./types";

export const CLASS_CONFIG: Record<
  Classification,
  { label: string; color: string; border: string; bg: string; textColor: string }
> = {
  REMOVED: {
    label: "REMOVED",
    color: "#ef4444",
    border: "border-red-500",
    bg: "bg-red-950/40",
    textColor: "text-red-400",
  },
  SOFTENED: {
    label: "SOFTENED",
    color: "#f59e0b",
    border: "border-amber-500",
    bg: "bg-amber-950/40",
    textColor: "text-amber-400",
  },
  NEW: {
    label: "NEW",
    color: "#3b82f6",
    border: "border-blue-500",
    bg: "bg-blue-950/30",
    textColor: "text-blue-400",
  },
  REWORDED: {
    label: "REWORDED",
    color: "#6b7280",
    border: "border-zinc-600",
    bg: "bg-zinc-900/60",
    textColor: "text-zinc-400",
  },
  RETAINED: {
    label: "RETAINED",
    color: "#374151",
    border: "border-zinc-700",
    bg: "bg-zinc-900/40",
    textColor: "text-zinc-500",
  },
  ABSORBED: {
    label: "ABSORBED",
    color: "#8b5cf6",
    border: "border-violet-600",
    bg: "bg-violet-950/30",
    textColor: "text-violet-400",
  },
};

export const SIGNAL_ORDER: Classification[] = [
  "REMOVED",
  "SOFTENED",
  "NEW",
  "ABSORBED",
  "REWORDED",
  "RETAINED",
];
