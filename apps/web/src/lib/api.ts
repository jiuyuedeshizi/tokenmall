"use client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type ApiError = {
  detail?:
    | string
    | ApiValidationErrorItem[];
};

export type ApiValidationErrorItem = {
  type?: string;
  loc?: Array<string | number>;
  msg?: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
};

function formatFieldLabel(field?: string) {
  if (field === "identifier") {
    return "账号";
  }
  if (field === "email") {
    return "邮箱";
  }
  if (field === "phone") {
    return "手机号";
  }
  if (field === "password") {
    return "密码";
  }
  if (field === "code") {
    return "验证码";
  }
  if (field === "name") {
    return "昵称";
  }
  return field ?? "字段";
}

function formatValidationMessage(item: ApiValidationErrorItem) {
  const field = Array.isArray(item.loc) ? String(item.loc[item.loc.length - 1] ?? "") : "";
  const label = formatFieldLabel(field);

  if (item.type === "value_error" && field === "email") {
    return `${label}格式不正确`;
  }
  if (item.type === "string_pattern_mismatch" && field === "phone") {
    return "手机号格式不正确";
  }
  if (item.type === "string_too_short" && field === "password") {
    const minLength = item.ctx?.min_length;
    return `${label}至少需要 ${minLength} 位`;
  }
  if (item.type === "string_too_short" && field === "name") {
    const minLength = item.ctx?.min_length;
    return `${label}至少需要 ${minLength} 位`;
  }
  return item.msg ? `${label}：${item.msg}` : `${label}输入有误`;
}

function formatApiError(errorBody: ApiError) {
  if (Array.isArray(errorBody.detail)) {
    return errorBody.detail.map(formatValidationMessage).join("；");
  }
  return errorBody.detail ?? "请求失败";
}

export function getToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("tokenmall_token") ?? "";
}

export function setToken(token: string) {
  window.localStorage.setItem("tokenmall_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("tokenmall_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const accessToken = token ?? getToken();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => ({}))) as ApiError;
    throw new Error(formatApiError(errorBody));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
