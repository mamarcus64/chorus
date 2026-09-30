/* The session hook and the provider share one context, so they live in this file. */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type User } from "./api";

interface AuthValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ project, children }: { project: string; children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const loading = loadedFor !== project;

  async function refresh() {
    try {
      setUser(await api.me(project));
    } catch {
      setUser(null);
    } finally {
      setLoadedFor(project);
    }
  }

  useEffect(() => {
    let cancelled = false;
    api.me(project)
      .then((next) => {
        if (!cancelled) setUser(next);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoadedFor(project);
      });
    return () => {
      cancelled = true;
    };
  }, [project]);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth outside AuthProvider");
  return value;
}
