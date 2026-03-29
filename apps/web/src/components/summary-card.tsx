import type { ReactNode } from "react";

export function SummaryCard({
  title,
  value,
  extra,
  tone = "default",
}: {
  title: string;
  value: ReactNode;
  extra?: ReactNode;
  tone?: "default" | "brand" | "green";
}) {
  const toneClass =
    tone === "brand"
      ? "bg-[var(--brand-soft)]"
      : tone === "green"
        ? "bg-[var(--green-soft)]"
        : "bg-white";

  return (
    <div className={`rounded-[28px] border border-[var(--line)] ${toneClass} p-6 shadow-[var(--card-shadow)]`}>
      <div className="text-sm text-[var(--text-muted)]">{title}</div>
      <div className="mt-4 text-4xl font-semibold tracking-tight">{value}</div>
      {extra ? <div className="mt-3 text-sm text-[var(--text-muted)]">{extra}</div> : null}
    </div>
  );
}
