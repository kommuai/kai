import axios from "axios";
import type { AxiosError } from "axios";

/** Dev: same-origin + Vite proxy. Prod behind nginx: leave VITE_API_URL unset (same-origin). */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_URL as string | undefined;
  if (fromEnv != null && String(fromEnv).trim() !== "") return fromEnv.trim();
  return "";
}

export const API_BASE = resolveApiBase();

/** Absolute or proxied path for fetch() — must match axios baseURL (upload/bootstrap use fetch). */
export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const base = (API_BASE || "").replace(/\/$/, "");
  return base ? `${base}${normalized}` : normalized;
}

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("shadou_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // Let the browser set multipart boundary (axios must not force application/json).
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    config.headers.delete("Content-Type");
  }
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
        localStorage.removeItem("shadou_token");
        localStorage.removeItem("shadou_user");
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

export interface TrainingJob {
  id: string;
  label: string;
  description: string;
}

export interface AgentTrainingSummary {
  agent_job: string;
  agent_job_label: string;
  current_level: number;
  current_level_title: string;
  current_level_emoji: string;
  next_level: number | null;
  progress_to_next: number;
  last_assessed_at: string | null;
  earned_badges?: string[];
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
  training_summary?: AgentTrainingSummary | null;
}

export interface TrainingLevelDef {
  id: string;
  number: number;
  title: string;
  tagline: string;
  emoji: string;
  color: string;
  meaning: string;
  requirements: { id: string; text: string }[];
}

export interface TrainingGate {
  name: string;
  value: number | null;
  threshold: number;
  ok: boolean;
}

export interface TrainingQuest {
  id: string;
  text: string;
  done: boolean;
}

export interface TrainingLevelResult {
  level_number: number;
  title: string;
  passed: boolean;
  score_pct: number;
  gates: TrainingGate[];
  quests: TrainingQuest[];
}

export interface TrainingSpecializationDef {
  id: string;
  branch: string;
  title: string;
  tagline: string;
  emoji: string;
  color: string;
  prereq_level: number;
  meaning: string;
  requirements: { id: string; text: string }[];
}

export interface TrainingBadgeResult {
  specialization_id: string;
  branch: string;
  title: string;
  passed: boolean;
  score_pct: number;
  locked: boolean;
  lock_reason: string;
  gates: TrainingGate[];
  quests: TrainingQuest[];
}

export interface TrainingStatus {
  agent_job: string;
  agent_job_label: string;
  levels: TrainingLevelDef[];
  specializations: TrainingSpecializationDef[];
  current_level: number;
  current_level_title: string;
  current_level_emoji: string;
  next_level: number | null;
  progress_to_next: number;
  last_assessed_at: string | null;
  level_results: Record<number, TrainingLevelResult>;
  badge_results: Record<string, TrainingBadgeResult>;
  earned_badges: string[];
  quests_next: TrainingQuest[];
}

export interface TrainingRun {
  id: string;
  tenant_id: string;
  level_number: number;
  passed: boolean;
  duration_ms: number;
  created_at: string;
  summary: Record<string, unknown>;
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
  compile?: CompileResult | null;
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
  display_name: string;
  phone: string | null;
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
  display_name: string;
  phone: string | null;
  frozen: boolean;
  last_activity_at: string | null;
  messages: MessageOut[];
  facts: MemoryFactOut[];
  tags: string[];
}

