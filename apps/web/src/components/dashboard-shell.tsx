"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { PlatformBrand } from "@/components/platform-brand";
import { apiFetch, clearToken } from "@/lib/api";
import type { UserInfo } from "@/types";

function OverviewIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 20V10M10 20V4M16 20v-8M22 20H2"
        stroke={active ? "#315efb" : "#667085"}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
    </svg>
  );
}

function CardIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <rect
        x="3"
        y="6"
        width="18"
        height="12"
        rx="2.5"
        stroke={active ? "#315efb" : "#667085"}
        strokeWidth="2.2"
      />
      <path d="M3 10h18" stroke={active ? "#315efb" : "#667085"} strokeWidth="2.2" />
    </svg>
  );
}

function KeyIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <circle cx="8" cy="15" r="4" stroke={active ? "#315efb" : "#667085"} strokeWidth="2.2" />
      <path
        d="M11 12 20 3M17 6h4v4"
        stroke={active ? "#315efb" : "#667085"}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
    </svg>
  );
}

function ModelIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 3 14.5 5.5l3.5-.5.5 3.5L21 11l-2.5 2.5.5 3.5-3.5.5L12 20l-2.5-2.5-3.5.5-.5-3.5L3 11l2.5-2.5-.5-3.5 3.5-.5L12 3Z"
        stroke={active ? "#315efb" : "#667085"}
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <circle cx="12" cy="11.5" r="2.5" stroke={active ? "#315efb" : "#667085"} strokeWidth="2" />
    </svg>
  );
}

function HistoryIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4M12 8v5l3 2"
        stroke={active ? "#315efb" : "#667085"}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
    </svg>
  );
}

