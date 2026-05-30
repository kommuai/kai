import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Mail, Users, AlertCircle } from "lucide-react";
import Logo from "../components/Logo";
import Spinner from "../components/Spinner";
import { tenantsApi } from "../lib/api";
import { acceptInviteToken, setPendingInviteToken } from "../lib/invite";
import { useAuthStore } from "../lib/auth";

export default function InvitePage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => !!s.token);
  const user = useAuthStore((s) => s.user);
  const [accepting, setAccepting] = useState(false);
  const acceptStarted = useRef(false);

  useEffect(() => {
    if (token) setPendingInviteToken(token);
  }, [token]);

  const { data: preview, isLoading, error } = useQuery({
    queryKey: ["invite-preview", token],
    queryFn: () => tenantsApi.invitePreview(token!),
    enabled: !!token,
    retry: false,
  });

  useEffect(() => {
    if (!token || !isAuthed || !preview || preview.status !== "pending" || preview.expired) return;
    if (user && user.email.toLowerCase() !== preview.email.toLowerCase()) return;
    if (acceptStarted.current) return;
    acceptStarted.current = true;

    setAccepting(true);
    acceptInviteToken(token, navigate).finally(() => setAccepting(false));
  }, [token, isAuthed, preview, user, navigate]);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <p className="text-sm text-gray-500">Invalid invite link.</p>
      </div>
    );
  }

  if (isLoading || (isAuthed && accepting)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <Spinner className="text-brand-600" />
        <p className="text-sm text-gray-500">Loading invite…</p>
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <Logo size="sm" />
        <p className="mt-6 text-sm text-red-600">This invite link is invalid or has expired.</p>
        <Link to="/login" className="mt-4 text-sm text-brand-600 hover:underline">
          Go to sign in
        </Link>
      </div>
    );
  }

  const emailMismatch =
    isAuthed && user && user.email.toLowerCase() !== preview.email.toLowerCase();

  if (preview.status !== "pending" || preview.expired) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <Logo size="sm" />
        <p className="mt-6 text-sm text-gray-600">
          {preview.expired ? "This invite has expired." : `This invite is ${preview.status}.`}
        </p>
        {isAuthed ? (
          <Link to="/dashboard" className="mt-4 text-sm text-brand-600 hover:underline">
            Go to dashboard
          </Link>
        ) : (
          <Link to="/login" className="mt-4 text-sm text-brand-600 hover:underline">
            Sign in
          </Link>
        )}
      </div>
    );
  }

  if (emailMismatch) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 max-w-md text-center">
        <Logo size="sm" />
        <div className="mt-6 flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-xl p-4">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p>
            You are signed in as <strong>{user?.email}</strong>, but this invite is for{" "}
            <strong>{preview.email}</strong>. Sign out and use the invited email.
          </p>
        </div>
        <Link to="/dashboard" className="mt-4 text-sm text-brand-600 hover:underline">
          Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-surface-muted">
      <div className="w-full max-w-md card p-8 space-y-6">
        <Logo size="sm" className="justify-center" />
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 mx-auto">
            <Users size={22} />
          </div>
          <h1 className="text-lg font-semibold text-gray-900">Join {preview.tenant_name}</h1>
          <p className="text-sm text-gray-500">
            You have been invited to collaborate on this agent in Kai Studio.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-xl px-3 py-2">
          <Mail size={16} className="text-gray-400 shrink-0" />
          <span className="truncate">{preview.email}</span>
        </div>
        {isAuthed ? (
          <p className="text-sm text-center text-gray-500">Accepting invite…</p>
        ) : (
          <div className="flex flex-col gap-2">
            <Link
              to="/login"
              state={{ inviteEmail: preview.email, inviteToken: token }}
              className="btn-primary w-full text-center"
            >
              Create account or sign in
            </Link>
            <p className="text-[11px] text-gray-400 text-center">
              Use <span className="font-mono">{preview.email}</span> so the invite matches your account.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
