import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { authApi } from "../lib/api";
import { useAuthStore } from "../lib/auth";
import Spinner from "../components/Spinner";

export default function OAuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      toast.error("OAuth failed — no token received");
      navigate("/login");
      return;
    }
    // Store token then fetch user info
    localStorage.setItem("kai_token", token);
    authApi
      .me()
      .then((user) => {
        setAuth(token, user);
        toast.success(`Welcome, ${user.name || user.email}!`);
        navigate("/dashboard");
      })
      .catch(() => {
        toast.error("Failed to verify token");
        navigate("/login");
      });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-muted">
      <div className="text-center space-y-4">
        <Spinner size="lg" className="text-brand-600 mx-auto" />
        <p className="text-gray-500 text-sm">Finishing sign in…</p>
      </div>
    </div>
  );
}
