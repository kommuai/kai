import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Snowflake,
  Plus,
  X,
  Send,
  Loader2,
  ChevronDown,
  Tags,
  MessageSquare,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { formatDistanceToNow } from "date-fns";
import { contactsApi, inboxApi, tenantsApi, type Tenant } from "../lib/api";
import Spinner from "../components/Spinner";

type MobileDrawer = null | "tags" | "chatwoot";

export default function ConversationPage() {
  const { slug, userId: userIdParam } = useParams<{ slug: string; userId: string }>();
  const userId = userIdParam ? decodeURIComponent(userIdParam) : "";
  const ctx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const qc = useQueryClient();
  const [tagInput, setTagInput] = useState("");
  const [replyText, setReplyText] = useState("");
  const [cwOpen, setCwOpen] = useState(false);
  const [tagsExpanded, setTagsExpanded] = useState(false);
  const [mobileDrawer, setMobileDrawer] = useState<MobileDrawer>(null);

  const { data: tenantQ } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !ctx?.tenant,
  });
  const tenant = ctx?.tenant ?? tenantQ;
  const tenantId = tenant?.id;
  const base = `/t/${slug}`;

  const { data: detail, isLoading, error } = useQuery({
    queryKey: ["conversation", tenantId, userId],
    queryFn: () => inboxApi.conversation(tenantId!, userId),
    enabled: !!tenantId && !!userId,
  });

  const invalidateTags = () => {
    qc.invalidateQueries({ queryKey: ["conversation", tenantId, userId] });
    qc.invalidateQueries({ queryKey: ["contacts", tenantId] });
    qc.invalidateQueries({ queryKey: ["inbox-conversations", tenantId] });
    qc.invalidateQueries({ queryKey: ["cwMeta", tenantId, userId] });
  };

  const { data: cwMeta } = useQuery({
    queryKey: ["cwMeta", tenantId, userId],
    queryFn: () => inboxApi.chatwootMeta(tenantId!, userId),
    enabled: !!tenantId && !!userId,
  });

  const { data: cwAccountLabels } = useQuery({
    queryKey: ["cwAccountLabels", tenantId],
    queryFn: () => inboxApi.chatwootAccountLabels(tenantId!),
    enabled: !!tenantId && !!cwMeta?.configured,
  });

  const [privateNoteText, setPrivateNoteText] = useState("");
  const [snoozeUntilLocal, setSnoozeUntilLocal] = useState("");
  const [labelSelection, setLabelSelection] = useState<string[]>([]);

  const showChatwootPanel = Boolean(cwMeta?.configured && cwMeta?.conversation_id);

  useEffect(() => {
    if (cwMeta?.labels) setLabelSelection([...cwMeta.labels]);
  }, [cwMeta?.labels?.join("|")]);

  useEffect(() => {
    if (showChatwootPanel) setCwOpen(true);
  }, [showChatwootPanel]);

  const statusMut = useMutation({
    mutationFn: (body: { status: string; snoozed_until?: number | null }) =>
      inboxApi.chatwootSetStatus(tenantId!, userId, body),
    onSuccess: (_, vars) => {
      toast.success(`Status → ${vars.status}`);
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Status update failed"),
  });

  const privateNoteMut = useMutation({
    mutationFn: () => inboxApi.chatwootPrivateNote(tenantId!, userId, privateNoteText.trim()),
    onSuccess: () => {
      toast.success("Private note added");
      setPrivateNoteText("");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to add note"),
  });

  const labelsMut = useMutation({
    mutationFn: () => inboxApi.chatwootSetLabels(tenantId!, userId, labelSelection),
    onSuccess: () => {
      toast.success("Labels updated");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Labels update failed"),
  });

  const handoverMut = useMutation({
    mutationFn: () => inboxApi.chatwootHandover(tenantId!, userId),
    onSuccess: () => {
      toast.success("Handed over to human (Kai frozen)");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Handover failed"),
  });

  const resumeBotMut = useMutation({
    mutationFn: () => inboxApi.chatwootResumeBot(tenantId!, userId),
    onSuccess: () => {
      toast.success("AI support agent resumed");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Resume failed"),
  });

  function cwLabelTitle(o: Record<string, unknown>) {
    return String(o.title ?? o.name ?? o.id ?? "").trim();
  }

  function toggleCwLabel(title: string) {
    setLabelSelection((prev) =>
      prev.includes(title) ? prev.filter((x) => x !== title) : [...prev, title],
    );
  }

  function snoozeUnix(): number | null {
    if (!snoozeUntilLocal) return null;
    const ms = new Date(snoozeUntilLocal).getTime();
    if (Number.isNaN(ms)) return null;
    return Math.floor(ms / 1000);
  }

  const addTagMut = useMutation({
    mutationFn: () => contactsApi.addTag(tenantId!, userId, tagInput.trim()),
    onSuccess: () => {
      toast.success("Tag added");
      setTagInput("");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to add tag"),
  });

  const removeTagMut = useMutation({
    mutationFn: (tag: string) => contactsApi.removeTag(tenantId!, userId, tag),
    onSuccess: () => {
      toast.success("Tag removed");
      invalidateTags();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to remove tag"),
  });

  const replyMut = useMutation({
    mutationFn: () => inboxApi.reply(tenantId!, userId, replyText.trim()),
    onSuccess: (res) => {
      setReplyText("");
      invalidateTags();
      if (res.chatwoot_delivered) {
        toast.success("Sent via Chatwoot");
      } else if (res.chatwoot_conversation_id && res.chatwoot_error) {
        toast.success("Reply saved (Chatwoot delivery failed)");
      } else {
        toast.success("Reply saved");
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to send reply"),
  });

  function handleSendReply() {
    const text = replyText.trim();
    if (!text || replyMut.isPending) return;
    replyMut.mutate();
  }

  function closeMobileDrawer() {
    setMobileDrawer(null);
  }

  function toggleTagsDesktop() {
    setTagsExpanded((v) => !v);
  }

  if (!tenant) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="m-4 rounded-2xl border border-red-100 bg-red-50 p-6 text-sm text-red-800">
        Could not load conversation.
      </div>
    );
  }

  const isUser = (role: string) => role === "user" || role === "human";

  function bubbleStyle(role: string) {
    if (isUser(role)) return "bg-brand-600 text-white rounded-bl-md";
    if (role === "agent") return "bg-emerald-600 text-white rounded-br-md";
    return "bg-white border border-gray-100 text-gray-800 rounded-br-md";
  }

  const tagCount = detail.tags.length;

  const tagsBody = (
    <>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {detail.tags.length === 0 ? (
          <span className="text-xs text-gray-400">No tags yet.</span>
        ) : (
          detail.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700"
            >
              {tag}
              <button
                type="button"
                className="p-0.5 rounded hover:bg-gray-200"
                onClick={() => removeTagMut.mutate(tag)}
                aria-label={`Remove ${tag}`}
              >
                <X size={11} />
              </button>
            </span>
          ))
        )}
      </div>
      <div className="flex gap-2">
        <input
          className="input flex-1 text-sm py-1.5"
          placeholder="New tag…"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") addTagMut.mutate();
          }}
        />
        <button
          type="button"
          className="btn-primary btn-sm shrink-0"
          disabled={!tagInput.trim() || addTagMut.isPending}
          onClick={() => addTagMut.mutate()}
        >
          <Plus size={13} />
        </button>
      </div>
    </>
  );

  const chatwootBody =
    !cwMeta ? (
      <div className="flex justify-center py-6">
        <Loader2 size={18} className="animate-spin text-violet-500" />
      </div>
    ) : !cwMeta.conversation_id ? (
      <p className="text-xs text-gray-600">
        No linked Chatwoot conversation yet. It is set automatically when messages arrive via the Agent AI support agent webhook.
      </p>
    ) : (
      <>
        <div>
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Status</div>
          <div className="flex items-center gap-2 mb-2">
            <span className="badge-purple capitalize">{cwMeta.status || "—"}</span>
            <span className="text-[10px] text-gray-400 font-mono">#{cwMeta.conversation_id}</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {(["open", "pending", "resolved", "snoozed"] as const).map((st) => (
              <button
                key={st}
                type="button"
                className={clsx(
                  "btn-secondary btn-sm py-1 px-2 capitalize text-[11px]",
                  cwMeta.status === st && "ring-1 ring-brand-400",
                )}
                disabled={statusMut.isPending}
                onClick={() => {
                  if (st === "snoozed") {
                    const u = snoozeUnix();
                    if (!u) {
                      toast.error("Pick a snooze date/time first");
                      return;
                    }
                    statusMut.mutate({ status: "snoozed", snoozed_until: u });
                    return;
                  }
                  statusMut.mutate({ status: st });
                }}
              >
                {st}
              </button>
            ))}
          </div>
          <div className="mt-2">
            <label className="text-[10px] text-gray-500 mb-1 block">Snooze until</label>
            <input
              type="datetime-local"
              className="input text-xs py-1.5"
              value={snoozeUntilLocal}
              onChange={(e) => setSnoozeUntilLocal(e.target.value)}
            />
          </div>
        </div>

        <div className="border-t border-violet-100 pt-3">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Agent</div>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              className="btn-secondary btn-sm py-1 px-2 text-[11px]"
              disabled={handoverMut.isPending}
              onClick={() => handoverMut.mutate()}
            >
              Human handover
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm py-1 px-2 text-[11px]"
              disabled={resumeBotMut.isPending}
              onClick={() => resumeBotMut.mutate()}
            >
              Resume AI support agent
            </button>
          </div>
        </div>

        <div className="border-t border-violet-100 pt-3">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Private note</div>
          <textarea
            className="input w-full text-xs py-1.5 min-h-[52px]"
            placeholder="Internal note…"
            value={privateNoteText}
            onChange={(e) => setPrivateNoteText(e.target.value)}
          />
          <button
            type="button"
            className="btn-primary btn-sm mt-1.5"
            disabled={!privateNoteText.trim() || privateNoteMut.isPending}
            onClick={() => privateNoteMut.mutate()}
          >
            Add note
          </button>
        </div>

        <div className="border-t border-violet-100 pt-3">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Labels</div>
          <p className="text-[10px] text-amber-700 bg-amber-50 rounded-lg px-2 py-1 mb-2">
            Saving replaces all labels on this conversation.
          </p>
          <div className="flex flex-wrap gap-2 max-h-28 overflow-y-auto">
            {(cwAccountLabels?.items ?? [])
              .map((raw) => cwLabelTitle(raw as Record<string, unknown>))
              .filter(Boolean)
              .map((title) => (
                <label key={title} className="inline-flex items-center gap-1.5 cursor-pointer text-xs">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={labelSelection.includes(title)}
                    onChange={() => toggleCwLabel(title)}
                  />
                  {title}
                </label>
              ))}
          </div>
          <button
            type="button"
            className="btn-primary btn-sm mt-2"
            disabled={labelsMut.isPending}
            onClick={() => labelsMut.mutate()}
          >
            Save labels
          </button>
        </div>
      </>
    );

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden bg-white lg:bg-transparent">
      {/* Top bar — mobile: compact toolbar */}
      <div className="shrink-0 border-b border-gray-100 bg-white">
        <div className="flex items-center gap-2 px-3 py-2 sm:px-4">
          <Link
            to={`${base}/inbox`}
            className="lg:hidden inline-flex items-center justify-center rounded-xl p-2 text-gray-600 hover:bg-gray-100"
            aria-label="Back to inbox"
          >
            <ArrowLeft size={18} />
          </Link>

          <div className="flex-1 min-w-0">
            <div className="font-mono text-xs sm:text-sm font-semibold text-gray-900 truncate">{detail.user_id}</div>
            <p className="text-[10px] sm:text-xs text-gray-400 truncate">
              {detail.last_activity_at
                ? `${formatDistanceToNow(new Date(detail.last_activity_at), { addSuffix: true })} · ${detail.messages.length} msgs`
                : `No activity · ${detail.messages.length} msgs`}
            </p>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => {
                if (typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches) {
                  toggleTagsDesktop();
                } else {
                  setMobileDrawer((d) => (d === "tags" ? null : "tags"));
                }
              }}
              className={clsx(
                "relative inline-flex items-center justify-center rounded-xl p-2.5 border transition-colors",
                mobileDrawer === "tags" || tagsExpanded
                  ? "border-brand-200 bg-brand-50 text-brand-700"
                  : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50",
              )}
              aria-expanded={mobileDrawer === "tags" || tagsExpanded}
              aria-label="Tags"
              title="Tags"
            >
              <Tags size={18} />
              {tagCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-0.5 rounded-full bg-brand-600 text-[9px] font-bold text-white flex items-center justify-center">
                  {tagCount > 9 ? "9+" : tagCount}
                </span>
              )}
            </button>

            {cwMeta?.configured && (
              <button
                type="button"
                onClick={() => {
                  if (typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches) {
                    setCwOpen((v) => !v);
                  } else {
                    setMobileDrawer((d) => (d === "chatwoot" ? null : "chatwoot"));
                  }
                }}
                className={clsx(
                  "lg:hidden inline-flex items-center justify-center rounded-xl p-2.5 border transition-colors",
                  mobileDrawer === "chatwoot"
                    ? "border-violet-200 bg-violet-50 text-violet-800"
                    : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50",
                )}
                aria-label="Chatwoot"
                title="Chatwoot"
              >
                <MessageSquare size={18} className="text-violet-600" />
              </button>
            )}
          </div>
        </div>
      </div>

      {detail.frozen && (
        <div className="flex items-center gap-2 px-3 py-1.5 text-[11px] text-amber-900 bg-amber-50 border-b border-amber-100 shrink-0">
          <Snowflake size={13} />
          <span>Human handover — AI support agent paused</span>
        </div>
      )}

      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
        {/* Chat */}
        <div className="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden lg:border-r lg:border-gray-100">
          <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-2 bg-surface-muted/50">
            {detail.messages.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-12">No messages in session history.</p>
            ) : (
              detail.messages.map((m, idx) => (
                <div key={idx} className={clsx("flex", isUser(m.role) ? "justify-start" : "justify-end")}>
                  <div
                    className={clsx(
                      "max-w-[min(100%,20rem)] sm:max-w-[min(100%,24rem)] rounded-2xl px-3 py-2 text-[13px] leading-snug shadow-sm",
                      bubbleStyle(m.role),
                    )}
                  >
                    <div className="text-[9px] uppercase tracking-wide opacity-60 mb-0.5">
                      {m.role === "assistant" ? "ai support agent" : m.role}
                    </div>
                    <div className="whitespace-pre-wrap break-words">{m.text}</div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="shrink-0 border-t border-gray-100 p-3 bg-white pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <div className="flex gap-2 items-end">
              <textarea
                className="input flex-1 min-h-[44px] max-h-32 text-sm py-2 resize-y"
                placeholder="Reply as agent…"
                rows={2}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendReply();
                  }
                }}
              />
              <button
                type="button"
                className="btn-primary btn-sm shrink-0 h-10 px-3"
                disabled={!replyText.trim() || replyMut.isPending}
                onClick={handleSendReply}
              >
                {replyMut.isPending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              </button>
            </div>
            <p className="text-[10px] text-gray-400 mt-1 hidden sm:block">Enter to send · Shift+Enter for new line</p>
          </div>
        </div>

        {/* Desktop: tags + Chatwoot column */}
        <aside className="hidden lg:flex lg:w-72 xl:w-80 shrink-0 flex-col border-l border-gray-100 bg-surface-muted/40 min-h-0">
          <div className="shrink-0 border-b border-gray-100 p-3 flex items-center justify-between gap-2 bg-white/80">
            <span className="text-xs font-semibold text-gray-600">Tags</span>
            <button
              type="button"
              onClick={toggleTagsDesktop}
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium border",
                tagsExpanded ? "border-brand-200 bg-brand-50 text-brand-800" : "border-gray-200 text-gray-600 hover:bg-gray-50",
              )}
            >
              <Tags size={14} />
              {tagCount > 0 ? `${tagCount}` : "Edit"}
            </button>
          </div>
          {tagsExpanded && <div className="p-3 overflow-y-auto border-b border-gray-100 bg-white">{tagsBody}</div>}

          {showChatwootPanel && (
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden m-2 rounded-xl border border-violet-100 bg-white shadow-sm">
              <button
                type="button"
                className="shrink-0 flex items-center justify-between px-3 py-2.5 text-left hover:bg-violet-50/50"
                onClick={() => setCwOpen((v) => !v)}
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-violet-700 bg-violet-100 px-1 rounded">CW</span>
                  <span className="text-xs font-semibold text-gray-800">Chatwoot</span>
                </div>
                <ChevronDown size={14} className={clsx("text-gray-400 transition-transform", cwOpen && "rotate-180")} />
              </button>
              {cwOpen && (
                <div className="flex-1 overflow-y-auto px-3 pb-3 pt-0 space-y-3 text-xs border-t border-violet-50">
                  {chatwootBody}
                </div>
              )}
            </div>
          )}
        </aside>
      </div>

      {/* Mobile bottom sheet: tags or Chatwoot */}
      {mobileDrawer && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close"
            onClick={closeMobileDrawer}
          />
          <div className="relative bg-white rounded-t-2xl shadow-2xl border-t border-gray-100 max-h-[min(78vh,560px)] flex flex-col animate-slide-up">
            <div className="flex justify-center pt-2 pb-1">
              <div className="h-1 w-10 rounded-full bg-gray-200" />
            </div>
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
              <span className="text-sm font-semibold text-gray-900">
                {mobileDrawer === "tags" ? "Contact tags" : "Chatwoot"}
              </span>
              <button
                type="button"
                className="btn-ghost btn-sm text-gray-500"
                onClick={closeMobileDrawer}
              >
                Done
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
              {mobileDrawer === "tags" ? (
                tagsBody
              ) : cwMeta?.configured ? (
                chatwootBody
              ) : (
                <p className="text-sm text-gray-500">Chatwoot is not enabled for this tenant.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
