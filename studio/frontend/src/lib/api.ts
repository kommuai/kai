import axios from "axios";
import type { AxiosError } from "axios";

/** In dev, use same-origin + Vite proxy. In production, set VITE_API_URL. */
export const API_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : import.meta.env.DEV
    ? ""
    : "http://localhost:8080";

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("kai_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      const path = window.location.pathname;
      const isAuthRoute =
        path === "/login" ||
        path.startsWith("/auth/") ||
        path.startsWith("/invite/") ||
        path === "/terms" ||
        path === "/privacy";
      if (!isAuthRoute) {
        localStorage.removeItem("kai_token");
        localStorage.removeItem("kai_user");
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  },
);

export default api;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string;
  provider: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Tenant {
  id: string;
  owner_id: string;
  slug: string;
  display_name: string;
  description: string;
  workspace_home: string;
  created_at: string;
  updated_at: string;
}

export interface SkillCapabilityOut {
  id: string;
  description: string;
  enabled: boolean;
  source: "profile" | "document";
  path: string | null;
  builtin: string | null;
  canonical_builtin: string | null;
  plugin: string | null;
}

export interface TenantCapabilitiesOut {
  active_profile: string;
  skills: SkillCapabilityOut[];
}

export interface FileContentOut {
  path: string;
  content: string;
}

export interface CompileResult {
  ok: boolean;
  message: string;
  intents: number | null;
}

export interface InviteOut {
  id: string;
  tenant_id: string;
  email: string;
  token: string;
  status: string;
  created_at: string;
  expires_at: string | null;
  invite_url?: string | null;
}

export interface InvitePreviewOut {
  email: string;
  tenant_name: string;
  tenant_slug: string;
  status: string;
  expired: boolean;
}

// ── Inbox / Contacts ─────────────────────────────────────────────────────────

export interface MessageOut {
  role: string;
  text: string;
  created_at: string | null;
}

export interface MemoryFactOut {
  fact_type: string;
  fact_key: string;
  fact_value: string;
  last_seen_at: string | null;
}

export interface ConversationOut {
  user_id: string;
  frozen: boolean;
  last_activity_at: string | null;
  last_message_preview: string;
  message_count: number;
}

export interface ConversationListOut {
  items: ConversationOut[];
  total: number;
}

export interface ConversationDetailOut {
  user_id: string;
  frozen: boolean;
  last_activity_at: string | null;
  messages: MessageOut[];
  facts: MemoryFactOut[];
  tags: string[];
  chatwoot_conversation_id?: string | null;
}

export interface ChatwootMetaOut {
  configured: boolean;
  conversation_id: string | null;
  status: string | null;
  labels: string[];
}

export interface ChatwootAccountLabelsOut {
  items: Record<string, unknown>[];
}

export interface SearchHitOut {
  user_id: string;
  message_id: number;
  role: string;
  snippet: string;
  created_at: string;
}

export interface SearchResultsOut {
  query: string;
  items: SearchHitOut[];
}

export interface ContactOut {
  user_id: string;
  display_name: string;
  last_activity_at: string | null;
  frozen: boolean;
  tags: string[];
  fact_preview: string;
}

export interface ContactListOut {
  items: ContactOut[];
  total: number;
}

export interface ContactDetailOut {
  user_id: string;
  display_name: string;
  frozen: boolean;
  last_activity_at: string | null;
  facts: MemoryFactOut[];
  tags: string[];
}

export interface ReplyOut {
  ok: boolean;
  message: MessageOut;
  chatwoot_delivered: boolean;
  chatwoot_error: string | null;
  chatwoot_conversation_id: string | null;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface OAuthProviders {
  google: boolean;
  facebook: boolean;
}

export const authApi = {
  signup: (data: { email: string; password: string; name: string }) =>
    api.post<TokenResponse>("/auth/signup", data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", data).then((r) => r.data),

  me: () => api.get<User>("/auth/me").then((r) => r.data),

  providers: () => api.get<OAuthProviders>("/auth/providers").then((r) => r.data),

  googleUrl: () => `${API_BASE}/auth/google`,
  facebookUrl: () => `${API_BASE}/auth/facebook`,
};

// ── Tenants ───────────────────────────────────────────────────────────────────

export const tenantsApi = {
  list: () => api.get<Tenant[]>("/tenants").then((r) => r.data),

  create: (data: {
    display_name: string;
    slug: string;
    description?: string;
    personality?: string;
    bot_name?: string;
    company_name?: string;
    product_summary?: string;
    scope_cannot_answer?: string[];
    escalation_rules?: string[];
    fallback_behavior?: string;
  }) =>
    api.post<Tenant>("/tenants", data).then((r) => r.data),

  get: (id: string) => api.get<Tenant>(`/tenants/${id}`).then((r) => r.data),
  getBySlug: (slug: string) => api.get<Tenant>(`/tenants/by-slug/${slug}`).then((r) => r.data),

  delete: (id: string, opts?: { deleteWorkspace?: boolean }) =>
    api
      .delete(`/tenants/${id}`, { params: { delete_workspace: opts?.deleteWorkspace ?? false } })
      .then((r) => r.data),

  capabilities: (id: string) =>
    api.get<TenantCapabilitiesOut>(`/tenants/${id}/capabilities`).then((r) => r.data),

  toggleSkill: (tenantId: string, skillId: string, data: { enabled: boolean; source: "profile" | "document"; path?: string | null }) =>
    api.patch<TenantCapabilitiesOut>(`/tenants/${tenantId}/capabilities/skills/${encodeURIComponent(skillId)}`, data).then((r) => r.data),

  getFile: (id: string, fileKey: string) =>
    api.get<FileContentOut>(`/tenants/${id}/files/${fileKey}`).then((r) => r.data),

  putFile: (id: string, fileKey: string, content: string) =>
    api.put<FileContentOut>(`/tenants/${id}/files/${fileKey}`, { content }).then((r) => r.data),

  compile: (id: string) =>
    api.post<CompileResult>(`/tenants/${id}/compile`).then((r) => r.data),

  listInvites: (tenantId: string) =>
    api.get<InviteOut[]>(`/tenants/${tenantId}/invites`).then((r) => r.data),

  createInvite: (tenantId: string, email: string) =>
    api.post<InviteOut>(`/tenants/${tenantId}/invites`, { email }).then((r) => r.data),

  revokeInvite: (tenantId: string, inviteId: string) =>
    api.delete<void>(`/tenants/${tenantId}/invites/${inviteId}`).then((r) => r.data),

  invitePreview: (token: string) =>
    api.get<InvitePreviewOut>(`/tenants/invites/${encodeURIComponent(token)}`).then((r) => r.data),

  acceptInvite: (token: string) =>
    api.post<Tenant>("/tenants/invites/accept", { token }).then((r) => r.data),
};

export interface AiAssistPatch {
  file: "workspace" | "system_prompt" | "faq";
  path: string;
  diff: string;
}

export interface AiAssistApplyResult {
  ok: boolean;
  applied: Array<{ file: string; path: string; diff: string; new_content: string }>;
  summary: string;
}

export const aiAssistApi = {
  /** Returns the raw fetch response (caller manages SSE stream). */
  chat: (
    tenantId: string,
    messages: Array<{ role: "user" | "assistant"; content: string }>,
  ): Promise<Response> =>
    fetch(`/tenants/${tenantId}/ai-assist/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("kai_token") ?? ""}`,
      },
      body: JSON.stringify({ messages }),
    }),

