import { useEffect, useRef, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Snowflake, Plus, X, Send, Loader2, Tags, Bot, UserRound } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { formatDistanceToNow } from "date-fns";
import { contactsApi, inboxApi, tenantsApi, type Tenant } from "../lib/api";
import { CorrespondentHeading } from "../lib/contactDisplay";
import { INBOX_LIST_POLL_MS, INBOX_THREAD_POLL_MS } from "../lib/inboxPolling";
import Spinner from "../components/Spinner";

export default function ConversationPage() {
  const { slug, userId: userIdParam } = useParams<{ slug: string; userId: string }>();
  const userId = userIdParam ? decodeURIComponent(userIdParam) : "";
  const ctx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const qc = useQueryClient();
  const [tagInput, setTagInput] = useState("");
  const [replyText, setReplyText] = useState("");
  const [tagsExpanded, setTagsExpanded] = useState(false);
  const [mobileTagsOpen, setMobileTagsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  const { data: tenantQ } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !ctx?.tenant,
  });
  const tenant = ctx?.tenant ?? tenantQ;
  const tenantId = tenant?.id;
  const base = `/t/${slug}`;

  const { data: detail, isLoading, error, isFetching: detailFetching } = useQuery({
    queryKey: ["conversation", tenantId, userId],
    queryFn: () => inboxApi.conversation(tenantId!, userId),
    enabled: !!tenantId && !!userId,
    staleTime: 1_000,
    refetchInterval: INBOX_THREAD_POLL_MS,
    refetchOnWindowFocus: true,
  });

  useQuery({
    queryKey: ["inbox-conversations", tenantId, "all"],
    queryFn: () => inboxApi.conversations(tenantId!, { status: "all", limit: 80 }),
    enabled: !!tenantId,
    staleTime: 2_000,
    refetchInterval: INBOX_LIST_POLL_MS,
    refetchOnWindowFocus: true,
  });

  const invalidateConversation = () => {
    qc.invalidateQueries({ queryKey: ["conversation", tenantId, userId] });
    qc.invalidateQueries({ queryKey: ["contacts", tenantId] });
    qc.invalidateQueries({ queryKey: ["inbox-conversations", tenantId] });
  };

  const addTagMut = useMutation({
    mutationFn: () => contactsApi.addTag(tenantId!, userId, tagInput.trim()),
    onSuccess: () => {
      toast.success("Tag added");
      setTagInput("");
      invalidateConversation();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to add tag"),
  });

  const removeTagMut = useMutation({
    mutationFn: (tag: string) => contactsApi.removeTag(tenantId!, userId, tag),
    onSuccess: () => {
      toast.success("Tag removed");
      invalidateConversation();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to remove tag"),
  });

  const replyMut = useMutation({
    mutationFn: () => inboxApi.reply(tenantId!, userId, replyText.trim()),
    onSuccess: (data) => {
      setReplyText("");
      invalidateConversation();
      if (data.channel_delivered === false) {
        toast(
          data.channel_detail || "Saved in Studio but not delivered on WhatsApp",
          { icon: "⚠️" },
        );
      } else if (data.channel_detail) {
        toast.success(data.channel_detail);
      } else {
        toast.success("Reply sent");
      }
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || "Failed to send reply"),
  });

  const resumeBotMut = useMutation({
    mutationFn: () => inboxApi.resumeBot(tenantId!, userId),
    onSuccess: (data) => {
      invalidateConversation();
      if (data.already_active) {
        toast.success("AI support agent is already active");
      } else {
        toast.success("AI support agent resumed");
      }
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e.response?.data?.detail || "Failed to resume AI support");
    },
  });

  const handoverBotMut = useMutation({
    mutationFn: () => inboxApi.handoverBot(tenantId!, userId),
    onSuccess: (data) => {
      invalidateConversation();
      if (data.already_in_handover) {
        toast.success("Already in human handover");
        return;
      }
      if (data.channel_delivered === false) {
        toast(
          data.channel_detail || "Handover started in Studio but customer was not notified on WhatsApp",
          { icon: "⚠️" },
        );
      } else {
        toast.success("Handed over to human support");
      }
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e.response?.data?.detail || "Failed to start handover");
    },
  });

  useEffect(() => {
    const count = detail?.messages.length ?? 0;
    if (count > prevMessageCountRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    prevMessageCountRef.current = count;
  }, [detail?.messages.length, detail?.messages]);

  function handleSendReply() {
    const text = replyText.trim();
    if (!text || replyMut.isPending) return;
    replyMut.mutate();
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

  const aiControlBtn =
    "shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white text-amber-900 px-3 py-1.5 text-[11px] font-medium hover:bg-amber-50 disabled:opacity-50";

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

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden bg-white lg:bg-transparent">
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
            <CorrespondentHeading
              displayName={detail.display_name}
              phone={detail.phone}
              userId={detail.user_id}
              className="text-sm sm:text-base min-w-0"
            />
            <p className="text-[10px] sm:text-xs text-gray-400 truncate">
              {detail.last_activity_at
                ? `${formatDistanceToNow(new Date(detail.last_activity_at), { addSuffix: true })} · ${detail.messages.length} msgs`
                : `No activity · ${detail.messages.length} msgs`}
              {detailFetching && <span className="ml-1 text-gray-400">· updating…</span>}
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              if (typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches) {
                setTagsExpanded((v) => !v);
              } else {
                setMobileTagsOpen((v) => !v);
              }
            }}
            className={clsx(
              "relative inline-flex items-center justify-center rounded-xl p-2.5 border transition-colors shrink-0",
              mobileTagsOpen || tagsExpanded
                ? "border-brand-200 bg-brand-50 text-brand-700"
                : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50",
            )}
            aria-expanded={mobileTagsOpen || tagsExpanded}
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
        </div>
      </div>

      <div
        className={clsx(
          "flex items-center gap-2 px-3 py-2 sm:px-4 text-[11px] border-b shrink-0",
          detail.frozen
            ? "bg-amber-50 border-amber-100 text-amber-900"
            : "bg-slate-50 border-gray-100 text-gray-700",
        )}
      >
        {detail.frozen ? (
          <Snowflake size={13} className="shrink-0" aria-hidden />
        ) : (
          <Bot size={13} className="shrink-0 text-brand-600" aria-hidden />
        )}
        <span className="flex-1 min-w-0">
          {detail.frozen
            ? "Human handover — AI support agent paused"
            : "AI support agent active"}
        </span>
        {detail.frozen ? (
          <button
            type="button"
            className={aiControlBtn}
            disabled={resumeBotMut.isPending}
            onClick={() => resumeBotMut.mutate()}
            title="Unfreeze session and let the AI reply again"
          >
            {resumeBotMut.isPending ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Bot size={12} />
            )}
            Resume AI support
          </button>
        ) : (
          <button
            type="button"
            className={aiControlBtn}
            disabled={handoverBotMut.isPending}
            onClick={() => handoverBotMut.mutate()}
            title="Pause AI and hand chat to a human agent"
          >
            {handoverBotMut.isPending ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <UserRound size={12} />
            )}
            Hand over to human
          </button>
        )}
      </div>

      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
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
            <div ref={messagesEndRef} />
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

        <aside className="hidden lg:flex lg:w-72 xl:w-80 shrink-0 flex-col border-l border-gray-100 bg-surface-muted/40 min-h-0">
          <div className="shrink-0 border-b border-gray-100 p-3 flex items-center justify-between gap-2 bg-white/80">
            <span className="text-xs font-semibold text-gray-600">Tags</span>
            <button
              type="button"
              onClick={() => setTagsExpanded((v) => !v)}
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium border",
                tagsExpanded ? "border-brand-200 bg-brand-50 text-brand-800" : "border-gray-200 text-gray-600 hover:bg-gray-50",
              )}
            >
              <Tags size={14} />
              {tagCount > 0 ? `${tagCount}` : "Edit"}
            </button>
          </div>
          {tagsExpanded && <div className="p-3 overflow-y-auto flex-1 min-h-0 bg-white">{tagsBody}</div>}
        </aside>
      </div>

      {mobileTagsOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close"
            onClick={() => setMobileTagsOpen(false)}
          />
          <div className="relative bg-white rounded-t-2xl shadow-2xl border-t border-gray-100 max-h-[min(78vh,560px)] flex flex-col animate-slide-up">
            <div className="flex justify-center pt-2 pb-1">
              <div className="h-1 w-10 rounded-full bg-gray-200" />
            </div>
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
              <span className="text-sm font-semibold text-gray-900">Contact tags</span>
              <button type="button" className="btn-ghost btn-sm text-gray-500" onClick={() => setMobileTagsOpen(false)}>
                Done
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">{tagsBody}</div>
          </div>
        </div>
      )}
    </div>
  );
}
