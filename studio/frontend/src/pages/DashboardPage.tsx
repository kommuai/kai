import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Building2,
  ChevronRight,
  Clock,
  Radio,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";
import Spinner from "../components/Spinner";
import WhatsAppWorkerBanner from "../components/WhatsAppWorkerBanner";
import { tenantsApi, type Tenant, type WhatsAppWorkerTenantOut } from "../lib/api";
import { useAuthStore } from "../lib/auth";

function TenantCard({
  tenant,
  workerRow,
}: {
  tenant: Tenant;
  workerRow?: WhatsAppWorkerTenantOut;
}) {
  const initials = tenant.display_name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const colors = [
    "from-violet-500 to-purple-600",
    "from-blue-500 to-cyan-600",
    "from-emerald-500 to-teal-600",
    "from-orange-500 to-amber-600",
    "from-pink-500 to-rose-600",
  ];
  const colorIdx = tenant.slug.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % colors.length;

  return (
    <Link
      to={`/t/${tenant.slug}`}
      className="card group flex flex-col p-5 hover:shadow-card-lg transition-all duration-200 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between mb-4">
        <div
          className={`h-12 w-12 rounded-2xl bg-gradient-to-br ${colors[colorIdx]} flex items-center justify-center text-white text-lg font-bold shadow-sm`}
        >
          {initials}
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
        {tenant.description && (
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">{tenant.description}</p>
        )}
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
      <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-brand-50">
        <Building2 size={36} className="text-brand-500" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">No tenants yet</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-xs">
        Create your first tenant to start configuring an AI support agent.
      </p>
      <Link to="/tenants/new" className="btn-primary">
        <Plus size={16} />
        Create tenant
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
  });

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const firstName = user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "there";

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting}, {firstName} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your AI support tenants from here.
        </p>
      </div>

      <WhatsAppWorkerBanner />

      {/* ── Stats row ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 sm:max-w-xl gap-4">
        <div className="card p-4 flex items-center gap-4">
          <div className="rounded-xl p-2.5 text-brand-600 bg-brand-50">
            <Building2 size={20} />
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{tenants?.length ?? "—"}</div>
            <div className="text-xs text-gray-500">Tenants</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-4">
          <div
            className={clsx(
              "rounded-xl p-2.5",
              worker?.bridge_reachable && (worker?.live_tenant_count ?? 0) > 0
                ? "text-emerald-600 bg-emerald-50"
                : "text-gray-500 bg-gray-100",
            )}
          >
            <Radio size={20} />
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">
              {worker?.bridge_reachable ? (worker.live_tenant_count ?? 0) : "—"}
            </div>
            <div className="text-xs text-gray-500">WhatsApp live</div>
          </div>
        </div>
      </div>

      {/* ── Tenant grid ── */}
      <div>
        <h2 className="text-base font-semibold text-gray-900 mb-4">Your tenants</h2>

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
              <span className="text-sm font-medium">Add tenant</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
