import { useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Sparkles, CheckCircle2, Circle, Loader2, History } from "lucide-react";
import Spinner from "../components/Spinner";
import LevelBadge from "../components/LevelBadge";
import AgentSprite from "../components/AgentSprite";
import ShadouMark from "../components/ShadouMark";
import TrainingProgressTree from "../components/TrainingProgressTree";
import { trainingApi, type Tenant, type TrainingSpecializationDef } from "../lib/api";

type Ctx = { tenant: Tenant };

export default function AgentTrainingPage() {
  const { tenant } = useOutletContext<Ctx>();
  const qc = useQueryClient();
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null);
  const [selectedBadge, setSelectedBadge] = useState<string | null>(null);
  const [prevLevel, setPrevLevel] = useState(tenant.training_summary?.current_level ?? 0);

  const { data: status, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["training", tenant.id],
    queryFn: () => trainingApi.status(tenant.id),
  });

  const { data: runs } = useQuery({
    queryKey: ["training-runs", tenant.id],
    queryFn: () => trainingApi.runs(tenant.id, 10),
  });

  const assessMut = useMutation({
    mutationFn: (opts?: { level?: number; specialization?: string }) =>
      trainingApi.assess(tenant.id, opts),
    onSuccess: async (data) => {
      const summary = data.summary as {
        current_level?: number;
        current_level_title?: string;
        earned_badges?: string[];
      };
      const newLv = summary.current_level ?? prevLevel;
      if (newLv > prevLevel) {
        toast.success(`Level up! You're now ${summary.current_level_title || `Level ${newLv}`}!`, {
          icon: "🏆",
          duration: 5000,
        });
        setPrevLevel(newLv);
      } else {
        toast.success("Certification run complete");
      }
      await qc.invalidateQueries({ queryKey: ["training", tenant.id] });
      await qc.invalidateQueries({ queryKey: ["training-runs", tenant.id] });
      await qc.invalidateQueries({ queryKey: ["tenantBySlug", tenant.slug] });
      await qc.invalidateQueries({ queryKey: ["tenants"] });
      refetch();
    },
    onError: (e: Error) => toast.error(e.message || "Assessment failed"),
  });

  const current = status?.current_level ?? 0;
  const earnedBadges = status?.earned_badges ?? tenant.training_summary?.earned_badges ?? [];
  const agentJob = status?.agent_job ?? tenant.training_summary?.agent_job ?? "customer_support";
  const agentJobLabel = status?.agent_job_label ?? tenant.training_summary?.agent_job_label ?? "Customer Support";

  const levelResultsMap = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(status?.level_results ?? {}).map(([k, v]) => [
          Number(k),
          { passed: v.passed, score_pct: v.score_pct },
        ]),
      ),
    [status?.level_results],
  );

  const activeLevel = selectedLevel ?? (current || 1);
  const selectedLevelDef = useMemo(
    () => status?.levels.find((l) => l.number === activeLevel),
    [status, activeLevel],
  );
  const selectedLevelResult = status?.level_results?.[activeLevel];

  const selectedSpec: TrainingSpecializationDef | undefined = useMemo(
    () => (status?.specializations ?? []).find((s) => s.id === selectedBadge),
    [status, selectedBadge],
  );
  const selectedBadgeResult = selectedBadge ? status?.badge_results?.[selectedBadge] : undefined;

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (isError || !status) {
    return (
      <div className="studio-page max-w-lg mx-auto py-16 text-center space-y-4">
        <p className="text-sm text-red-600">Could not load Academy data.</p>
        <p className="text-xs text-gray-500">{(error as Error)?.message || "Training API error"}</p>
        <button type="button" className="btn-primary text-sm" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="studio-page max-w-4xl mx-auto space-y-8 pb-12">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-600 via-indigo-600 to-purple-800 text-white p-8 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center gap-6">
          <AgentSprite
            level={current}
            earnedBadges={earnedBadges}
            agentJob={agentJob}
            size="lg"
            className="shrink-0"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-violet-200 text-sm font-medium mb-2">
              <ShadouMark size="xs" className="brightness-0 invert opacity-90" />
              {agentJobLabel} · Academy
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {current > 0 ? status?.current_level_title : "Train your agent"}
            </h1>
            <p className="mt-2 text-violet-100 text-sm max-w-lg">
              {current > 0
                ? (status.levels ?? []).find((l) => l.number === current)?.tagline
                : `Three core ${agentJobLabel} levels, then job-specific specialization badges — certification only.`}
            </p>
            {earnedBadges.length > 0 && (
              <p className="mt-2 text-xs text-violet-200">
                Badges:{" "}
                {(status.specializations ?? [])
                  .filter((s) => earnedBadges.includes(s.id))
                  .map((s) => s.title)
                  .join(", ")}
              </p>
            )}
            <div className="mt-6 flex flex-wrap items-end gap-4">
              <LevelBadge
                level={current}
                title={status?.current_level_title}
                emoji={status?.current_level_emoji}
                progress={status?.progress_to_next}
              />
              <button
                type="button"
                disabled={assessMut.isPending}
                onClick={() => assessMut.mutate({})}
                className="inline-flex items-center gap-2 rounded-xl bg-white text-violet-800 px-5 py-2.5 text-sm font-semibold shadow hover:bg-violet-50 disabled:opacity-60"
              >
                {assessMut.isPending ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
                Run full certification
              </button>
            </div>
            {status?.next_level != null && (
              <p className="mt-3 text-xs text-violet-200">
                {Math.round((status.progress_to_next ?? 0) * 100)}% progress toward Level {status.next_level}
              </p>
            )}
          </div>
        </div>
      </div>

      <section className="card p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Achievement progression</h2>
        <p className="text-xs text-gray-500 mb-6">Core levels first, then branch into Sales, Technical, or Logistics.</p>
        <TrainingProgressTree
          levels={status?.levels ?? []}
          specializations={status?.specializations ?? []}
          currentLevel={current}
          levelResults={levelResultsMap}
          badgeResults={status?.badge_results ?? {}}
          earnedBadges={earnedBadges}
          selectedLevel={selectedLevel}
          selectedBadge={selectedBadge}
          onSelectLevel={(n) => {
            setSelectedLevel(n);
            setSelectedBadge(null);
          }}
          onSelectBadge={(id) => {
            setSelectedBadge(id);
            setSelectedLevel(null);
          }}
        />
      </section>

      {selectedLevelDef && !selectedBadge && (
        <section className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {selectedLevelDef.emoji} Level {selectedLevelDef.number}: {selectedLevelDef.title}
          </h2>
          <p className="text-sm text-gray-600">{selectedLevelDef.meaning}</p>
          <button
            type="button"
            disabled={assessMut.isPending}
            onClick={() => assessMut.mutate({ level: selectedLevelDef.number })}
            className="btn-primary text-sm"
          >
            Try Level {selectedLevelDef.number} exam
          </button>
          <QuestList
            quests={
              selectedLevelResult?.quests ??
              selectedLevelDef.requirements.map((r) => ({ ...r, done: false }))
            }
          />
          <GateList gates={selectedLevelResult?.gates} />
          <Link to={`/t/${tenant.slug}/configuration`} className="text-sm text-brand-600 hover:underline">
            Edit FAQ & config
          </Link>
        </section>
      )}

      {selectedSpec && selectedBadge && (
        <section className="card p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {selectedSpec.emoji} {selectedSpec.title}
          </h2>
          <p className="text-xs uppercase tracking-wide text-gray-400">{selectedSpec.branch} specialization</p>
          <p className="text-sm text-gray-600">{selectedSpec.meaning}</p>
          {selectedBadgeResult?.locked ? (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {selectedBadgeResult.lock_reason || `Reach core level ${selectedSpec.prereq_level} first.`}
            </p>
          ) : (
            <button
              type="button"
              disabled={assessMut.isPending || current < selectedSpec.prereq_level}
              onClick={() => assessMut.mutate({ specialization: selectedSpec.id })}
              className="btn-primary text-sm"
            >
              Run {selectedSpec.title} badge exam
            </button>
          )}
          <QuestList
            quests={
              selectedBadgeResult?.quests ??
              selectedSpec.requirements.map((r) => ({ ...r, done: false }))
            }
          />
          <GateList gates={selectedBadgeResult?.gates} />
        </section>
      )}

      {status?.quests_next && status.quests_next.length > 0 && status.next_level != null && (
        <section className="card p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Next level quests</h2>
          <QuestList quests={status.quests_next} />
        </section>
      )}

      <section className="card p-6">
        <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <History size={16} />
          Certification history
        </h2>
        {!runs?.length ? (
          <p className="text-sm text-gray-500">No runs yet. Hit Run full certification to start.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {runs.map((r) => (
              <li key={r.id} className="py-3 flex justify-between text-sm">
                <span>
                  {r.level_number > 0 ? `Level ${r.level_number}` : "Full / badge"} ·{" "}
                  {r.passed ? "Passed" : "Not passed"}
                </span>
                <span className="text-gray-400">{(r.duration_ms / 1000).toFixed(1)}s</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function QuestList({ quests }: { quests: { id: string; text: string; done: boolean }[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Quests</h3>
      <ul className="space-y-2">
        {quests.map((q) => (
          <li key={q.id} className="flex items-start gap-2 text-sm">
            {q.done ? (
              <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <Circle size={18} className="text-gray-300 shrink-0 mt-0.5" />
            )}
            <span className={q.done ? "text-gray-700" : "text-gray-500"}>{q.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function GateList({ gates }: { gates?: { name: string; value: number | null; threshold: number; ok: boolean }[] }) {
  if (!gates?.length) return null;
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Gates</h3>
      <ul className="space-y-1 text-xs font-mono">
        {gates.map((g) => (
          <li key={g.name} className={g.ok ? "text-emerald-700" : "text-red-600"}>
            {g.ok ? "✓" : "✗"} {g.name}: {g.value ?? "—"} / {g.threshold}
          </li>
        ))}
      </ul>
    </div>
  );
}
