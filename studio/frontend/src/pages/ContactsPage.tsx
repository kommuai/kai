import { useState, useEffect } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Search, User } from "lucide-react";
import { contactsApi, tenantsApi, type ContactOut, type Tenant } from "../lib/api";
import Spinner from "../components/Spinner";

export default function ContactsPage() {
  const { slug } = useParams<{ slug: string }>();
  const ctx = useOutletContext<{ tenant?: Tenant } | undefined>();
  const [searchInput, setSearchInput] = useState("");
  const [debounced, setDebounced] = useState("");
  const [tagFilter, setTagFilter] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(searchInput.trim()), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data: tenantQ } = useQuery({
    queryKey: ["tenantBySlug", slug],
    queryFn: () => tenantsApi.getBySlug(slug!),
    enabled: !!slug && !ctx?.tenant,
  });
  const tenant = ctx?.tenant ?? tenantQ;
  const tenantId = tenant?.id;
  const base = `/t/${slug}`;

  const { data, isLoading } = useQuery({
    queryKey: ["contacts", tenantId, debounced, tagFilter],
    queryFn: () =>
      contactsApi.list(tenantId!, {
        search: debounced || undefined,
        tag: tagFilter || undefined,
        limit: 100,
      }),
    enabled: !!tenantId,
  });

  const allTags = Array.from(
    new Set((data?.items ?? []).flatMap((c: ContactOut) => c.tags)),
  ).sort();

  if (!tenant) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="input pl-10"
            placeholder="Search by name or user id…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        <select
          className="input sm:w-48"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
        >
          <option value="">All tags</option>
          {allTags.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Spinner className="text-brand-600" />
        </div>
      ) : !data?.items.length ? (
        <div className="card p-10 text-center text-sm text-gray-500">No contacts found.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((c: ContactOut) => (
            <Link
              key={c.user_id}
              to={`${base}/inbox/${encodeURIComponent(c.user_id)}`}
              className="card p-4 hover:shadow-card-lg transition-shadow group"
            >
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
                  <User size={18} className="text-brand-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-gray-900 truncate group-hover:text-brand-700">{c.display_name}</div>
                  <div className="text-xs font-mono text-gray-500 truncate mt-0.5">{c.user_id}</div>
                  {c.fact_preview && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">{c.fact_preview}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {c.frozen && <span className="badge-orange">Handover</span>}
                    {c.tags.map((tag) => (
                      <span key={tag} className="badge-gray text-[10px]">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <p className="text-[10px] text-gray-400 mt-2">
                    {c.last_activity_at
                      ? formatDistanceToNow(new Date(c.last_activity_at), { addSuffix: true })
                      : "—"}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
