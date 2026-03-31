export type UserInfo = {
  id: number;
  email: string;
  phone?: string | null;
  name: string;
  role: "user" | "admin";
  status: string;
};

export type Wallet = {
  balance: string;
  reserved_balance: string;
  available_balance: string;
  currency: string;
};

export type ApiKey = {
  id: number;
  name: string;
  key_prefix: string;
  status: string;
  token_limit: number | null;
  request_limit: number | null;
  budget_limit: string | null;
  used_tokens: number;
  used_requests: number;
  used_amount: string;
  last_used_at: string | null;
  created_at: string;
  month_requests: number;
  success_rate: string | number;
  avg_response_time_ms: number | null;
  plaintext_key?: string;
};

export type PaymentOrder = {
  id: number;
  order_no: string;
  amount: string;
  payment_method: string;
  channel_order_no?: string | null;
  payment_url?: string | null;
  qr_code?: string | null;
  qr_code_image?: string | null;
  status: string;
  paid_at: string | null;
  created_at: string;
};

export type RefundSummary = {
  refundable_amount: string;
  recharge_amount: string;
  consumed_amount: string;
  refunded_amount: string;
  pending_exists: boolean;
};

export type RefundRequest = {
  id: number;
  request_no: string;
  amount: string;
  refunded_amount?: string;
  remaining_amount?: string;
  reason: string;
  status: string;
  admin_note: string;
  reviewed_at: string | null;
  refunded_at: string | null;
  created_at: string;
};

export type UsageLog = {
  id: number | string;
  model_code: string;
  request_id: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  amount: string;
  billing_source?: string;
  status: string;
  error_message: string;
  created_at: string;
  event_type?: string;
  title?: string;
  subtitle?: string;
  badge?: string;
};

export type UsageHistoryResponse = {
  items: UsageLog[];
  total: number;
  page: number;
  page_size: number;
};

export type PricingItem = {
  label: string;
  unit: string;
  price: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type DashboardSummary = {
  total_requests: number;
  month_spend: string;
  token_balance: string;
  success_rate: number;
  recent_activities: {
    time: string;
    title: string;
    subtitle: string;
    tokens: number;
    amount: string;
  }[];
  monthly_usage: { label: string; value: number }[];
  weekly_usage: { label: string; value: number }[];
};

export type ModelInfo = {
  id: number;
  provider: string;
  supports_multimodal_chat?: boolean;
  vendor_display_name: string;
  model_code: string;
  model_id: string;
  capability_type: string;
  display_name: string;
  category: string;
  billing_mode: string;
  pricing_items: PricingItem[];
  input_price_per_million: string;
  output_price_per_million: string;
  description: string;
  hero_description: string;
  rating: number;
  support_features: string[];
  tags: string[];
  example_python: string;
  example_typescript: string;
  example_curl: string;
};

export type AdminOverview = {
  total_users: number;
  active_users: number;
  total_api_keys: number;
  active_models: number;
  total_requests: number;
  success_rate: number;
  month_spend: string;
  pending_orders: number;
  recent_orders: {
    order_no: string;
    amount: string;
    status: string;
    created_at: string;
  }[];
  recent_errors: {
    request_id: string;
    model_code: string;
    error_message: string;
    created_at: string;
  }[];
};

export type AdminUser = {
  id: number;
  email: string;
  name: string;
  role: string;
  status: string;
  balance: string;
  reserved_balance: string;
  api_key_count: number;
  created_at: string;
};

export type AdminOrder = PaymentOrder & {
  user_id: number;
  user_email: string;
  user_name: string;
};

export type AdminApiKey = ApiKey & {
  user_id: number;
  user_email: string;
  user_name: string;
};

export type AdminLedger = {
  id: number;
  user_id: number;
  user_email: string;
  user_name: string;
  type: string;
  amount: string;
  balance_after: string;
  reference_type: string;
  reference_id: string;
  description: string;
  created_at: string;
};

export type AdminUsage = UsageLog & {
  user_id: number;
  user_email: string;
  user_name: string;
  api_key_id: number | null;
};

export type AdminModel = ModelInfo & {
  is_active: boolean;
  created_at: string;
};

export type BailianCatalogItem = {
  id: number;
  upstream_model_id: string;
  provider: string;
  provider_display_name: string;
  display_name: string;
  model_code: string;
  category: string;
  capability_type: string;
  billing_mode: string;
  pricing_items: PricingItem[];
  description: string;
  support_features: string[];
  tags: string[];
  input_price_per_million: string | null;
  output_price_per_million: string | null;
  owned_by: string;
  is_available: boolean;
  is_imported: boolean;
  last_synced_at: string;
};

export type ModelPriceSnapshot = {
  id: number;
  model_catalog_id: number;
  input_price_per_million: string;
  output_price_per_million: string;
  note: string;
  created_at: string;
};

export type AdminRefund = RefundRequest & {
  user_id: number;
  user_email: string;
  user_name: string;
};

export type AdminRefundActionResult = {
  success: boolean;
  status: string;
  message?: string;
};
