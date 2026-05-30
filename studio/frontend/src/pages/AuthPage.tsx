import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, Sparkles, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import Logo from "../components/Logo";
import OAuthButton from "../components/OAuthButton";
import Spinner from "../components/Spinner";
import { authApi, API_BASE } from "../lib/api";
import { formatApiError } from "../lib/apiErrors";
import { useAuthStore } from "../lib/auth";
import { finishAuthAndNavigate, setPendingInviteToken } from "../lib/invite";

type Tab = "signin" | "signup";
type FieldErrors = { email?: string; password?: string; name?: string; terms?: string };

function validateEmail(email: string): string | undefined {
  const t = email.trim();
  if (!t) return "Email is required.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t)) return "Enter a valid email address.";
  return undefined;
}

function validatePassword(password: string, signup: boolean): string | undefined {
  if (!password) return "Password is required.";
  if (signup && password.length < 8) return "Password must be at least 8 characters.";
  return undefined;
}

export default function AuthPage() {
  const [tab, setTab] = useState<Tab>("signin");
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [showForgotHint, setShowForgotHint] = useState(false);

  const { data: providers } = useQuery({
    queryKey: ["auth-providers"],
    queryFn: () => authApi.providers(),
    staleTime: 60_000,
  });

  const googleEnabled = providers?.google ?? true;
  const facebookEnabled = providers?.facebook ?? true;
  const anyOAuth = googleEnabled || facebookEnabled;

  useEffect(() => {
    setFormError(null);
    setFieldErrors({});
    setShowForgotHint(false);
  }, [tab]);

  useEffect(() => {
    const st = location.state as { inviteEmail?: string; inviteToken?: string } | null;
    if (st?.inviteToken) setPendingInviteToken(st.inviteToken);
    if (st?.inviteEmail) {
      setEmail(st.inviteEmail);
      setTab("signup");
    }
  }, [location.state]);

  function switchTab(t: Tab) {
    setTab(t);
  }

  function validateForm(): boolean {
    const errs: FieldErrors = {
      email: validateEmail(email),
      password: validatePassword(password, tab === "signup"),
    };
    if (tab === "signup") {
      if (!name.trim()) errs.name = "Name is required.";
      if (!acceptedTerms) errs.terms = "You must accept the Terms and Privacy Policy.";
    }
    setFieldErrors(errs);
    return !Object.values(errs).some(Boolean);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!validateForm()) return;

    const trimmedEmail = email.trim().toLowerCase();
    setLoading(true);
    try {
      const data =
        tab === "signup"
          ? await authApi.signup({ email: trimmedEmail, password, name: name.trim() })
          : await authApi.login({ email: trimmedEmail, password });

      setAuth(data.access_token, data.user);
      toast.success(`Welcome, ${data.user.name || data.user.email}!`);
      await finishAuthAndNavigate(navigate);
    } catch (err: unknown) {
      const msg = formatApiError(
        err,
        tab === "signin" ? "Sign in failed. Check your email and password." : "Could not create your account.",
      );
      setFormError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  const inputErrorCls = "border-red-300 focus:border-red-500 focus:ring-red-500/30";

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-[52%] relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-950 flex-col justify-between p-12">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute top-1/2 -right-24 h-80 w-80 rounded-full bg-brand-400/20 blur-3xl" />
          <div className="absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
        </div>

        <Logo size="md" className="relative z-10 [&_span]:text-white [&_.text-brand-600]:text-brand-200 [&_div]:bg-white/20" />

        <div className="relative z-10 max-w-md">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-sm text-brand-100">
            <Sparkles size={14} />
            AI support agent platform
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight">
            Configure your AI support agents in one place
          </h1>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-4">
          {[
            { label: "Agents", value: "∞" },
            { label: "Languages", value: "EN/BM" },
            { label: "Channels", value: "WA +" },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-2xl bg-white/10 p-4 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">{value}</div>
              <div className="text-sm text-brand-200 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-10 bg-surface-muted">
        <div className="mb-8 lg:hidden">
          <Logo size="lg" />
        </div>

        <div className="w-full max-w-md animate-slide-up">
          <div className="mb-8 flex gap-1 rounded-2xl bg-gray-100 p-1">
            {(["signin", "signup"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                className={clsx(
                  "flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all duration-200",
                  tab === t ? "bg-white text-gray-900 shadow-card" : "text-gray-500 hover:text-gray-700",
                )}
              >
                {t === "signin" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {tab === "signin" ? "Welcome back" : "Get started"}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              {tab === "signin"
                ? "Sign in to your Kai Studio account"
                : "Create your account and start building"}
            </p>
          </div>

          {formError && (
            <div
              role="alert"
              className="mb-6 flex gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              <AlertCircle size={18} className="shrink-0 mt-0.5" />
              <p>{formError}</p>
            </div>
          )}

          {anyOAuth && (
            <>
              <div className="space-y-3 mb-6">
                {googleEnabled && (
                  <OAuthButton
                    provider="google"
                    href={`${API_BASE}/auth/google`}
                    label={tab === "signin" ? "Continue with Google" : "Sign up with Google"}
                  />
                )}
                {facebookEnabled && (
                  <OAuthButton
                    provider="facebook"
                    href={`${API_BASE}/auth/facebook`}
                    label={tab === "signin" ? "Continue with Facebook" : "Sign up with Facebook"}
                  />
                )}
              </div>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-surface-muted px-3 text-xs text-gray-400 font-medium">
                    or continue with email
                  </span>
                </div>
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {tab === "signup" && (
              <div>
                <label className="label" htmlFor="name">
                  Full name
                </label>
                <div className="relative">
                  <User
                    size={16}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                  />
                  <input
                    id="name"
                    className={clsx("input pl-10", fieldErrors.name && inputErrorCls)}
                    type="text"
                    placeholder="Jane Smith"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (fieldErrors.name) setFieldErrors((p) => ({ ...p, name: undefined }));
                    }}
                    autoComplete="name"
                    aria-invalid={!!fieldErrors.name}
                    aria-describedby={fieldErrors.name ? "name-error" : undefined}
                  />
                </div>
                {fieldErrors.name && (
                  <p id="name-error" className="mt-1 text-xs text-red-600">
                    {fieldErrors.name}
                  </p>
                )}
              </div>
            )}

            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <div className="relative">
                <Mail
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                />
                <input
                  id="email"
                  className={clsx("input pl-10", fieldErrors.email && inputErrorCls)}
                  type="email"
                  placeholder="jane@company.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (fieldErrors.email) setFieldErrors((p) => ({ ...p, email: undefined }));
                    if (formError) setFormError(null);
                  }}
                  autoComplete="email"
                  aria-invalid={!!fieldErrors.email}
                  aria-describedby={fieldErrors.email ? "email-error" : undefined}
                />
              </div>
              {fieldErrors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="label mb-0" htmlFor="password">
                  Password
                </label>
                {tab === "signin" && (
                  <button
                    type="button"
                    className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                    onClick={() => setShowForgotHint((v) => !v)}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              {showForgotHint && tab === "signin" && (
                <p className="mb-2 text-xs text-gray-600 rounded-lg bg-gray-100 px-3 py-2">
                  Password reset is not available in-app yet. If you signed up with Google or Facebook, use those
                  buttons above. Otherwise contact your workspace administrator.
                </p>
              )}
              <div className="relative">
                <Lock
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                />
                <input
                  id="password"
                  className={clsx("input pl-10 pr-10", fieldErrors.password && inputErrorCls)}
                  type={showPw ? "text" : "password"}
                  placeholder={tab === "signup" ? "At least 8 characters" : "Your password"}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (fieldErrors.password) setFieldErrors((p) => ({ ...p, password: undefined }));
                    if (formError) setFormError(null);
                  }}
                  autoComplete={tab === "signup" ? "new-password" : "current-password"}
                  aria-invalid={!!fieldErrors.password}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {fieldErrors.password && (
                <p id="password-error" className="mt-1 text-xs text-red-600">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {tab === "signup" && (
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-1 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                  checked={acceptedTerms}
                  onChange={(e) => {
                    setAcceptedTerms(e.target.checked);
                    if (fieldErrors.terms) setFieldErrors((p) => ({ ...p, terms: undefined }));
                  }}
                />
                <span className="text-xs text-gray-600 leading-relaxed">
                  I agree to the{" "}
                  <Link to="/terms" className="text-brand-600 hover:underline font-medium" target="_blank">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link to="/privacy" className="text-brand-600 hover:underline font-medium" target="_blank">
                    Privacy Policy
                  </Link>
                  .
                </span>
              </label>
            )}
            {fieldErrors.terms && <p className="text-xs text-red-600 -mt-2">{fieldErrors.terms}</p>}

            <button type="submit" disabled={loading} className="btn-primary btn-lg w-full mt-2">
              {loading ? (
                <Spinner size="sm" className="text-white" />
              ) : (
                <>
                  {tab === "signin" ? "Sign in" : "Create account"}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
