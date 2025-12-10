import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient } from "../api/client";
import type { User } from "../api/auth";
import type { AuthState } from "../types/auth.types";

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await apiClient.auth.login(email, password);
          // Fetch full user info including role and status
          const fullUser = await apiClient.auth.me();
          set({
            user: { ...response.user, ...fullUser },
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      signup: async (name: string, email: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await apiClient.auth.signup(name, email, password);
          // Fetch full user info including role and status
          const fullUser = await apiClient.auth.me();
          set({
            user: { ...response.user, ...fullUser },
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      fetchUser: async () => {
        try {
          const user = await apiClient.auth.me();
          set({ user });
        } catch (error) {
          // If fetch fails, user might not be authenticated
          set({ user: null });
        }
      },

      logout: async () => {
        try {
          await apiClient.auth.logout();
        } catch (error) {
          console.error("Logout error:", error);
        } finally {
          set({ user: null });
          // prevent BFCache
          if (typeof window !== "undefined") {
            window.location.replace("/login");
          }
        }
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
