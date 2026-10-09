"use client";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { User } from "@supabase/supabase-js";
import { getSupabase, isAuthConfigured } from "@/lib/auth/supabase";
import { clearDraft } from "@/lib/resume-builder";
export { displayName } from "@/lib/auth/user";

export type AuthStatus = "disabled" | "loading" | "signed-out" | "signed-in";
type AuthState = {
  status: AuthStatus;
  user: User | null;
  error?: string;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState>({
  status: "disabled",
  user: null,
  signIn: async () => {},
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>(isAuthConfigured ? "loading" : "disabled");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) return;
    let alive = true;
    const apply = (session: { user: User } | null) => {
      if (!alive) return;
      setUser(session?.user ?? null);
      setStatus(session ? "signed-in" : "signed-out");
    };
    void supabase.auth.getSession().then(({ data }) => apply(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, session) => apply(session));
    return () => {
      alive = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      status,
      user,
      error,
      async signIn() {
        const supabase = getSupabase();
        if (!supabase) return;
        setError(undefined);
        const { error: failure } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: { redirectTo: `${window.location.origin}/auth/callback` },
        });
        if (failure) setError("Google sign-in could not start. Try again in a moment.");
      },
      async signOut() {
        await getSupabase()?.auth.signOut();
        queryClient.clear(); // nothing from the previous person stays in memory
        clearDraft(); // nor an unsent resume draft saved in this browser
      },
    }),
    [status, user, error, queryClient],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
