import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "@/lib/api/client";

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  signup: (name: string, username: string, email: string, password: string)=> Promise<void>;
  updateProfile: (data: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          // OAuth2PasswordRequestForm expects form-encoded 'username' and 'password'
          const body = new URLSearchParams();
          body.set("username", username);
          body.set("password", password);

          const res = await fetch(
            `${apiClient['baseUrl'] || ""}/auth/login`,
            {
              method: "POST",
              headers: { "Content-Type": "application/x-www-form-urlencoded" },
              body: body.toString(),
            },
          );

          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Login failed" }));
            throw new Error(JSON.stringify(err));
          }

          const data = await res.json();
          const token = data.access_token as string | undefined;
          if (!token) throw new Error("No access token returned from server");

          // Store token in ApiClient and in persisted state
          apiClient.setToken(token);

          const user: User = { id: "", email: "", name: username };
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      signup: async (name: string, username: string, email: string, password: string) => {
        // Call backend signup
        set({ isLoading: true });
        try {
          const res = await fetch(`${apiClient['baseUrl'] || ""}/auth/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, username, email, password }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Signup failed" }));
            throw new Error(JSON.stringify(err));
          }
          set({ isLoading: false });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        // clear token and state
        apiClient.setToken(null);
        set({ user: null, isAuthenticated: false });
      },

      updateProfile: (data: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...data } : null,
        }));
      },
    }),
    {
      name: "auth-storage",
    },
  ),
);
