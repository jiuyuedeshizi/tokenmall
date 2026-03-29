"use client";

import { useEffect, useEffectEvent, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { apiFetch, clearToken, getToken } from "@/lib/api";
import type { UserInfo } from "@/types";

type Props = {
  children: (context: { user: UserInfo }) => React.ReactNode;
};

export function AuthGuard({ children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useEffectEvent(async () => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    try {
      const me = await apiFetch<UserInfo>("/auth/me", undefined, token);
      setUser(me);
      if (pathname.startsWith("/admin") && me.role !== "admin") {
        router.replace("/overview");
      }
    } catch {
      clearToken();
      router.replace("/login");
    } finally {
      setLoading(false);
    }
  });

  useEffect(() => {
    void refreshUser();
  }, [pathname]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--page-bg)] text-[var(--text-main)]">
        正在加载控制台...
      </div>
    );
  }

  return <>{children({ user })}</>;
}
