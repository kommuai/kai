import { useState, useEffect, useCallback } from "react";
import { useParams, useOutletContext } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";
import {
  Save,
  Play,
  CheckCircle2,
  XCircle,
  FileCode2,
  FileText,
  BookOpen,
  Puzzle,
  TerminalSquare,
  Clock,
  Loader2,
  Users,
  Copy,
  Plus,
  Trash2,
  Sparkles,
  Code2,
} from "lucide-react";
import clsx from "clsx";
import { formatDistanceToNow } from "date-fns";
import { tenantsApi, type CompileResult, type InviteOut, type Tenant } from "../lib/api";
import Spinner from "../components/Spinner";
import DeleteTenantPanel from "../components/DeleteTenantPanel";
import TenantCapabilitiesPanel from "../components/TenantCapabilitiesPanel";
import TenantChannelPanel from "../components/TenantChannelPanel";
import AiAssistPanel from "../components/AiAssistPanel";
import { useAuthStore } from "../lib/auth";

type FileKey = "workspace" | "system_prompt" | "faq";
type ConfigTabKey = FileKey | "skills";

function isFileTab(tab: ConfigTabKey): tab is FileKey {
  return tab !== "skills";
}

interface Tab {
  key: ConfigTabKey;
  label: string;
  icon: React.ReactNode;
  language?: string;
  description: string;
}

const TABS: Tab[] = [
  {
    key: "workspace",
    label: "Workspace",
    icon: <FileCode2 size={16} />,
    language: "yaml",
    description: "Core configuration: tenant ID, channels, tools profile, and admin settings.",
  },
  {
    key: "skills",
    label: "Skills",
    icon: <Puzzle size={16} />,
    description: "Turn agent actions and plugins on or off. Changes apply to workspace.yaml immediately.",
  },
  {
    key: "system_prompt",
    label: "System Prompt",
    icon: <FileText size={16} />,
    language: "markdown",
    description: "Instructions that shape your AI support agent's personality, rules, and response format.",
  },
  {
    key: "faq",
    label: "FAQ / Knowledge",
    icon: <BookOpen size={16} />,
    language: "markdown",
    description: "The authoritative knowledge base. Add intents, aliases, and answers here.",
  },
];

