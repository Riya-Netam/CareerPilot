import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, ReactNode, useContext, useMemo } from "react";
import { api, ApiError } from "../services/api";
import type { User } from "../types";

export interface AuthState { user: User | null; loading: boolean; refresh: () => Promise<void>; signOut: () => Promise<void> }
export const AuthContext = createContext<AuthState>({ user: null, loading: false, refresh: async () => {}, signOut: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["me"],
    queryFn: async () => { try { return await api.get<User>("/auth/me"); } catch (e) { if (e instanceof ApiError && [401, 403].includes(e.status)) return null; throw e; } },
    retry: false, staleTime: 60_000,
  });
  const value = useMemo<AuthState>(() => ({
    user: q.data ?? null, loading: q.isLoading,
    refresh: async () => { await qc.invalidateQueries({ queryKey: ["me"] }); },
    signOut: async () => { try { await api.post("/auth/logout"); } finally { qc.clear(); qc.setQueryData(["me"], null); } },
  }), [q.data, q.isLoading, qc]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
