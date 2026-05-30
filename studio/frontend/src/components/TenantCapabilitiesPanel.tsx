import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Puzzle } from "lucide-react";
import clsx from "clsx";
import { tenantsApi } from "../lib/api";
import Spinner from "./Spinner";
import Toggle from "./Toggle";

interface TenantCapabilitiesPanelProps {
  tenantId: string;
  /** When true, renders inside the configuration editor tab (no outer section chrome). */
  embedded?: boolean;
}

function skillBadge(skill: { source: string; plugin: string | null }): string {
  if (skill.source === "document") return "Document";
  if (skill.plugin) return "Plugin";
  return "Builtin";
}

function skillMeta(skill: {
  source: string;
  path: string | null;
  plugin: string | null;
  builtin: string | null;
  canonical_builtin: string | null;
}): string | undefined {
  if (skill.source === "document" && skill.path) return skill.path;
  if (skill.plugin) return skill.plugin;
  if (skill.builtin && skill.canonical_builtin && skill.builtin !== skill.canonical_builtin) {
    return skill.canonical_builtin;
  }
  return undefined;
}

export default function TenantCapabilitiesPanel({ tenantId, embedded = false }: TenantCapabilitiesPanelProps) {
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
      <div className={clsx("flex justify-center", embedded ? "py-12" : "card p-8")}>
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={clsx("text-sm text-gray-500", embedded ? "px-4 py-8" : "card p-6")}>
        Could not load skills for this workspace.
      </div>
    );
  }

  const empty = (
    <div
      className={clsx(
        "flex items-start gap-3 text-sm text-gray-500",
        embedded ? "px-4 py-8" : "card p-4",
      )}
    >
      <Puzzle size={18} className="text-gray-300 shrink-0 mt-0.5" />
      <p>
        No skills yet. Add entries under{" "}
        <code className="font-mono text-xs bg-gray-100 px-1 rounded">tools_profile</code> in Workspace, or use{" "}
        <code className="font-mono text-xs bg-gray-100 px-1 rounded">skills/&lt;name&gt;/skill.md</code>.
      </p>
    </div>
  );

  const list = (
    <ul className={clsx(embedded ? "divide-y divide-gray-100" : "grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3")}>
      {data.skills.map((skill) => {
        const meta = skillMeta(skill);
        if (embedded) {
          return (
            <li
              key={`${skill.source}:${skill.id}`}
              className={clsx(
                "px-4 py-3 flex items-start gap-3 hover:bg-gray-50/80 transition-colors",
                !skill.enabled && "opacity-60",
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-medium text-gray-900">{skill.id}</span>
                  <span className="badge-purple text-[10px] py-0">{skillBadge(skill)}</span>
                </div>
                {meta && <p className="text-[10px] text-gray-400 font-mono truncate mt-0.5">{meta}</p>}
                <p className="text-xs text-gray-600 leading-relaxed mt-1 line-clamp-2">{skill.description}</p>
              </div>
              <div className="inline-flex items-center gap-2 shrink-0 pt-0.5">
                <span
                  className={clsx(
                    "text-[11px] font-medium tabular-nums",
                    skill.enabled ? "text-brand-700" : "text-gray-400",
                  )}
                >
                  {skill.enabled ? "On" : "Off"}
                </span>
                <Toggle
                  checked={skill.enabled}
                  disabled={toggleMut.isPending}
                  aria-label={`${skill.enabled ? "Disable" : "Enable"} ${skill.id}`}
                  onChange={(enabled) =>
                    toggleMut.mutate({
                      id: skill.id,
                      enabled,
                      source: skill.source,
                      path: skill.path,
                    })
                  }
                />
              </div>
            </li>
          );
        }

        return (
          <li key={`${skill.source}:${skill.id}`}>
            <div
              className={clsx(
                "rounded-xl border border-gray-100 bg-white p-4 shadow-sm flex flex-col gap-2 h-full",
                !skill.enabled && "opacity-60",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 text-sm font-mono truncate">{skill.id}</h3>
                  {meta && <p className="text-[10px] text-gray-400 truncate mt-0.5">{meta}</p>}
                  <span className="badge-purple inline-flex mt-2 text-[10px]">{skillBadge(skill)}</span>
                </div>
                <div className="inline-flex items-center gap-2 shrink-0 pt-0.5">
                  <span
                    className={clsx(
                      "text-[11px] font-medium tabular-nums",
                      skill.enabled ? "text-brand-700" : "text-gray-400",
                    )}
                  >
                    {skill.enabled ? "On" : "Off"}
                  </span>
                  <Toggle
                    checked={skill.enabled}
                    disabled={toggleMut.isPending}
                    aria-label={`${skill.enabled ? "Disable" : "Enable"} ${skill.id}`}
                    onChange={(enabled) =>
                      toggleMut.mutate({
                        id: skill.id,
                        enabled,
                        source: skill.source,
                        path: skill.path,
                      })
                    }
                  />
                </div>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed flex-1">{skill.description}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );

  if (embedded) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto bg-white">
        {data.skills.length === 0 ? empty : list}
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <div className="h-8 w-8 rounded-lg bg-violet-50 flex items-center justify-center">
          <Puzzle size={16} className="text-violet-600" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Skills</h2>
          <p className="text-xs text-gray-500">
            Profile <span className="font-mono text-brand-700">{data.active_profile}</span> in workspace.yaml
          </p>
        </div>
      </div>
      {data.skills.length === 0 ? empty : list}
    </section>
  );
}