function CompilePanel({ tenantId }: { tenantId: string }) {
  const [result, setResult] = useState<CompileResult | null>(null);
  const { mutate, isPending } = useMutation({
    mutationFn: () => tenantsApi.compile(tenantId),
    onSuccess: (r) => {
      setResult(r);
      if (r.ok) toast.success("Compiled successfully!");
      else toast.error("Compile failed");
    },
    onError: () => toast.error("Compile request failed"),
  });

  return (
    <div className="border-t border-gray-100 bg-gray-50/80">
      <div className="px-4 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <TerminalSquare size={14} />
          <span>Knowledge compiler</span>
        </div>
        <button
          onClick={() => mutate()}
          disabled={isPending}
          className="btn-secondary btn-sm flex items-center gap-1.5"
        >
          {isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          Compile
        </button>
      </div>

      {result && (
        <div
          className={clsx(
            "mx-4 mb-3 rounded-xl p-3 text-xs font-mono leading-relaxed animate-fade-in",
            result.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800",
          )}
        >
          <div className="flex items-center gap-2 mb-1 font-semibold text-sm font-sans">
            {result.ok ? (
              <CheckCircle2 size={15} className="text-emerald-600" />
            ) : (
              <XCircle size={15} className="text-red-600" />
            )}
            {result.ok ? `Compiled${result.intents != null ? ` — ${result.intents} intents` : ""}` : "Compile failed"}
          </div>
          <pre className="whitespace-pre-wrap break-all">{result.message}</pre>
        </div>
      )}
    </div>
  );
}

export default function TenantEditorPage() {
  const { slug } = useParams<{ slug: string }>();
  const outletCtx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const qc = useQueryClient();

  const [editorMode, setEditorMode] = useState<"edit" | "ai">("edit");
  const [activeTab, setActiveTab] = useState<ConfigTabKey>("workspace");
  const [content, setContent] = useState<Record<FileKey, string>>({
    workspace: "",
    system_prompt: "",
    faq: "",
  });
  const [dirty, setDirty] = useState<Record<FileKey, boolean>>({
    workspace: false,
    system_prompt: false,
    faq: false,
  });

  const { data: tenantFetched, isLoading: tenantLoading } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !outletCtx?.tenant,
  });

  const tenant = outletCtx?.tenant ?? tenantFetched;
  const currentUserId = useAuthStore((s) => s.user?.id);
  const isOwner = tenant && currentUserId && tenant.owner_id === currentUserId;

  // Load all files in parallel
  const tenantId = tenant?.id;
  const { data: wsFile } = useQuery({ queryKey: ["file", tenantId, "workspace"], queryFn: () => tenantsApi.getFile(tenantId!, "workspace"), enabled: !!tenantId });
  const { data: spFile } = useQuery({ queryKey: ["file", tenantId, "system_prompt"], queryFn: () => tenantsApi.getFile(tenantId!, "system_prompt"), enabled: !!tenantId });
  const { data: faqFile } = useQuery({ queryKey: ["file", tenantId, "faq"], queryFn: () => tenantsApi.getFile(tenantId!, "faq"), enabled: !!tenantId });

  useEffect(() => {
    if (wsFile) setContent((p) => ({ ...p, workspace: wsFile.content }));
  }, [wsFile]);
  useEffect(() => {
    if (spFile) setContent((p) => ({ ...p, system_prompt: spFile.content }));
  }, [spFile]);
  useEffect(() => {
    if (faqFile) setContent((p) => ({ ...p, faq: faqFile.content }));
  }, [faqFile]);

  const saveMutation = useMutation({
    mutationFn: ({ key, text }: { key: FileKey; text: string }) =>
      tenantsApi.putFile(tenantId!, key, text),
    onSuccess: (_, { key }) => {
      setDirty((p) => ({ ...p, [key]: false }));
      qc.invalidateQueries({ queryKey: ["file", tenantId, key] });
      toast.success("Saved!");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Save failed");
    },
  });

  // ── Invites ────────────────────────────────────────────────────────────────
  const [inviteEmail, setInviteEmail] = useState("");

  const { data: invites, isLoading: invitesLoading } = useQuery({
    queryKey: ["invites", tenantId],
    queryFn: () => tenantsApi.listInvites(tenantId!),
    enabled: !!tenantId,
  });

  const createInviteMutation = useMutation({
    mutationFn: () => tenantsApi.createInvite(tenantId!, inviteEmail),
    onSuccess: (inv) => {
      toast.success("Invite created");
      setInviteEmail("");
      qc.invalidateQueries({ queryKey: ["invites", tenantId] });
      if (inv.invite_url) navigator.clipboard?.writeText(inv.invite_url).catch(() => {});
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to create invite"),
  });

  const revokeInviteMutation = useMutation({
    mutationFn: ({ inviteId }: { inviteId: string }) => tenantsApi.revokeInvite(tenantId!, inviteId),
    onSuccess: () => {
      toast.success("Invite revoked");
      qc.invalidateQueries({ queryKey: ["invites", tenantId] });
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to revoke invite"),
  });

  function handleSave() {
    if (!isFileTab(activeTab)) return;
    saveMutation.mutate({ key: activeTab, text: content[activeTab] });
  }

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    },
    [activeTab, content],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (tenantLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (!tenant) return <div className="text-center py-20 text-gray-400">Tenant not found.</div>;

  const activeTabDef = TABS.find((t) => t.key === activeTab)!;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-semibold text-gray-900">Configuration</h1>
          <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
            <Clock size={11} />
            Updated {formatDistanceToNow(new Date(tenant.updated_at), { addSuffix: true })}
          </p>
        </div>
        {editorMode === "edit" && isFileTab(activeTab) && (
          <button
            onClick={handleSave}
            disabled={!dirty[activeTab] || saveMutation.isPending}
            className={clsx("btn-primary btn-sm", !dirty[activeTab] && "opacity-50")}
          >
            {saveMutation.isPending ? (
              <Spinner size="sm" className="text-white" />
            ) : (
              <Save size={14} />
            )}
            Save
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-brand-400/40 px-1.5 py-0.5 text-[10px] font-mono text-brand-200 ml-1">
              ⌘S
            </kbd>
          </button>
        )}
      </div>

      {tenantId && <TenantChannelPanel tenantId={tenantId} />}

      {/* ── Editor card ── */}
      <div className="card overflow-hidden flex flex-col" style={{ height: "calc(100dvh - 180px)", minHeight: 480 }}>

        {/* ── Mode toggle bar ── */}
        <div className="flex items-center justify-between px-3 pt-2 pb-0 border-b border-gray-100 bg-gray-50/60">
          <div className="flex gap-1 overflow-x-auto scrollbar-hide">
            {editorMode === "edit" && TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={clsx(
                  "flex items-center gap-2 px-3 py-2 rounded-t-lg text-sm font-medium whitespace-nowrap transition-all duration-150 border border-b-0",
                  activeTab === tab.key
                    ? "bg-white text-gray-900 border-gray-200 -mb-px z-10"
                    : "text-gray-500 border-transparent hover:text-gray-700 hover:bg-white/60",
                )}
              >
                {tab.icon}
                {tab.label}
                {isFileTab(tab.key) && dirty[tab.key] && (
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                )}
              </button>
            ))}
            {editorMode === "ai" && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-purple-700">
                <Sparkles size={15} />
                AI Config Assistant
              </div>
            )}
          </div>

          {/* Mode switcher pill */}
          <div className="flex-shrink-0 ml-3 mb-1 flex items-center gap-0.5 bg-gray-100 rounded-xl p-0.5">
            <button
              onClick={() => setEditorMode("edit")}
              className={clsx(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all",
                editorMode === "edit"
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
            >
              <Code2 size={12} />
              Edit
            </button>
            <button
              onClick={() => setEditorMode("ai")}
              className={clsx(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all",
                editorMode === "ai"
                  ? "bg-purple-600 text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
            >
              <Sparkles size={12} />
              AI Assist
            </button>
          </div>
        </div>

        {editorMode === "edit" ? (
          <>
            {/* Description bar */}
            <div className="px-4 py-2 bg-white border-b border-gray-100 text-xs text-gray-500 flex items-center gap-2">
              {activeTabDef.icon}
              {activeTabDef.description}
            </div>

            {/* Editor or skills list */}
            <div className="flex-1 overflow-hidden">
              {activeTab === "skills" && tenantId ? (
                <TenantCapabilitiesPanel tenantId={tenantId} embedded />
              ) : isFileTab(activeTab) ? (
                <Editor
                  language={activeTabDef.language ?? "plaintext"}
                  value={content[activeTab]}
                  onChange={(v) => {
                    setContent((p) => ({ ...p, [activeTab]: v || "" }));
                    setDirty((p) => ({ ...p, [activeTab]: true }));
                  }}
                  theme="vs"
                  options={{
                    fontSize: 13,
                    lineHeight: 22,
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    fontLigatures: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                    renderLineHighlight: "gutter",
                    smoothScrolling: true,
                    padding: { top: 16, bottom: 16 },
                    overviewRulerLanes: 0,
                    folding: true,
                    lineNumbers: "on",
                    tabSize: 2,
                  }}
                />
              ) : null}
            </div>

            {/* Compile panel — FAQ only */}
            {tenantId && activeTab === "faq" && <CompilePanel tenantId={tenantId} />}
          </>
        ) : (
          <div className="flex-1 overflow-hidden bg-gray-50/30">
            {tenantId && <AiAssistPanel tenantId={tenantId} />}
          </div>
        )}
      </div>

      {/* ── Members / Invites ── */}
      <div className="card p-5">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-2xl bg-brand-50 flex items-center justify-center">
              <Users size={18} className="text-brand-600" />
            </div>
            <div>
              <div className="font-semibold text-gray-900">Members</div>
              <div className="text-xs text-gray-500">Everyone invited has equal edit rights.</div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            className="input flex-1"
            placeholder="Invite by email (e.g. teammate@company.com)"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
          <button
            className="btn-primary"
            disabled={!inviteEmail || createInviteMutation.isPending || !tenantId}
            onClick={() => createInviteMutation.mutate()}
          >
            {createInviteMutation.isPending ? <Spinner size="sm" className="text-white" /> : <Plus size={16} />}
            Invite
          </button>
        </div>

        <div className="divider" />

        {invitesLoading ? (
          <div className="py-8 flex justify-center">
            <Spinner className="text-brand-600" />
          </div>
        ) : !invites?.length ? (
          <div className="text-sm text-gray-500 py-6">No invites yet.</div>
        ) : (
          <div className="space-y-2">
            {invites.map((inv) => (
              <InviteRow
                key={inv.id}
                invite={inv}
                onCopy={() => {
                  if (!inv.invite_url) return;
                  navigator.clipboard?.writeText(inv.invite_url).then(
                    () => toast.success("Copied invite link"),
                    () => toast.error("Failed to copy"),
                  );
                }}
                onRevoke={() => revokeInviteMutation.mutate({ inviteId: inv.id })}
                revokeDisabled={revokeInviteMutation.isPending || inv.status !== "pending"}
              />
            ))}
          </div>
        )}
      </div>

      {isOwner && tenant && <DeleteTenantPanel tenant={tenant} />}
    </div>
  );
}

function InviteRow({
  invite,
  onCopy,
  onRevoke,
  revokeDisabled,
}: {
  invite: InviteOut;
  onCopy: () => void;
  onRevoke: () => void;
  revokeDisabled: boolean;
}) {
  const badge =
    invite.status === "pending"
      ? "badge-orange"
      : invite.status === "accepted"
        ? "badge-green"
        : "badge-gray";

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-white px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <div className="font-semibold text-gray-900 truncate">{invite.email}</div>
          <span className={badge}>{invite.status}</span>
        </div>
        <div className="text-xs text-gray-400 font-mono truncate">
          {invite.invite_url || invite.token}
        </div>
      </div>

      <div className="flex items-center gap-2 justify-end">
        <button className="btn-secondary btn-sm" onClick={onCopy} disabled={!invite.invite_url}>
          <Copy size={14} />
          Copy link
        </button>
        <button className="btn-danger btn-sm" onClick={onRevoke} disabled={revokeDisabled}>
          <Trash2 size={14} />
          Revoke
        </button>
      </div>
    </div>
  );
}
