import { create } from "zustand";
import type { User } from "@/types/user";
import { saveAuth, clearAuth, getToken, getStoredUser } from "@/lib/auth";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isAdmin: false,

  setAuth: (token, user) => {
    saveAuth(token, user);
    set({ token, user, isAuthenticated: true, isAdmin: user.role === "admin" });
  },

  logout: () => {
    clearAuth();
    set({ token: null, user: null, isAuthenticated: false, isAdmin: false });
  },

  hydrate: () => {
    const token = getToken();
    const user = getStoredUser();
    if (token && user) {
      set({ token, user, isAuthenticated: true, isAdmin: user.role === "admin" });
    }
  },
}));
