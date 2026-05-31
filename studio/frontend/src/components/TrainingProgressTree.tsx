import clsx from "clsx";
import { CheckCircle2, Lock, Circle } from "lucide-react";
import type { TrainingBadgeResult, TrainingLevelDef, TrainingSpecializationDef } from "../lib/api";

type NodeState = "cleared" | "current" | "in_progress" | "locked";

function coreState(lv: TrainingLevelDef, current: number, results: Record<number, { passed: boolean; score_pct: number }>): NodeState {
  if (lv.number <= current) return "cleared";
  if (lv.number === current + 1) return "current";
  const r = results[lv.number];
  if (r && r.score_pct > 0 && !r.passed) return "in_progress";
  return "locked";
}

function badgeState(
  spec: TrainingSpecializationDef,
  current: number,
  earned: string[],
  badgeResults: Record<string, TrainingBadgeResult>,
): NodeState {
  if (earned.includes(spec.id)) return "cleared";
  if (current < spec.prereq_level) return "locked";
  const r = badgeResults[spec.id];
  if (r?.locked) return "locked";
  if (r && r.score_pct > 0 && !r.passed) return "in_progress";
  if (current >= spec.prereq_level) return "current";
  return "locked";
}

function NodeIcon({ state }: { state: NodeState }) {
  if (state === "cleared") return <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />;
  if (state === "locked") return <Lock size={16} className="text-gray-400 shrink-0" />;
  return <Circle size={18} className={state === "current" ? "text-violet-500" : "text-amber-500"} />;
}

function nodeClasses(state: NodeState, selected: boolean) {
  return clsx(
    "rounded-xl border px-3 py-2.5 text-left transition-all min-w-0",
    state === "cleared" && "border-emerald-200 bg-emerald-50/90",
    state === "current" && "border-violet-300 bg-violet-50 ring-2 ring-violet-200",
    state === "in_progress" && "border-amber-200 bg-amber-50/80",
    state === "locked" && "border-gray-100 bg-gray-50 opacity-75",
    selected && "ring-2 ring-brand-500",
  );
}

export default function TrainingProgressTree({
  levels,
  specializations,
  currentLevel,
  levelResults,
  badgeResults,
  earnedBadges,
  selectedLevel,
  selectedBadge,
  onSelectLevel,
  onSelectBadge,
}: {
  levels: TrainingLevelDef[];
  specializations: TrainingSpecializationDef[];
  currentLevel: number;
  levelResults: Record<number, { passed: boolean; score_pct: number }>;
  badgeResults: Record<string, TrainingBadgeResult>;
  earnedBadges: string[];
  selectedLevel: number | null;
  selectedBadge: string | null;
  onSelectLevel: (n: number) => void;
  onSelectBadge: (id: string) => void;
}) {
  const sortedLevels = [...levels].sort((a, b) => a.number - b.number);
  const capLevel = sortedLevels[sortedLevels.length - 1]?.number ?? 3;

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4 self-start">Core path</p>
        <div className="flex flex-col items-center gap-0 w-full max-w-md">
          {sortedLevels.map((lv, idx) => {
            const st = coreState(lv, currentLevel, levelResults);
            return (
              <div key={lv.id} className="flex flex-col items-center w-full">
                <button
                  type="button"
                  onClick={() => onSelectLevel(lv.number)}
                  className={clsx("w-full flex items-center gap-3", nodeClasses(st, selectedLevel === lv.number))}
                >
                  <span className="text-2xl" aria-hidden>
                    {lv.emoji}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-gray-900">
                      Lv.{lv.number} · {lv.title}
                    </div>
                    <div className="text-[11px] text-gray-500 truncate">{lv.tagline}</div>
                  </div>
                  <NodeIcon state={st} />
                </button>
                {idx < sortedLevels.length - 1 && (
                  <div className="w-0.5 h-6 bg-gradient-to-b from-violet-300 to-violet-200 my-0.5" aria-hidden />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Specialization branches</p>
        <p className="text-xs text-gray-500 mb-4">
          Unlock after reaching Level {capLevel} — {specializations[0]?.prereq_level ?? 3} (Certified Chat Ranger).
        </p>
        <div className="relative pt-2">
          <div
            className="hidden sm:block absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-4 bg-violet-200"
            aria-hidden
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            {specializations.map((sp) => {
              const st = badgeState(sp, currentLevel, earnedBadges, badgeResults);
              return (
                <button
                  key={sp.id}
                  type="button"
                  onClick={() => onSelectBadge(sp.id)}
                  className={clsx("flex flex-col items-center gap-2", nodeClasses(st, selectedBadge === sp.id))}
                >
                  <span className="text-3xl" aria-hidden>
                    {sp.emoji}
                  </span>
                  <div className="text-center w-full">
                    <div className="font-semibold text-sm text-gray-900">{sp.title}</div>
                    <div className="text-[10px] uppercase tracking-wide text-gray-400 mt-0.5">{sp.branch}</div>
                  </div>
                  <NodeIcon state={st} />
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
