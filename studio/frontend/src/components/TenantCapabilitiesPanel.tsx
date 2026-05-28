import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Puzzle } from "lucide-react";
import clsx from "clsx";
import { tenantsApi } from "../lib/api";
import Spinner from "./Spinner";

interface TenantCapabilitiesPanelProps {
  tenantId: string;
}

function CapabilityCard({
  title,
  subtitle,
  description,
  badge,
  topRight,
  disabled,
}: {
  title: string;
  subtitle?: string;
  description: string;
  badge?: string;
  topRight?: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <div
      className={clsx(
        "rounded-xl border border-gray-100 bg-white p-4 shadow-sm flex flex-col gap-2 h-full",
        disabled && "opacity-60",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-900 text-sm font-mono truncate">{title}</h3>
          {subtitle && <p className="text-[10px] text-gray-400 truncate mt-0.5">{subtitle}</p>}
          {badge && <span className="badge-purple inline-flex mt-2 text-[10px]">{badge}</span>}
        </div>
        {topRight && <div className="shrink-0 pt-0.5">{topRight}</div>}
      </div>
      <p className="text-xs text-gray-600 leading-relaxed flex-1">{description}</p>
    </div>
  );
}

function skillBadge(skill: { source: string; plugin: string | null }): string | undefined {
  if (skill.source === "document") return "Document";
  if (skill.plugin) return "Plugin";
  return "Builtin";
}

function skillSubtitle(skill: {
  source: string;
  path: string | null;
  plugin: string | null;
  builtin: string | null;
  canonical_builtin: string | null;
}): string | undefined {
  if (skill.source === "document" && skill.path) {
    return skill.path;
  }
  if (skill.plugin) {
    return `plugin: ${skill.plugin}`;
  }
  if (skill.builtin && skill.canonical_builtin && skill.builtin !== skill.canonical_builtin) {
    return `builtin: ${skill.canonical_builtin}`;
  }
  return undefined;
}

export default function TenantCapabilitiesPanel({ tenantId }: TenantCapabilitiesPanelProps) {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["tenant-capabilities", tenantId],
    queryFn: () => tenantsApi.capabilities(tenantId),
    enabled: !!tenantId,
  });

  const toggleMut = useMutation({
    mutationFn: (args: { id: string; enabled: boolean; source: "profile" | "document"; path?: string | null }) =>
      tenantsApi.toggleSkill(tenantId, args.id, { enabled: args.enabled, source: args.source, path: args.path ?? null }),
    onSuccess: (next) => {
      qc.setQueryData(["tenant-capabilities", tenantId], next);
    },
  });

  if (isLoading) {
    return (
      <div className="card p-8 flex justify-center">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card p-6 text-sm text-gray-500">
        Could not load skills for this workspace.
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <div className="h-8 w-8 rounded-lg bg-violet-50 flex items-center justify-center">
          <Sparkles size={16} className="text-violet-600" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Skills</h2>
          <p className="text-xs text-gray-500">
            Profile{" "}
            <span className="font-mono text-brand-700">{data.active_profile}</span> in workspace.yaml,
            plus optional <span className="font-mono">skills/</span> docs
          </p>
        </div>
      </div>
      {data.skills.length === 0 ? (
        <div className="card p-4 flex items-start gap-3 text-sm text-gray-500">
          <Puzzle size={18} className="text-gray-300 shrink-0 mt-0.5" />
          <p>
            No skills configured. Enable entries under{" "}
            <code className="font-mono text-xs bg-gray-100 px-1 rounded">tools_profile</code> in
            workspace.yaml, or add{" "}
            <code className="font-mono text-xs bg-gray-100 px-1 rounded">skills/&lt;name&gt;/skill.md</code>.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {data.skills.map((skill) => (
            <div key={`${skill.source}:${skill.id}`}>
              <CapabilityCard
                title={skill.id}
                subtitle={skillSubtitle(skill)}
                description={skill.description}
                badge={skillBadge(skill)}
                disabled={!skill.enabled}
                topRight={
                  <label className="inline-flex items-center gap-2 text-[11px] text-gray-500 select-none">
                    <span className={clsx(!skill.enabled && "text-gray-400")}>
                      {skill.enabled ? "Enabled" : "Disabled"}
                    </span>
                    <input
                      type="checkbox"
                      className="rounded border-gray-300"
                      checked={skill.enabled}
                      disabled={toggleMut.isPending}
                      onChange={(e) =>
                        toggleMut.mutate({
                          id: skill.id,
                          enabled: e.target.checked,
                          source: skill.source,
                          path: skill.path,
                        })
                      }
                    />
                  </label>
                }
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