function BillIcon({ active }: { active: boolean }) {
  return (
    <svg aria-hidden="true" className="h-6 w-6" fill="none" viewBox="0 0 24 24">
      <path
        d="M7 3h10v18l-2-1.5L13 21l-2-1.5L9 21l-2-1.5L5 21V5a2 2 0 0 1 2-2Z"
        stroke={active ? "#315efb" : "#667085"}
        strokeLinejoin="round"
        strokeWidth="2.1"
      />
      <path d="M9 8h4M9 12h4M9 16h2" stroke={active ? "#315efb" : "#667085"} strokeLinecap="round" strokeWidth="2.1" />
      <path d="M16.5 9.5h-2a1.5 1.5 0 0 0 0 3h1a1.5 1.5 0 1 1 0 3h-2M15.5 8v1.5M15.5 16.5V18" stroke={active ? "#315efb" : "#667085"} strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

const navItems = [
  { href: "/overview", label: "概览", icon: OverviewIcon },
  { href: "/recharge", label: "充值中心", icon: CardIcon },
  { href: "/api-keys", label: "API密钥", icon: KeyIcon },
  { href: "/models", label: "模型库", icon: ModelIcon },
  { href: "/usage", label: "使用历史", icon: HistoryIcon },
  { href: "/billing", label: "账单", icon: BillIcon },
];

export function DashboardShell({
  user,
  children,
}: {
  user: UserInfo;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState(user);
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileName, setProfileName] = useState(user.name);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    setCurrentUser(user);
    setProfileName(user.name);
  }, [user]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function handleProfileSave() {
    setSavingProfile(true);
    try {
      const updated = await apiFetch<UserInfo>("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ name: profileName }),
      });
      setCurrentUser(updated);
      setNotice("账户信息已更新");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordChange() {
    if (newPassword !== confirmPassword) {
      setNotice("两次输入的新密码不一致");
      return;
    }
    setSavingPassword(true);
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setNotice("密码已修改");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "修改密码失败");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f9fc] text-[var(--text-main)]">
      {notice ? (
        <div className="fixed right-8 top-24 z-50 rounded-full bg-[#172033] px-4 py-2 text-[14px] text-white shadow-lg">
          {notice}
        </div>
      ) : null}
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-8 py-1.5 xl:px-10">
          <PlatformBrand href="/overview" />

          <div className="flex items-center gap-4">
            {currentUser.role === "admin" ? (
              <Link
                className="rounded-full border border-[var(--line)] px-4 py-1.5 text-sm text-[#4d596a]"
                href="/admin"
              >
                管理后台
              </Link>
            ) : null}
            <div className="relative">
              <button
                className="flex items-center gap-3 rounded-full bg-[#eef4ff] px-4 py-1.5"
                onClick={() => setMenuOpen((prev) => !prev)}
                type="button"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#d9e7ff] text-[#315efb]">
                  <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <path
                      d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-3.314 0-6 1.79-6 4v1h12v-1c0-2.21-2.686-4-6-4Z"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
                <span className="text-[15px] font-semibold text-[#172033]">{currentUser.name}</span>
              </button>

              {menuOpen ? (
                <div className="absolute right-0 top-[58px] z-40 w-[220px] overflow-hidden rounded-[20px] border border-[#e5eaf3] bg-white shadow-[0_20px_45px_rgba(15,23,42,0.12)]">
                  <button
                    className="flex w-full items-center gap-3 border-b border-[#eef2f6] px-5 py-4 text-left text-[16px] font-semibold text-[#4d596a] hover:bg-[#f8fafc]"
                    onClick={() => {
                      setSettingsOpen(true);
                      setMenuOpen(false);
                    }}
                    type="button"
                  >
                    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <path d="M12 3 14.5 5.5l3.5-.5.5 3.5L21 11l-2.5 2.5.5 3.5-3.5.5L12 20l-2.5-2.5-3.5.5-.5-3.5L3 11l2.5-2.5-.5-3.5 3.5-.5L12 3Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="2" />
                      <circle cx="12" cy="11.5" r="2.5" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    账户设置
                  </button>
                  <button
                    className="flex w-full items-center gap-3 px-5 py-4 text-left text-[16px] font-semibold text-[#4d596a] hover:bg-[#f8fafc]"
                    onClick={() => {
                      clearToken();
                      router.replace("/login");
                    }}
                    type="button"
                  >
                    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <path d="M10 17H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4M14 16l4-4-4-4M18 12H9" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                    </svg>
                    退出登录
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <nav className="mx-auto flex max-w-[1440px] items-center gap-8 px-8 xl:px-10">
          {navItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-3 py-3.5 text-[15px] font-semibold transition ${
                  active ? "text-[#315efb]" : "text-[#4d596a] hover:text-[#172033]"
                }`}
              >
                <Icon active={active} />
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

      {settingsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#172033]/35 px-4">
          <div className="w-full max-w-[720px] rounded-[28px] bg-white shadow-[0_32px_80px_rgba(15,23,42,0.18)]">
            <div className="flex items-center justify-between border-b border-[#e5eaf3] px-8 py-6">
              <div>
                <h2 className="text-[28px] font-semibold text-[#172033]">账户设置</h2>
                <p className="mt-2 text-[15px] text-[#667085]">查看个人信息，并支持修改昵称和密码。</p>
              </div>
              <button
                className="text-[30px] leading-none text-[#98a2b3]"
                onClick={() => setSettingsOpen(false)}
                type="button"
              >
                ×
              </button>
            </div>

            <div className="grid gap-6 px-8 py-7 md:grid-cols-2">
              <section className="flex h-full flex-col rounded-[24px] border border-[#e5eaf3] bg-[#fcfdff] p-6">
                <h3 className="text-[18px] font-semibold text-[#172033]">个人信息</h3>
                <div className="mt-5 space-y-4">
                  <div className="rounded-[18px] bg-[#f8fafc] p-5">
                    <div className="text-[13px] text-[#98a2b3]">邮箱</div>
                    <div className="mt-1 text-[15px] font-semibold text-[#172033]">{currentUser.email}</div>
                  </div>
                  <div className="rounded-[18px] bg-[#f8fafc] p-5">
                    <div className="text-[13px] text-[#98a2b3]">角色</div>
                    <div className="mt-1 text-[15px] font-semibold text-[#172033]">
                      {currentUser.role === "admin" ? "管理员" : "普通用户"}
                    </div>
                  </div>
                  <label className="block">
                    <div className="mb-2 text-[14px] font-medium text-[#4d596a]">昵称</div>
                    <input
                      className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setProfileName(event.target.value)}
                      value={profileName}
                    />
                  </label>
                </div>
                <div className="mt-6">
                  <button
                    className="rounded-[14px] bg-[#315efb] px-5 py-3 text-[15px] font-semibold text-white disabled:opacity-60"
                    disabled={savingProfile}
                    onClick={() => void handleProfileSave()}
                    type="button"
                  >
                    {savingProfile ? "保存中..." : "保存信息"}
                  </button>
                </div>
              </section>

              <section className="flex h-full flex-col rounded-[24px] border border-[#e5eaf3] bg-[#fcfdff] p-6">
                <h3 className="text-[18px] font-semibold text-[#172033]">修改密码</h3>
                <div className="mt-5 space-y-4">
                  <label className="block">
                    <div className="mb-2 text-[14px] font-medium text-[#4d596a]">当前密码</div>
                    <input
                      className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setCurrentPassword(event.target.value)}
                      type="password"
                      value={currentPassword}
                    />
                  </label>
                  <label className="block">
                    <div className="mb-2 text-[14px] font-medium text-[#4d596a]">新密码</div>
                    <input
                      className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setNewPassword(event.target.value)}
                      type="password"
                      value={newPassword}
                    />
                  </label>
                  <label className="block">
                    <div className="mb-2 text-[14px] font-medium text-[#4d596a]">确认新密码</div>
                    <input
                      className="h-[50px] w-full rounded-[18px] border border-[#dbe3ef] px-4 text-[15px] text-[#172033] outline-none"
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      type="password"
                      value={confirmPassword}
                    />
                  </label>
                </div>
                <div className="mt-6">
                  <button
                    className="rounded-[14px] bg-[#172033] px-5 py-3 text-[15px] font-semibold text-white disabled:opacity-60"
                    disabled={savingPassword}
                    onClick={() => void handlePasswordChange()}
                    type="button"
                  >
                    {savingPassword ? "提交中..." : "修改密码"}
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
