import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  LogOut,
  ChevronDown,
  ChevronLeft,
  Menu,
  X,
  Inbox,
  Users,
  SlidersHorizontal,
  ClipboardCheck,
  Trophy,
} from "lucide-react";
import LevelBadge from "./LevelBadge";
import clsx from "clsx";
import Logo from "./Logo";
import { useAuthStore } from "../lib/auth";
import { tenantsApi } from "../lib/api";
import WhatsAppDeliveryBadge from "./WhatsAppDeliveryBadge";

const TENANT_COLORS = [
  "from-violet-500 to-purple-600",
  "from-blue-500 to-cyan-600",
  "from-emerald-500 to-teal-600",
  "from-orange-500 to-amber-600",
  "from-pink-500 to-rose-600",
];

function tenantColor(slug: string) {
  const idx = slug.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % TENANT_COLORS.length;
  return TENANT_COLORS[idx];
}

function Avatar({ name, url }: { name: string; url?: string }) {
  if (url) return <img src={url} alt={name} className="h-8 w-8 rounded-full object-cover" />;
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  return (
    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-xs font-bold shrink-0">
      {initials}
    </div>
  );
}

const navCls = ({ isActive }: { isActive: boolean }) =>
  clsx(
    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150",
    isActive
      ? "bg-brand-50 text-brand-700"
      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
  );

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // Detect tenant context from URL
  const slugMatch = location.pathname.match(/^\/t\/([^/]+)/);
  const tenantSlug = slugMatch?.[1] ?? null;

  // Close sidebar + profile on navigation
  useEffect(() => {
    setSidebarOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  const { data: currentTenant } = useQuery({
    queryKey: ["tenantBySlug", tenantSlug],
    queryFn: () => tenantsApi.getBySlug(tenantSlug!),
    enabled: !!tenantSlug,
    staleTime: 60_000,
  });

  const { data: channelStatus } = useQuery({
    queryKey: ["tenant-channels", currentTenant?.id],
    queryFn: () => tenantsApi.channels(currentTenant!.id),
    enabled: !!currentTenant?.id,
    refetchInterval: 20_000,
  });

  function handleLogout() {
    logout();
    navigate("/login");
  }

  // ── Sidebar nav content ──────────────────────────────────────────────────
  const navContent = tenantSlug ? (
    <div className="space-y-0.5">
      <Link
        to="/dashboard"
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-xl transition-all mb-2"
      >
        <ChevronLeft size={15} />
        <span>All agents</span>
      </Link>

      {/* Tenant identity */}
      <div className="px-3 py-2.5 mb-1">
        <div className="flex items-center gap-3">
          <div
            className={`h-9 w-9 rounded-xl bg-gradient-to-br ${tenantColor(tenantSlug)} flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm`}
          >
            {(currentTenant?.display_name ?? tenantSlug).charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-gray-900 leading-tight truncate">
              {currentTenant?.display_name ?? tenantSlug}
            </div>
            <div className="text-[10px] font-mono text-gray-400 truncate mt-0.5">{tenantSlug}</div>
            {currentTenant?.training_summary && (
              <div className="mt-2">
                <LevelBadge
                  level={currentTenant.training_summary.current_level}
                  title={currentTenant.training_summary.current_level_title}
                  emoji={currentTenant.training_summary.current_level_emoji}
                  progress={currentTenant.training_summary.progress_to_next}
                  size="sm"
                />
              </div>
            )}
            {channelStatus?.whatsapp_baileys && (
              <div className="mt-1.5">
                <WhatsAppDeliveryBadge wa={channelStatus.whatsapp_baileys} size="xs" />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="h-px bg-gray-100 mx-1 mb-2" />

      <NavLink to={`/t/${tenantSlug}/inbox`} className={navCls}>
        <Inbox size={17} />
        Inbox
      </NavLink>
      <NavLink to={`/t/${tenantSlug}/review`} className={navCls}>
        <ClipboardCheck size={17} />
        Review
      </NavLink>
      <NavLink to={`/t/${tenantSlug}/academy`} className={navCls}>
        <Trophy size={17} />
        Academy
      </NavLink>
      <NavLink to={`/t/${tenantSlug}/configuration`} end className={navCls}>
        <SlidersHorizontal size={17} />
        Configuration
      </NavLink>
      <NavLink to={`/t/${tenantSlug}/contacts`} className={navCls}>
        <Users size={17} />
        Contacts
      </NavLink>
    </div>
  ) : (
    <NavLink to="/dashboard" className={navCls}>
      <LayoutDashboard size={17} />
      Dashboard
    </NavLink>
  );

  // ── Sidebar shell ────────────────────────────────────────────────────────
  const sidebar = (
    <nav className="flex flex-col h-full">
      <div className="p-5 border-b border-gray-100 shrink-0">
        <Link to="/dashboard">
          <Logo size="sm" />
        </Link>
      </div>

      <div className="flex-1 p-3 overflow-y-auto">{navContent}</div>

      {/* Profile footer */}
      <div className="p-4 border-t border-gray-100 shrink-0">
        <div className="relative">
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex w-full items-center gap-3 rounded-xl p-2.5 hover:bg-gray-100 transition-all duration-150"
          >
            <Avatar name={user?.name || "User"} url={user?.avatar_url} />
            <div className="flex-1 min-w-0 text-left">
              <div className="text-sm font-semibold text-gray-900 truncate">{user?.name || "Account"}</div>
              <div className="text-xs text-gray-400 truncate">{user?.email}</div>
            </div>
            <ChevronDown
              size={14}
              className={clsx("text-gray-400 transition-transform shrink-0", profileOpen && "rotate-180")}
            />
          </button>

          {profileOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-1 bg-white rounded-2xl border border-gray-100 shadow-card-xl py-1 z-50 animate-fade-in">
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut size={16} />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );

  const isTenantRoute = Boolean(tenantSlug);
  // Inbox/conversation only — Configuration scrolls on mobile so the editor pane keeps height.
  const isFullHeightRoute =
    isTenantRoute && location.pathname.startsWith(`/t/${tenantSlug}/inbox`);

  return (
    <div className="h-dvh flex overflow-hidden bg-surface-muted">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-64 flex-col bg-white border-r border-gray-100 fixed inset-y-0 left-0 z-30">
        {sidebar}
      </aside>

      {/* ── Mobile sidebar overlay ── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative w-72 max-w-[85vw] bg-white h-full border-r border-gray-100 flex flex-col animate-slide-up">
            <button
              onClick={() => setSidebarOpen(false)}
              className="absolute top-4 right-4 btn-ghost btn-icon text-gray-500 z-10"
              aria-label="Close menu"
            >
              <X size={20} />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-0 min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden shrink-0 z-20 bg-white border-b border-gray-100 flex items-center justify-between px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="btn-ghost btn-icon text-gray-600"
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>

          <div className="flex-1 text-center">
            {tenantSlug ? (
              <span className="text-sm font-semibold text-gray-900 truncate">
                {currentTenant?.display_name ?? tenantSlug}
              </span>
            ) : (
              <Logo size="sm" />
            )}
          </div>

          <Avatar name={user?.name || "User"} url={user?.avatar_url} />
        </header>

        <main
          className={clsx(
            "flex-1 min-h-0 min-w-0 flex flex-col max-w-7xl w-full mx-auto",
            isFullHeightRoute ? "p-0 sm:p-4 md:p-6 lg:p-8 overflow-hidden" : "p-4 sm:p-6 lg:p-8 overflow-hidden",
          )}
        >
          <div
            className={clsx(
              "flex-1 min-h-0 min-w-0",
              isFullHeightRoute
                ? "flex flex-col overflow-hidden"
                : "overflow-y-auto overflow-x-hidden",
            )}
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
