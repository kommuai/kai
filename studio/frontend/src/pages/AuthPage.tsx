import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import Logo from "../components/Logo";
import OAuthButton from "../components/OAuthButton";
import Spinner from "../components/Spinner";
import { authApi, API_BASE } from "../lib/api";
import { useAuthStore } from "../lib/auth";

type Tab = "signin" | "signup";

export default function AuthPage() {
  const [tab, setTab] = useState<Tab>("signin");
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      let data;
      if (tab === "signup") {
        data = await authApi.signup({ email, password, name });
      } else {
        data = await authApi.login({ email, password });
      }
      setAuth(data.access_token, data.user);
      toast.success(`Welcome, ${data.user.name || data.user.email}!`);
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Something went wrong";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* ── Left panel (hero) — hidden on mobile ── */}
      <div className="hidden lg:flex lg:w-[52%] relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-950 flex-col justify-between p-12">
        {/* Background blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
          <div className="absolute top-1/2 -right-24 h-80 w-80 rounded-full bg-brand-400/20 blur-3xl" />
          <div className="absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
        </div>

        <Logo size="md" className="relative z-10 [&_span]:text-white [&_.text-brand-600]:text-brand-200 [&_div]:bg-white/20" />

        <div className="relative z-10 max-w-md">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-sm text-brand-100">
            <Sparkles size={14} />
            Multi-tenant AI chatbot platform
          </div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">
            Configure your AI support agents in one place
          </h1>
          <p className="text-brand-200 text-lg leading-relaxed">
            Manage multiple tenants, edit knowledge bases, and deploy conversational AI — all from a single beautiful dashboard.
          </p>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-4">
          {[
            { label: "Tenants", value: "∞" },
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

      {/* ── Right panel (form) ── */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-10 bg-surface-muted">
        {/* Mobile logo */}
        <div className="mb-8 lg:hidden">
          <Logo size="lg" />
        </div>

        <div className="w-full max-w-md animate-slide-up">
          {/* Tab toggle */}
          <div className="mb-8 flex gap-1 rounded-2xl bg-gray-100 p-1">
            {(["signin", "signup"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={clsx(
                  "flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all duration-200",
                  tab === t
                    ? "bg-white text-gray-900 shadow-card"
                    : "text-gray-500 hover:text-gray-700",
                )}
              >
                {t === "signin" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">
              {tab === "signin" ? "Welcome back" : "Get started"}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              {tab === "signin"
                ? "Sign in to your Kai Studio account"
                : "Create your account and start building"}
            </p>
          </div>

          {/* OAuth buttons */}
          <div className="space-y-3 mb-6">
            <OAuthButton
              provider="google"
              href={`${API_BASE}/auth/google`}
              label={tab === "signin" ? "Continue with Google" : "Sign up with Google"}
            />
            <OAuthButton
              provider="facebook"
              href={`${API_BASE}/auth/facebook`}
              label={tab === "signin" ? "Continue with Facebook" : "Sign up with Facebook"}
            />
          </div>

          {/* Divider */}
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

          {/* Email form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === "signup" && (
              <div>
                <label className="label" htmlFor="name">Full name</label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  <input
                    id="name"
                    className="input pl-10"
                    type="text"
                    placeholder="Jane Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    autoComplete="name"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="label" htmlFor="email">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                  id="email"
                  className="input pl-10"
                  type="email"
                  placeholder="jane@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="label mb-0" htmlFor="password">Password</label>
                {tab === "signin" && (
                  <button type="button" className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                  id="password"
                  className="input pl-10 pr-10"
                  type={showPw ? "text" : "password"}
                  placeholder={tab === "signup" ? "At least 8 characters" : "••••••••"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={tab === "signup" ? "new-password" : "current-password"}
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  tabIndex={-1}
                  aria-label="Toggle password visibility"
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary btn-lg w-full mt-2"
            >
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

          {tab === "signup" && (
            <p className="mt-4 text-center text-xs text-gray-400">
              By signing up, you agree to our{" "}
              <a href="#" className="text-brand-600 hover:underline">Terms</a> and{" "}
              <a href="#" className="text-brand-600 hover:underline">Privacy Policy</a>.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
