import { useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Send,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { hitlApi, tenantsApi, type AiAssistPatch, type HitlTicket, type Tenant } from "../lib/api";
import FileDiffViewer from "../components/FileDiffViewer";
import Spinner from "../components/Spinner";

const OPEN_STATUSES = new Set(["open", "replied"]);

function isOpenTicket(ticket: HitlTicket): boolean {
  return OPEN_STATUSES.has(ticket.status);
}

const FILE_LABELS: Record<string, string> = {
  workspace: "workspace.yaml",
  system_prompt: "system_prompt.md",
  faq: "knowledge/master_faq.md",
};

function patchLabel(patch: AiAssistPatch): string {
  if (patch.intent_id) return `knowledge/master_faq.md → ${patch.intent_id}`;
  if (patch.file.startsWith("plugin:")) return `tools/plugins/${patch.file.slice(7)}/main.py`;
  return FILE_LABELS[patch.file] ?? patch.path;
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    open: "bg-amber-100 text-amber-800",
    replied: "bg-blue-100 text-blue-800",
    resolved: "bg-emerald-100 text-emerald-800",
    dismissed: "bg-gray-100 text-gray-600",
    out_of_scope: "bg-gray-100 text-gray-600",
  };
  return map[status] ?? "bg-gray-100 text-gray-700";
}

function statusLabel(status: string): string {
  if (status === "out_of_scope") return "out of scope";
  return status.replace(/_/g, " ");
}

