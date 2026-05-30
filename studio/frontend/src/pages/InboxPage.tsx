import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Search, MessageSquare, Inbox, Trash2 } from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { inboxApi, tenantsApi, type ConversationOut, type SearchHitOut, type Tenant } from "../lib/api";
import { CorrespondentHeading } from "../lib/contactDisplay";
import { INBOX_LIST_POLL_MS } from "../lib/inboxPolling";
import Spinner from "../components/Spinner";

type StatusTab = "all" | "active" | "frozen";

function inboxErrorMessage(err: unknown): string {
  const e = err as { response?: { status?: number; data?: { detail?: string } } };
  const status = e.response?.status;
  const detail = e.response?.data?.detail;
  if (status === 404) return "Inbox API not found. Restart the backend so latest routes are loaded.";
  if (status === 503 && detail) return String(detail);
  if (detail) return String(detail);
  return "Failed to load conversations.";
}

export default function InboxPage() {
  const { slug, userId } = useParams<{ slug: string; userId?: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const ctx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const [status, setStatus] = useState<StatusTab>("all");
  const [searchInput, setSearchInput] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(searchInput.trim()), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const tenant = ctx?.tenant;
  const { data: tenantQ } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !tenant,
  });
  const t = tenant ?? tenantQ;
  const tenantId = t?.id;
  const base = `/t/${slug}`;
  const hasDetail = !!userId;

  const { data: convData, isLoading: convLoading, error: convError, isFetching: convFetching } = useQuery({
    queryKey: ["inbox-conversations", tenantId, status],
    queryFn: () => inboxApi.conversations(tenantId!, { status, limit: 80 }),
    enabled: !!tenantId && !debounced,
    staleTime: 2_000,
    refetchInterval: debounced ? false : INBOX_LIST_POLL_MS,
    refetchOnWindowFocus: true,
  });

  const { data: searchData, isLoading: searchLoading, error: searchError } = useQuery({
    queryKey: ["inbox-search", tenantId, debounced],
    queryFn: () => inboxApi.search(tenantId!, debounced, { limit: 50 }),
    enabled: !!tenantId && debounced.length >= 2,
  });

  const showSearch = debounced.length >= 2;

  const deleteMut = useMutation({
    mutationFn: (targetUserId: string) => inboxApi.deleteConversation(tenantId!, targetUserId),
    onSuccess: (_data, targetUserId) => {
      toast.success("Conversation deleted");
      qc.invalidateQueries({ queryKey: ["inbox-conversations", tenantId] });
      qc.invalidateQueries({ queryKey: ["inbox-search", tenantId] });
      qc.invalidateQueries({ queryKey: ["contacts", tenantId] });
      qc.removeQueries({ queryKey: ["conversation", tenantId, targetUserId] });
      const active = userId ? decodeURIComponent(userId) : "";
      if (active === targetUserId) {
        navigate(`${base}/inbox`, { replace: true });
      }
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } };
      toast.error(e.response?.data?.detail || "Failed to delete conversation");
    },
  });

  const confirmDelete = (targetUserId: string, label: string) => {
    const name = label.trim() || targetUserId;
    if (
      !window.confirm(
        `Delete the entire chat with ${name}? This removes all messages from the database and cannot be undone.`,
      )
    ) {
      return;
    }
    deleteMut.mutate(targetUserId);
  };

  const rows = useMemo(() => {
    if (showSearch && searchData) {
      return searchData.items.map((h: SearchHitOut) => ({ kind: "search" as const, hit: h }));
    }
    if (!showSearch && convData) {
      return convData.items.map((c: ConversationOut) => ({ kind: "conv" as const, conv: c }));
    }
    return [];
  }, [showSearch, searchData, convData]);

  if (!t) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  const rowNavCls = (isActive: boolean) =>
    clsx(
      "flex items-start gap-3 px-4 py-3 transition-colors border-l-2",
      isActive
        ? "bg-brand-50/70 border-l-brand-600"
        : "hover:bg-gray-50 border-l-transparent",
    );

  const listPanel = (
    <section className="flex flex-col flex-1 min-w-0 overflow-hidden">
      {/* Search */}
      <div className="p-3 border-b border-gray-100 space-y-2 bg-white shrink-0">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <input
            className="input pl-9 py-2 text-sm"
            placeholder="Search conversations…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        {!showSearch && (
          <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
            {(
              [
                ["all", "All", "All"],
                ["active", "AI", "AI active"],
                ["frozen", "Handover", "Handover"],
              ] as const
            ).map(([key, short, long]) => (
              <button
                key={key}
                type="button"
                onClick={() => setStatus(key)}
                className={clsx(
                  "flex-1 rounded-md px-1.5 sm:px-2 py-1.5 text-[11px] sm:text-xs font-medium transition-all min-w-0",
                  status === key
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-800",
                )}
              >
                <span className="sm:hidden">{short}</span>
                <span className="hidden sm:inline">{long}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {(showSearch ? searchError : convError) ? (
          <div className="py-10 px-5 text-center text-sm text-red-700 bg-red-50">
            {inboxErrorMessage(showSearch ? searchError : convError)}
          </div>
        ) : (convLoading && !showSearch) || (searchLoading && showSearch) ? (
          <div className="flex justify-center py-16">
            <Spinner className="text-brand-600" />
          </div>
        ) : rows.length === 0 ? (
          <div className="py-16 px-5 text-center text-sm text-gray-400">
            {showSearch
              ? "No matches found."
              : "No conversations yet. When customers message the AI support agent, they appear here."}
          </div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {rows.map((row, i) =>
              row.kind === "conv" ? (
                <li key={row.conv.user_id} className="group relative">
                  <NavLink
                    to={`${base}/inbox/${encodeURIComponent(row.conv.user_id)}`}
                    className={({ isActive }) => clsx(rowNavCls(isActive), "pr-10")}
                  >
                    <div className="mt-0.5 h-8 w-8 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
                      <MessageSquare size={14} className="text-brand-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <CorrespondentHeading
                          displayName={row.conv.display_name}
                          phone={row.conv.phone}
                          userId={row.conv.user_id}
                          className="text-sm min-w-0"
                        />
                        {row.conv.frozen ? (
                          <span className="badge-orange shrink-0">Handover</span>
                        ) : (
                          <span className="badge-green shrink-0">AI</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 truncate mt-0.5">
                        {row.conv.last_message_preview || "—"}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {row.conv.last_activity_at
                          ? formatDistanceToNow(new Date(row.conv.last_activity_at), { addSuffix: true })
                          : "No activity"}
                        {" · "}
                        {row.conv.message_count} msgs
                      </p>
                    </div>
                  </NavLink>
                  <button
                    type="button"
                    title="Delete conversation"
                    aria-label="Delete conversation"
                    disabled={deleteMut.isPending}
                    className={clsx(
                      "absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg",
                      "text-gray-400 hover:text-red-600 hover:bg-red-50",
                      "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 transition-opacity",
                    )}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      confirmDelete(row.conv.user_id, row.conv.display_name || row.conv.phone || "");
                    }}
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ) : (
                <li key={`${row.hit.user_id}-${row.hit.message_id}-${i}`} className="group relative">
                  <NavLink
                    to={`${base}/inbox/${encodeURIComponent(row.hit.user_id)}`}
                    className={({ isActive }) => clsx(rowNavCls(isActive), "pr-10")}
                  >
                    <div className="flex-1 min-w-0">
                      <CorrespondentHeading
                        displayName={row.hit.display_name}
                        phone={row.hit.phone}
                        userId={row.hit.user_id}
                        className="text-sm"
                      />
                      <p className="text-sm text-gray-700 mt-0.5 line-clamp-2">{row.hit.snippet}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{row.hit.role}</p>
                    </div>
                  </NavLink>
                  <button
                    type="button"
                    title="Delete conversation"
                    aria-label="Delete conversation"
                    disabled={deleteMut.isPending}
                    className={clsx(
                      "absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg",
                      "text-gray-400 hover:text-red-600 hover:bg-red-50",
                      "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 transition-opacity",
                    )}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      confirmDelete(row.hit.user_id, row.hit.display_name || row.hit.phone || "");
                    }}
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ),
            )}
          </ul>
        )}
      </div>
    </section>
  );

  return (
    <div className="studio-panel-fill animate-fade-in card overflow-hidden lg:flex-row min-h-0">
      {/* Left panel: conversation list */}
      <div
        className={clsx(
          "flex flex-col border-r border-gray-100 overflow-hidden",
          hasDetail
            ? "hidden lg:flex lg:w-[300px] xl:w-[360px] shrink-0"
            : "flex w-full lg:w-[300px] xl:w-[360px] shrink-0",
        )}
      >
        {/* Panel header */}
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-gray-100 bg-gray-50/80 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Inbox size={15} className="text-brand-600 shrink-0" />
            <h1 className="text-sm font-semibold text-gray-900">Inbox</h1>
          </div>
          {!debounced && convFetching && (
            <span className="text-[10px] text-gray-400 animate-pulse shrink-0">Updating…</span>
          )}
        </div>
        {listPanel}
      </div>

      {/* Right panel: conversation detail */}
      <div
        className={clsx(
          "flex-1 min-h-0 min-w-0 flex-col overflow-hidden",
          hasDetail ? "flex" : "hidden lg:flex",
        )}
      >
        {hasDetail ? (
          <Outlet context={{ tenant: t }} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-gray-400 bg-surface-muted">
            <div className="h-16 w-16 rounded-2xl bg-gray-100 flex items-center justify-center">
              <MessageSquare size={28} className="text-gray-300" />
            </div>
            <p className="text-sm">Select a conversation to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
