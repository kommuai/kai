import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { authApi } from "../lib/api";
import { formatApiError } from "../lib/apiErrors";
import { useAuthStore } from "../lib/auth";
import { finishAuthAndNavigate } from "../lib/invite";
import Spinner from "../components/Spinner";

export default function OAuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    const oauthError = params.get("error") || params.get("error_description");
    if (oauthError) {
      toast.error(oauthError);
      navigate("/login", { replace: true });
      return;
    }

    const token = params.get("token");
    if (!token) {
      toast.error("Sign-in was cancelled or failed. Please try again.");
      navigate("/login", { replace: true });
      return;
    }

    localStorage.setItem("kai_token", token);
    authApi
      .me()
      .then((user) => {
        setAuth(token, user);
        toast.success(`Welcome, ${user.name || user.email}!`);
        return finishAuthAndNavigate(navigate);
      })
      .catch((err) => {
        const msg = formatApiError(err, "Could not verify your sign-in. Please try again.");
        toast.error(msg);
        localStorage.removeItem("kai_token");
        navigate("/login", { replace: true });
      });
  }, [params, navigate, setAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted">
      <div className="text-center space-y-4">
        <Spinner size="lg" className="text-brand-600 mx-auto" />
        <p className="text-gray-500 text-sm">Finishing sign in…</p>
      </div>
    </div>
  );
}
