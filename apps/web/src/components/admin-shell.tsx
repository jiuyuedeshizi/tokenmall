"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { PlatformBrand } from "@/components/platform-brand";
import { clearToken } from "@/lib/api";
import type { UserInfo } from "@/types";

const adminNavItems = [
  { href: "/admin", label: "平台概览" },
  { href: "/admin/users", label: "用户管理" },
  { href: "/admin/orders", label: "订单管理" },
  { href: "/admin/refunds", label: "退款管理" },
  { href: "/admin/ledger", label: "账务管理" },
  { href: "/admin/api-keys", label: "API Key" },
  { href: "/admin/models", label: "模型管理" },
  { href: "/admin/usage", label: "使用记录" },
];

export function AdminShell({
  user,
  children,
}: {
  user: UserInfo;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#f7f9fc] text-[#172033]">
      <header className="border-b border-[#e2e8f0] bg-white">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-8 py-0.5 xl:px-10">
          <PlatformBrand href="/admin" />

          <div className="flex items-center gap-3">
            <Link
              className="rounded-full border border-[#dbe3ef] px-4 py-1.5 text-[14px] font-medium text-[#4d596a]"
              href="/overview"
            >
              返回前台
            </Link>
            <div className="flex items-center gap-3 rounded-full bg-[#eef4ff] px-4 py-1.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#d9e7ff] text-[#315efb]">
                <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <path
                    d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-3.314 0-6 1.79-6 4v1h12v-1c0-2.21-2.686-4-6-4Z"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                </svg>
              </div>
              <span className="text-[15px] font-semibold text-[#172033]">{user.name}</span>
            </div>
            <button
              className="rounded-full border border-[#dbe3ef] px-4 py-1.5 text-[14px] font-medium text-[#4d596a]"
              onClick={() => {
                clearToken();
                router.replace("/login");
              }}
              type="button"
            >
              退出
            </button>
          </div>
        </div>

        <nav className="mx-auto -mt-1 flex max-w-[1440px] items-center gap-8 px-8 xl:px-10">
          {adminNavItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                className={`relative py-3 text-[15px] font-semibold ${
                  active ? "text-[#315efb]" : "text-[#4d596a]"
                }`}
                href={item.href}
              >
                {item.label}
                <span
                  className={`absolute bottom-0 left-0 h-[3px] rounded-full bg-[#315efb] transition-all ${
                    active ? "w-full" : "w-0"
                  }`}
                />
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-[1440px] px-8 py-8 xl:px-10">{children}</main>
    </div>
  );
}
