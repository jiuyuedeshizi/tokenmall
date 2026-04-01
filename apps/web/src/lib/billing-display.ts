type BillingItem = {
  status?: string;
  billing_quantity?: number;
  billing_unit?: string;
  amount?: string | number;
};

export function formatBillingQuantity(item: BillingItem) {
  if (item.status && item.status !== "success") {
    return "-";
  }
  const quantity = item.billing_quantity ?? 0;
  if (quantity <= 0) {
    return "-";
  }
  switch ((item.billing_unit ?? "token").trim().toLowerCase()) {
    case "image":
      return `${quantity.toLocaleString()} 张`;
    case "second":
      return `${quantity.toLocaleString()} 秒`;
    case "char":
      return `${quantity.toLocaleString()} 字符`;
    default:
      return `${quantity.toLocaleString()} tokens`;
  }
}

export function formatBillingAmount(amount?: string | number, status?: string) {
  if (status && status !== "success") {
    return "-";
  }
  const numeric = typeof amount === "number" ? amount : Number(amount ?? 0);
  if (!Number.isFinite(numeric)) {
    return String(amount ?? "-");
  }
  const normalized = numeric.toFixed(6);
  const [integer, fraction] = normalized.split(".");
  const trimmed = fraction.replace(/0+$/, "");
  return `${integer}.${trimmed.length >= 4 ? trimmed : fraction.slice(0, 4)}`;
}