  applyPatches: (
    tenantId: string,
    messages: Array<{ role: "user" | "assistant"; content: string }>,
  ): Promise<AiAssistApplyResult> =>
    fetch(`/tenants/${tenantId}/ai-assist/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("kai_token") ?? ""}`,
      },
      body: JSON.stringify({ messages, apply_patches: true }),
    }).then((r) => r.json()),
};

function encSeg(s: string) {
  return encodeURIComponent(s);
}

export const inboxApi = {
  conversations: (
    tenantId: string,
    params?: { status?: "all" | "active" | "frozen"; limit?: number; offset?: number },
  ) => api.get<ConversationListOut>(`/tenants/${tenantId}/inbox/conversations`, { params }).then((r) => r.data),

  search: (tenantId: string, q: string, params?: { limit?: number; offset?: number }) =>
    api
      .get<SearchResultsOut>(`/tenants/${tenantId}/inbox/conversations/search`, { params: { q, ...params } })
      .then((r) => r.data),

  conversation: (tenantId: string, userId: string) =>
    api.get<ConversationDetailOut>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}`).then((r) => r.data),

  reply: (tenantId: string, userId: string, text: string) =>
    api
      .post<ReplyOut>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/reply`, { text })
      .then((r) => r.data),

  chatwootMeta: (tenantId: string, userId: string) =>
    api.get<ChatwootMetaOut>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot`).then((r) => r.data),

  chatwootAccountLabels: (tenantId: string) =>
    api.get<ChatwootAccountLabelsOut>(`/tenants/${tenantId}/inbox/chatwoot/account-labels`).then((r) => r.data),

  chatwootSetStatus: (tenantId: string, userId: string, body: { status: string; snoozed_until?: number | null }) =>
    api
      .post<{ ok: boolean }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot/status`, body)
      .then((r) => r.data),

  chatwootPrivateNote: (tenantId: string, userId: string, text: string) =>
    api
      .post<{ ok: boolean }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot/private-note`, {
        text,
      })
      .then((r) => r.data),

  chatwootSetLabels: (tenantId: string, userId: string, labels: string[]) =>
    api
      .put<{ ok: boolean; labels: string[] }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot/labels`, {
        labels,
      })
      .then((r) => r.data),

  chatwootHandover: (tenantId: string, userId: string) =>
    api
      .post<{ ok: boolean }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot/handover`)
      .then((r) => r.data),

  chatwootResumeBot: (tenantId: string, userId: string) =>
    api
      .post<{ ok: boolean }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/chatwoot/resume-bot`)
      .then((r) => r.data),
};

export const contactsApi = {
  list: (tenantId: string, params?: { search?: string; tag?: string; limit?: number; offset?: number }) =>
    api.get<ContactListOut>(`/tenants/${tenantId}/contacts`, { params }).then((r) => r.data),

  get: (tenantId: string, userId: string) =>
    api.get<ContactDetailOut>(`/tenants/${tenantId}/contacts/${encSeg(userId)}`).then((r) => r.data),

  addTag: (tenantId: string, userId: string, tag: string) =>
    api.post<void>(`/tenants/${tenantId}/contacts/${encSeg(userId)}/tags`, { tag }).then((r) => r.data),

  removeTag: (tenantId: string, userId: string, tag: string) =>
    api.delete<void>(`/tenants/${tenantId}/contacts/${encSeg(userId)}/tags/${encSeg(tag)}`).then((r) => r.data),
};
