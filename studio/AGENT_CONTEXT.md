# Kai Studio — agent context

**Location:** `studio/` in the Kai monorepo (`workspace/kai/studio/`). The standalone `workspace/kai-admin-ui` tree was removed after this merge.

## Session log

### 2026-05-29 — Chatwoot removed entirely
- Deleted `kai_chatwoot_studio.py`, inbox Chatwoot routes, ConversationPage Chatwoot panel, engine `kai/integrations/chatwoot/`.
- Inbox/replies use `sessions.db` + WhatsApp worker only.

### 2026-05-28 — Conversation UI: remove Memory / idle Chatwoot, tags icon, mobile sheet

- **Change:** `ConversationPage.tsx` — removed Memory card and Chatwoot card when not configured or no linked conversation (no empty “not configured” panel). Tags: chips + add form only after Tags icon (mobile sheet or desktop expand). Chatwoot on mobile: bottom sheet via message icon when `KAI_CHATWOOT_*` configured; desktop Chatwoot column only when a linked `conversation_id` exists. Tighter header, safe-area on composer, `min-h-0` scroll chain. `InboxPage` detail column `min-h-0`.
- **Validation:** `npm run build` OK.

### 2026-05-27 — UI restructure: sidebar merge + full-space layout

- **Intent:** Tenant nav (Configuration / Inbox / Contacts) merged into AppShell sidebar. TenantShell stripped to thin data wrapper. Inbox uses full-height card layout. All pages trimmed of redundant headers.
- **Files:** `components/AppShell.tsx` (tenant-aware dynamic sidebar, mobile hamburger+drawer), `components/TenantShell.tsx` (no visual layout), `pages/InboxPage.tsx` (card-based full-height two-panel), `pages/ConversationPage.tsx` (full-height flex, collapsible Chatwoot panel, mobile back bar), `pages/TenantEditorPage.tsx` (simplified header, dvh editor height), `pages/ContactsPage.tsx` (removed redundant title).
- **Validation:** `npm run build` OK, zero lint errors.
- **Key behavior:** AppShell reads slug from URL via regex; when in `/t/:slug/*`, shows tenant avatar + name + nav; auto-closes sidebar on navigation. InboxPage height: `calc(100dvh - 7rem)` mobile, `calc(100dvh - 3rem)` md, `calc(100dvh - 4rem)` lg.

### 2026-05-27 — Chatwoot Phase A+B (Studio inbox)

- **Backend:** `kai_chatwoot_studio.py` worker actions: `get_meta`, `set_status`, `private_note`, `set_labels`, `human_handover`, `resume_bot`, `account_labels` (empty list when Chatwoot not configured). `inbox_router.py` routes for meta, status, private note, labels, handover, resume; `ConversationDetailOut.chatwoot_conversation_id` from session JSON.
- **Frontend:** `api.ts` Chatwoot helpers; `ConversationPage` violet “Chatwoot” card (status, snooze `datetime-local`, handover/resume, private note, labels + replace warning). Query invalidation includes `cwMeta`.
- **Runtime:** `kai/integrations/chatwoot/client.py` — `set_conversation_status`, `create_private_note`, label GET/POST, `list_account_labels`, etc.
- **Fix:** Restored broken `ConversationPage.tsx` block (`conversation` query + `invalidateTags` function) after a merge left orphaned invalidation lines.
- **Validation:** `npm run build`; `python3 -c "from main import app"`.

### 2026-05-27 — Inbox agent replies

- **Studio reply:** `POST /tenants/{id}/inbox/conversations/{user_id}/reply` runs `backend/kai_reply.py` with tenant `KAI_HOME` — appends `agent` role to sessions.db, optional Chatwoot outbound when `chatwoot_conversation_id` is on the session.
- **Kai runtime:** `kai_service.pre_router` persists `chatwoot_conversation_id` from webhook payloads into session JSON for later Studio delivery.
- **Frontend:** reply composer on `ConversationPage` (green agent bubbles).

### 2026-05-27 — Add tenant only from dashboard

- Removed global “New tenant” entry points: `AppShell` sidebar link and dashboard header button. Creating a tenant remains via dashboard empty state + dashed “Add tenant” card in the grid (`DashboardPage.tsx`).

### 2026-05-27 — Inbox, Conversations & Contacts (Kai Studio)

- **Intent:** Read-only inbox/contacts from tenant `sessions.db`; contact tags in `admin.db` (`contact_tags`).
- **Backend:** `database.py` migration + `models.ContactTag`; `routers/inbox_router.py` (mounted in `main.py`); `schemas.py` inbox/contact models. Endpoints under `/tenants/{tenant_id}/inbox/*` and `/tenants/{tenant_id}/contacts/*`. Returns **503** if sessions DB missing.
- **Frontend:** `TenantShell.tsx` (nav: Configuration, Inbox, Contacts); `InboxPage` (two-panel on `lg`, nested `<Outlet context={{ tenant }} />`); `ConversationPage`, `ContactsPage`; `api.ts` `inboxApi` + `contactsApi`; nested `/t/:slug/inbox/:userId` under `InboxPage`; `TenantEditorPage` uses `useOutletContext` to avoid duplicate tenant fetch.
- **Validation:** `npm run build` (frontend) OK; `python -c "from main import app"` OK.

### 2026-05-27 — Link Kommu tenant to `yuanting@kommu.ai`

- Inserted SQLite `tenants` row: `slug=kommu`, `workspace_home=/home/ting/workspace/kai-tenant-kommu`, owner = user with email `yuanting@kommu.ai`.
- **Next agent:** For other users, repeat with their `users.id` or add an admin API; avoid reusing slug `kommu` (unique).