function TicketDetail({
  tenantId,
  ticket,
  onUpdated,
}: {
  tenantId: string;
  ticket: HitlTicket;
  onUpdated: () => void;
}) {
  const [replyText, setReplyText] = useState(ticket.operator_reply ?? "");
  const [expandedDiffs, setExpandedDiffs] = useState<Set<number>>(new Set([0]));
  const patches = ticket.kb_patch_preview ?? [];
  const open = isOpenTicket(ticket);

  const replyMut = useMutation({
    mutationFn: () => hitlApi.reply(tenantId, ticket.ticket_id, replyText.trim()),
    onSuccess: (data) => {
      toast.success(data.channel_delivered ? "Reply sent to customer" : data.channel_detail || "Reply saved");
      onUpdated();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to send reply");
    },
  });

  const proposeMut = useMutation({
    mutationFn: () => hitlApi.proposeKnowledge(tenantId, ticket.ticket_id),
    onSuccess: () => {
      toast.success("Knowledge update proposed — review the diff below");
      onUpdated();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to propose KB update");
    },
  });

  const applyMut = useMutation({
    mutationFn: () => hitlApi.applyKnowledge(tenantId, ticket.ticket_id),
    onSuccess: () => {
      toast.success("Knowledge base updated — ticket archived");
      onUpdated();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to apply KB update");
    },
  });

  const rejectMut = useMutation({
    mutationFn: () => hitlApi.rejectKnowledge(tenantId, ticket.ticket_id),
    onSuccess: () => {
      toast.success("KB update dismissed");
      onUpdated();
    },
  });

  const outOfScopeMut = useMutation({
    mutationFn: () => hitlApi.outOfScope(tenantId, ticket.ticket_id),
    onSuccess: () => {
      toast.success("Marked out of scope — archived");
      onUpdated();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to archive ticket");
    },
  });

  const canProposeKb = open && !!ticket.operator_reply && ticket.kb_patch_status === "none";
  const canReviewKb = open && ticket.kb_patch_status === "pending_review" && patches.length > 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full capitalize", statusBadge(ticket.status))}>
            {statusLabel(ticket.status)}
          </span>
          {ticket.confidence != null && (
            <span className="text-xs text-gray-500">
              Confidence {(ticket.confidence * 100).toFixed(0)}%
            </span>
          )}
          {ticket.verification_flagged && (
            <span className="inline-flex items-center gap-1 text-xs text-amber-700">
              <AlertTriangle size={12} /> Verification flagged
            </span>
          )}
        </div>

        {ticket.impact_reason && (
          <p className="text-xs text-gray-500">
            <ShieldAlert size={12} className="inline mr-1" />
            Impact: {ticket.impact_reason}
          </p>
        )}

        <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
          <p className="text-xs font-medium text-gray-500 mb-1">Customer question</p>
          <p className="text-sm text-gray-900 whitespace-pre-wrap">{ticket.user_question}</p>
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3">
          <p className="text-xs font-medium text-amber-800 mb-1">Bot answer (needs review)</p>
          <p className="text-sm text-gray-900 whitespace-pre-wrap">{ticket.bot_answer}</p>
        </div>

        {ticket.operator_reply && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
            <p className="text-xs font-medium text-emerald-800 mb-1">Your reply to customer</p>
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{ticket.operator_reply}</p>
          </div>
        )}

        {canReviewKb && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/30 p-3 space-y-3">
            <p className="text-sm font-medium text-brand-900">Proposed knowledge base update</p>
            {patches.map((patch, i) => (
              <div key={i} className="rounded-lg border border-gray-200 bg-white overflow-hidden">
                <button
                  type="button"
                  className="w-full flex items-center justify-between px-3 py-2 text-left text-xs font-medium text-gray-700 hover:bg-gray-50"
                  onClick={() =>
                    setExpandedDiffs((prev) => {
                      const next = new Set(prev);
                      if (next.has(i)) next.delete(i);
                      else next.add(i);
                      return next;
                    })
                  }
                >
                  {patchLabel(patch)}
                  {expandedDiffs.has(i) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {expandedDiffs.has(i) && patch.diff && (
                  <div className="border-t border-gray-100 p-2">
                    <FileDiffViewer diff={patch.diff} />
                  </div>
                )}
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={applyMut.isPending}
                onClick={() => applyMut.mutate()}
                className="btn-primary text-sm inline-flex items-center gap-1.5"
              >
                {applyMut.isPending ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Apply to knowledge base
              </button>
              <button
                type="button"
                disabled={rejectMut.isPending}
                onClick={() => rejectMut.mutate()}
                className="btn-secondary text-sm inline-flex items-center gap-1.5"
              >
                <XCircle size={14} />
                Reject
              </button>
            </div>
          </div>
        )}
      </div>

      {open && (
        <div className="border-t border-gray-200 p-4 space-y-3 bg-white shrink-0">
          <label className="label">Reply to customer</label>
          <textarea
            className="input resize-none min-h-[80px]"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write the verified answer to send on WhatsApp…"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!replyText.trim() || replyMut.isPending}
              onClick={() => replyMut.mutate()}
              className="btn-primary text-sm inline-flex items-center gap-1.5"
            >
              {replyMut.isPending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              Send to customer
            </button>
            {canProposeKb && (
              <button
                type="button"
                disabled={proposeMut.isPending}
                onClick={() => proposeMut.mutate()}
                className="btn-secondary text-sm"
              >
                {proposeMut.isPending ? "Generating…" : "Generate KB update"}
              </button>
            )}
            <button
              type="button"
              disabled={outOfScopeMut.isPending}
              onClick={() => outOfScopeMut.mutate()}
              className="btn-secondary text-sm inline-flex items-center gap-1.5 text-gray-600"
            >
              {outOfScopeMut.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Ban size={14} />
              )}
              Out of scope
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HitlReviewPage() {
  const { slug } = useParams<{ slug: string }>();
  const ctx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"open" | "archived">("open");

  const { data: tenantQ } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !ctx?.tenant,
  });
  const tenant = ctx?.tenant ?? tenantQ;
  const tenantId = tenant?.id;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["hitl-tickets", tenantId, filter],
    queryFn: () => hitlApi.tickets(tenantId!, { queue: filter, limit: 80 }),
    enabled: !!tenantId,
    refetchInterval: 15_000,
  });

  const tickets = data?.tickets ?? [];
  const selected = tickets.find((t) => t.ticket_id === selectedId) ?? tickets[0] ?? null;

  const invalidate = () => {
    setSelectedId(null);
    qc.invalidateQueries({ queryKey: ["hitl-tickets", tenantId] });
    refetch();
  };

  if (!tenantId && !tenantQ) return <Spinner className="m-8" />;

  return (
    <div className="flex flex-col h-[calc(100vh-0px)] md:h-full max-w-6xl mx-auto w-full">
      <div className="px-4 py-3 border-b border-gray-200 bg-white shrink-0">
        <h1 className="text-lg font-semibold text-gray-900">Human review</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Low-confidence, high-impact answers flagged during live chat
        </p>
        <div className="flex gap-2 mt-3">
          {(["open", "archived"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => {
                setFilter(f);
                setSelectedId(null);
              }}
              className={clsx(
                "text-xs px-3 py-1 rounded-full capitalize",
                filter === f ? "bg-brand-100 text-brand-800 font-medium" : "bg-gray-100 text-gray-600",
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        <div className="w-full md:w-80 border-r border-gray-200 bg-white overflow-y-auto shrink-0">
          {isLoading ? (
            <Spinner className="m-6" />
          ) : tickets.length === 0 ? (
            <p className="text-sm text-gray-500 p-4">
              {filter === "open" ? "No open tickets." : "No archived tickets."}
            </p>
          ) : (
            <ul>
              {tickets.map((t) => (
                <li key={t.ticket_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(t.ticket_id)}
                    className={clsx(
                      "w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50",
                      selected?.ticket_id === t.ticket_id && "bg-brand-50",
                    )}
                  >
                    <p className="text-sm font-medium text-gray-900 line-clamp-2">{t.user_question}</p>
                    <p className="text-xs text-gray-500 mt-1 truncate">{t.user_id}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={clsx(
                          "text-[10px] px-1.5 py-0.5 rounded capitalize",
                          statusBadge(t.status),
                        )}
                      >
                        {statusLabel(t.status)}
                      </span>
                      <span className="text-[10px] text-gray-400">
                        {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="hidden md:flex flex-1 flex-col min-w-0 bg-gray-50">
          {selected ? (
            <TicketDetail tenantId={tenantId!} ticket={selected} onUpdated={invalidate} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-500">
              Select a ticket to review
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="md:hidden border-t border-gray-200 bg-white max-h-[50vh] overflow-hidden flex flex-col">
          <TicketDetail tenantId={tenantId!} ticket={selected} onUpdated={invalidate} />
        </div>
      )}
    </div>
  );
}
