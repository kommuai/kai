import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  ChevronRight,
  Clock,
  Coins,
  Zap,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Spinner from "../components/Spinner";
import UsageDailyChart from "../components/UsageDailyChart";
import WhatsAppWorkerBanner from "../components/WhatsAppWorkerBanner";
import LevelBadge from "../components/LevelBadge";
import AgentSprite from "../components/AgentSprite";
import ShadouMark from "../components/ShadouMark";
import {
  tenantsApi,
  usageApi,
  type Tenant,
  type WhatsAppWorkerTenantOut,
} from "../lib/api";
import { useAuthStore } from "../lib/auth";

function TenantCard({
  tenant,
  workerRow,
}: {
  tenant: Tenant;
  workerRow?: WhatsAppWorkerTenantOut;
}) {
  const level = tenant.training_summary?.current_level ?? 0;
  const earnedBadges = tenant.training_summary?.earned_badges ?? [];
  const agentJob = tenant.training_summary?.agent_job ?? "customer_support";
  const jobLabel = tenant.training_summary?.agent_job_label ?? "Customer Support";

  return (
    <Link
      to={`/t/${tenant.slug}/inbox`}
      className="card group flex flex-col p-5 hover:shadow-card-lg transition-all duration-200 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="rounded-2xl bg-gradient-to-br from-slate-100 to-violet-100 border border-violet-100/80 px-2 pt-3 pb-1 shadow-sm">
          <AgentSprite level={level} earnedBadges={earnedBadges} agentJob={agentJob} size="md" />
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="badge-purple">{tenant.slug}</span>
          {workerRow?.state === "connected" && (
            <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-full">
              WA live
            </span>
          )}
        </div>
      </div>

      <div className="flex-1">
        <h3 className="font-semibold text-gray-900 group-hover:text-brand-700 transition-colors">
          {tenant.display_name}
        </h3>
        <p className="text-[11px] text-gray-400 mt-0.5">{jobLabel}</p>
        {tenant.training_summary ? (
          <div className="mt-2">
            <LevelBadge
              level={tenant.training_summary.current_level}
              title={tenant.training_summary.current_level_title}
              emoji={tenant.training_summary.current_level_emoji}
              progress={tenant.training_summary.progress_to_next}
              size="sm"
            />
          </div>
        ) : tenant.description ? (
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">{tenant.description}</p>
        ) : null}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {formatDistanceToNow(new Date(tenant.updated_at), { addSuffix: true })}
        </span>
        <ChevronRight size={14} className="text-gray-300 group-hover:text-brand-500 transition-colors" />
      </div>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-5">
        <ShadouMark size="2xl" className="mx-auto" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">No agents yet</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-xs">
        Create your first support agent to get started.
      </p>
      <Link to="/tenants/new" className="btn-primary">
        <Plus size={16} />
        Create agent
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: tenants, isLoading } = useQuery({
    queryKey: ["tenants"],
    queryFn: tenantsApi.list,
  });

  const { data: worker } = useQuery({
    queryKey: ["whatsapp-worker"],
    queryFn: () => tenantsApi.whatsappWorker(),
    refetchInterval: 20_000,
    retry: false,
  });

  const {
    data: usage,
    isLoading: usageLoading,
    isError: usageError,
    error: usageErrorDetail,
  } = useQuery({
    queryKey: ["deepseek-usage", "day"],
    queryFn: () => usageApi.deepseek("day"),
    refetchInterval: 15_000,
    retry: 1,
  });

  const formatUsd = (n: number) =>
    n < 0.01 && n > 0 ? "< $0.01" : `$${n.toFixed(n >= 1 ? 2 : 4)}`;

  const formatTokens = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(2)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const firstName = user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "there";

  return (
    <div className="studio-page space-y-6 sm:space-y-8 animate-fade-in pb-4">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          {greeting}, {firstName} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your AI support agents from here.
        </p>
      </div>

      <WhatsAppWorkerBanner />

      {/* ── Stats row ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card p-4 flex items-center gap-4">
          <div className="rounded-xl p-2.5 text-amber-600 bg-amber-50">
            <Zap size={20} />
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">
              {usageLoading ? "…" : usageError ? "!" : usage ? formatTokens(usage.totals.total_tokens) : "0"}
            </div>
            <div className="text-xs text-gray-500">DeepSeek tokens (24h)</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-4">
          <div className="rounded-xl p-2.5 text-indigo-600 bg-indigo-50">
            <Coins size={20} />
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">
              {usageLoading ? "…" : usageError ? "!" : usage ? formatUsd(usage.totals.cost_usd) : "$0"}
            </div>
            <div className="text-xs text-gray-500">Est. spend (24h)</div>
          </div>
        </div>
      </div>

      {usageError && (
        <div className="card p-4 border-amber-200 bg-amber-50 text-sm text-amber-900">
          Could not load DeepSeek usage.{" "}
          {(usageErrorDetail as { message?: string })?.message ||
            "Check that Studio backend is running and the dashboard proxy includes /usage."}
        </div>
      )}

      {usage && !usageError && (
        <div className="card p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-gray-900">DeepSeek usage</h2>
              <p className="text-xs text-gray-500 mt-1">
                Last 24h summary · 14-day daily trend (updates live)
              </p>
            </div>
            <div className="text-xs text-gray-500 text-right">
              <div>{usage.totals.request_count} API calls (24h)</div>
              <div>
                In: {formatTokens(usage.totals.prompt_tokens)}
                {usage.totals.cached_prompt_tokens > 0 && (
                  <span className="text-emerald-600">
                    {" "}
                    ({formatTokens(usage.totals.cached_prompt_tokens)} cached)
                  </span>
                )}
                {" · "}
                Out: {formatTokens(usage.totals.completion_tokens)}
              </div>
            </div>
          </div>

          {usage.daily?.length > 0 && <UsageDailyChart daily={usage.daily} />}

          {usage.tenants.some((t) => t.total_tokens > 0) ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                    <th className="pb-2 font-medium">Agent</th>
                    <th className="pb-2 font-medium text-right">Tokens</th>
                    <th className="pb-2 font-medium text-right">Est. USD</th>
                    <th className="pb-2 font-medium text-right">Calls</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.tenants
                    .filter((t) => t.total_tokens > 0)
                    .sort((a, b) => b.cost_usd - a.cost_usd)
                    .map((t) => (
                      <tr key={t.tenant_id} className="border-b border-gray-50 last:border-0">
                        <td className="py-2 font-medium text-gray-800">{t.display_name}</td>
                        <td className="py-2 text-right text-gray-600">{formatTokens(t.total_tokens)}</td>
                        <td className="py-2 text-right text-gray-800">{formatUsd(t.cost_usd)}</td>
                        <td className="py-2 text-right text-gray-500">{t.request_count}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              No DeepSeek calls recorded yet. Usage appears after AI Assist, onboarding, or engine
              chat (set <code className="text-xs bg-gray-100 px-1 rounded">SHADOU_ADMIN_DB_DIR</code> on
              the Shadou engine to include WhatsApp/runtime traffic).
            </p>
          )}
        </div>
      )}

      {/* ── Agent grid ── */}
      <div>
        <h2 className="text-base font-semibold text-gray-900 mb-4">Your agents</h2>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner className="text-brand-600" />
          </div>
        ) : !tenants?.length ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {tenants.map((t) => (
              <TenantCard
                key={t.id}
                tenant={t}
                workerRow={worker?.tenants?.find((w) => w.slug === t.slug)}
              />
            ))}
            <Link
              to="/tenants/new"
              className="card flex flex-col items-center justify-center gap-3 p-8 border-dashed border-2 border-gray-200 text-gray-400 hover:border-brand-300 hover:text-brand-600 hover:bg-brand-50/50 transition-all duration-200 cursor-pointer"
            >
              <div className="h-12 w-12 rounded-2xl bg-gray-100 flex items-center justify-center">
                <Plus size={24} />
              </div>
              <span className="text-sm font-medium">Add agent</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