export interface SearchHitOut {
  user_id: string;
  display_name: string;
  phone: string | null;
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

export type WhatsAppDelivery =
  | "live"
  | "configured_only"
  | "bridge_offline"
  | "worker_disabled"
  | "not_configured"
  | "needs_config";

export interface WhatsAppBaileysChannelOut {
  enabled: boolean;
  phone: string | null;
  auth_present: boolean;
  configured: boolean;
  worker_live?: boolean;
  worker_state?: string | null;
  worker_error?: string | null;
  delivery?: WhatsAppDelivery;
}

export interface TenantChannelsOut {
  inbound_provider: string;
  bridge_reachable?: boolean;
  bridge_url?: string;
  worker_enabled?: boolean;
  whatsapp_baileys: WhatsAppBaileysChannelOut;
}

export interface WhatsAppWorkerTenantOut {
  slug: string;
  state: string;
  phone: string | null;
  error: string | null;
  home: string;
}

export interface WhatsAppWorkerOut {
  bridge_reachable: boolean;
  bridge_url?: string;
  worker_enabled: boolean;
  scan_interval_ms?: number;
  tenants: WhatsAppWorkerTenantOut[];
  live_tenant_count: number;
  detail: string | null;
}

export interface ReplyOut {
  ok: boolean;
  message: MessageOut;
  channel_delivered?: boolean | null;
  channel_detail?: string | null;
}

export interface HitlTicket {
  ticket_id: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  user_question: string;
  bot_answer: string;
  confidence: number | null;
  decision: string | null;
  fallback_reason: string | null;
  verification_flagged: boolean;
  impact_reason: string | null;
  status: string;
  operator_reply: string | null;
  replied_at: string | null;
  kb_patch_status: string;
  kb_patch_preview?: AiAssistPatch[] | null;
}

export interface HitlReplyOut {
  ok: boolean;
  ticket: HitlTicket;
  channel_delivered?: boolean;
  channel_detail?: string | null;
}

export interface HitlKbProposeOut {
  ok: boolean;
  ticket: HitlTicket;
  patches: AiAssistPatch[];
  summary: string;
}

export interface HitlKbApplyOut {
  ok: boolean;
  ticket: HitlTicket;
  applied: AiAssistPatch[];
  summary: string;
  compile?: Record<string, unknown> | null;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface OAuthProviders {
  google: boolean;
  facebook: boolean;
}

export interface DeepSeekDailyUsage {
  date: string;
  total_tokens: number;
  cost_usd: number;
  request_count: number;
}

export interface DeepSeekUsageSummary {
  period: string;
  since: string;
  totals: {
    prompt_tokens: number;
    completion_tokens: number;
    cached_prompt_tokens: number;
    total_tokens: number;
    cost_usd: number;
    request_count: number;
  };
  tenants: Array<{
    tenant_id: string;
    slug: string;
    display_name: string;
    prompt_tokens: number;
    completion_tokens: number;
    cached_prompt_tokens: number;
    total_tokens: number;
    cost_usd: number;
    request_count: number;
  }>;
  by_source: Array<{
    source: string;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
    request_count: number;
  }>;
  daily: DeepSeekDailyUsage[];
}

export const usageApi = {
  deepseek: (period: "day" | "month" = "day") =>
    api.get<DeepSeekUsageSummary>("/usage/deepseek", { params: { period } }).then((r) => r.data),
};

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
    onboarding_session_id?: string | null;
    channel_type?: "none" | "telegram" | "whatsapp_cloud" | "whatsapp_baileys";
    agent_job?: string;
  }) =>
    api.post<Tenant>("/tenants", data).then((r) => r.data),

  trainingJobs: () => api.get<TrainingJob[]>("/tenants/training-jobs").then((r) => r.data),

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

  channels: (tenantId: string) =>
    api
      .get<TenantChannelsOut>(`/tenants/${tenantId}/channels`)
      .then((r) => r.data),

  whatsappWorker: () =>
    api
      .get<WhatsAppWorkerOut>("/tenants/whatsapp-worker")
      .then((r) => r.data),

  whatsappStart: (tenantId: string) =>
    api
      .post<{
        link_id: string;
        status: string;
        qr_data_url: string | null;
        phone: string | null;
        error: string | null;
      }>(`/tenants/${tenantId}/whatsapp/start`)
      .then((r) => r.data),

  whatsappStatus: (tenantId: string) =>
    api
      .get<{
        status: string;
        qr_data_url: string | null;
        phone: string | null;
        error: string | null;
      }>(`/tenants/${tenantId}/whatsapp/status`)
      .then((r) => r.data),
};

export const trainingApi = {
  status: (tenantId: string) =>
    api.get<TrainingStatus>(`/tenants/${tenantId}/training`).then((r) => r.data),

  assess: (tenantId: string, opts?: { level?: number; specialization?: string }) =>
    api
      .post<{ run_id: string; status: string; summary: Record<string, unknown> }>(
        `/tenants/${tenantId}/training/assess`,
        {
          level: opts?.level ?? null,
          specialization: opts?.specialization ?? null,
        },
        { timeout: 600000 },
      )
      .then((r) => r.data),

  runs: (tenantId: string, limit = 20) =>
    api.get<TrainingRun[]>(`/tenants/${tenantId}/training/runs`, { params: { limit } }).then((r) => r.data),

  runDetail: (tenantId: string, runId: string) =>
    api
      .get<{ id: string; failures: Array<Record<string, unknown>>; summary: Record<string, unknown> }>(
        `/tenants/${tenantId}/training/runs/${runId}`,
      )
      .then((r) => r.data),
};

export interface AiAssistPatch {
  file: string;
  path: string;
  diff: string;
  type?: string;
  intent_id?: string;
}

export interface AiAssistApplyResult {
  ok: boolean;
  applied: Array<{ file: string; path: string; diff: string; new_content: string }>;
  summary: string;
}

export interface OnboardingDocument {
  name: string;
  size: number;
}

export type BootstrapProgressEvent =
  | { type: "progress"; stage: string; percent: number; message: string }
  | { type: "done"; percent: number; summary: string; applied?: unknown[] }
  | { type: "error"; message: string };

