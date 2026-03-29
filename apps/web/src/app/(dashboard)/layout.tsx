"use client";

import { AuthGuard } from "@/components/auth-guard";
import { DashboardShell } from "@/components/dashboard-shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      {({ user }) => <DashboardShell user={user}>{children}</DashboardShell>}
    </AuthGuard>
  );
}
