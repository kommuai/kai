import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "./api";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => {
        localStorage.setItem("kai_token", token);
        set({ token, user, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem("kai_token");
        localStorage.removeItem("kai_user");
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    { name: "kai_auth" },
  ),
);