export const onboardingApi = {
  createSession: () =>
    api.post<{ session_id: string }>("/tenants/onboarding/sessions").then((r) => r.data),

  listDocuments: (sessionId: string) =>
    api
      .get<{ documents: OnboardingDocument[] }>(`/tenants/onboarding/sessions/${sessionId}/documents`)
      .then((r) => r.data.documents),

  uploadDocuments: async (sessionId: string, files: File[]): Promise<OnboardingDocument[]> => {
    if (!files.length) {
      throw new Error("No files selected.");
    }
    const path = `/tenants/onboarding/sessions/${sessionId}/documents`;
    const token = localStorage.getItem("shadou_token");
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    let documents: OnboardingDocument[] = [];
    for (const f of files) {
      const name = (f.name || "").trim() || `upload-${Date.now()}.txt`;
      const fd = new FormData();
      fd.append("file", f, name);

      const res = await fetch(apiUrl(path), { method: "POST", headers, body: fd });
      const body = (await res.json().catch(() => null)) as { documents?: OnboardingDocument[]; detail?: string } | null;
      if (!res.ok) {
        const detail = typeof body?.detail === "string" ? body.detail : `Upload failed (${res.status})`;
        throw new Error(detail);
      }
      if (!Array.isArray(body?.documents) || body.documents.length === 0) {
        throw new Error(
          `Upload for "${name}" did not save. Use a .txt, .md, or .pdf file and stay on this page until the filename appears below.`,
        );
      }
      documents = body.documents;
    }
    return documents;
  },

  whatsappStart: (sessionId: string) =>
    api
      .post<{
        link_id: string;
        status: string;
        qr_data_url: string | null;
        phone: string | null;
        error: string | null;
      }>(`/tenants/onboarding/sessions/${sessionId}/whatsapp/start`)
      .then((r) => r.data),

  whatsappStatus: (sessionId: string) =>
    api
      .get<{
        status: string;
        qr_data_url: string | null;
        phone: string | null;
        error: string | null;
      }>(`/tenants/onboarding/sessions/${sessionId}/whatsapp/status`)
      .then((r) => r.data),

  bootstrap: (tenantId: string, questionnaire: Record<string, unknown>): Promise<Response> =>
    fetch(apiUrl(`/tenants/onboarding/${tenantId}/bootstrap`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("shadou_token") ?? ""}`,
      },
      body: JSON.stringify({ questionnaire }),
    }),
};

export async function consumeBootstrapStream(
  response: Response,
  onEvent: (evt: BootstrapProgressEvent) => void,
): Promise<void> {
  if (!response.ok || !response.body) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      /* ignore */
    }
    throw new Error(detail || `Bootstrap failed (${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (!payload) continue;
      try {
        onEvent(JSON.parse(payload) as BootstrapProgressEvent);
      } catch {
        /* ignore malformed */
      }
    }
  }
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
        Authorization: `Bearer ${localStorage.getItem("shadou_token") ?? ""}`,
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
        Authorization: `Bearer ${localStorage.getItem("shadou_token") ?? ""}`,
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

  deleteConversation: (tenantId: string, userId: string) =>
    api
      .delete<{ ok: boolean; user_id: string }>(
        `/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}`,
      )
      .then((r) => r.data),

  resumeBot: (tenantId: string, userId: string) =>
    api
      .post<{ ok: boolean; user_id: string; frozen: boolean; message?: string; already_active?: boolean }>(
        `/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/resume-bot`,
      )
      .then((r) => r.data),

  handoverBot: (tenantId: string, userId: string) =>
    api
      .post<{
        ok: boolean;
        user_id: string;
        frozen: boolean;
        message?: string | null;
        already_in_handover?: boolean;
        channel_delivered?: boolean | null;
        channel_detail?: string | null;
      }>(`/tenants/${tenantId}/inbox/conversations/${encSeg(userId)}/handover-bot`)
      .then((r) => r.data),
};

export const hitlApi = {
  tickets: (tenantId: string, params?: { queue?: "open" | "archived"; limit?: number }) =>
    api.get<{ tickets: HitlTicket[]; total: number }>(`/tenants/${tenantId}/hitl/tickets`, { params }).then((r) => r.data),

  ticket: (tenantId: string, ticketId: string) =>
    api.get<HitlTicket>(`/tenants/${tenantId}/hitl/tickets/${ticketId}`).then((r) => r.data),

  reply: (tenantId: string, ticketId: string, text: string) =>
    api.post<HitlReplyOut>(`/tenants/${tenantId}/hitl/tickets/${ticketId}/reply`, { text }).then((r) => r.data),

  proposeKnowledge: (tenantId: string, ticketId: string) =>
    api.post<HitlKbProposeOut>(`/tenants/${tenantId}/hitl/tickets/${ticketId}/propose-knowledge`).then((r) => r.data),

  applyKnowledge: (tenantId: string, ticketId: string) =>
    api.post<HitlKbApplyOut>(`/tenants/${tenantId}/hitl/tickets/${ticketId}/apply-knowledge`).then((r) => r.data),

  rejectKnowledge: (tenantId: string, ticketId: string) =>
    api.post<HitlTicket>(`/tenants/${tenantId}/hitl/tickets/${ticketId}/reject-knowledge`).then((r) => r.data),

  outOfScope: (tenantId: string, ticketId: string) =>
    api.post<HitlTicket>(`/tenants/${tenantId}/hitl/tickets/${ticketId}/out-of-scope`).then((r) => r.data),
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
