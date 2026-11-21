/**
 * TypeScript interfaces matching SmartBasket FastAPI v1 Pydantic schemas.
 * Enforces contract invariance between mobile client and unified backend.
 */

export type PantryStatus = 'ok' | 'low' | 'finished';
export type HouseholdRole = 'buyer' | 'consumer';

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MembershipSummary {
  id: string;
  home_id: string;
  home_name: string;
  role: HouseholdRole;
  created_at: string;
}

export interface UserProfileResponse {
  id: string;
  username: string;
  email: string;
  created_at: string;
  memberships: MembershipSummary[];
}

export interface HomeResponse {
  id: string;
  name: string;
  created_at: string;
}

export interface HomeMemberDetail {
  id: string;
  user_id: string;
  username: string;
  email: string;
  role: HouseholdRole;
  created_at: string;
}

export interface HomeDetailResponse extends HomeResponse {
  members: HomeMemberDetail[];
}

export interface PantryItemResponse {
  id: string;
  home_id: string;
  product_id: string | null;
  category_id: string | null;
  custom_name: string | null;
  barcode: string | null;
  quantity: string;
  unit_type: string;
  low_stock_threshold: string;
  status: PantryStatus;
  is_deleted: boolean;
  updated_at: string;
  product_name: string | null;
  category_name: string | null;
}

export interface PantryItemCreateRequest {
  product_id?: string | null;
  category_id?: string | null;
  custom_name?: string | null;
  barcode?: string | null;
  quantity?: number | string;
  unit_type?: string;
  low_stock_threshold?: number | string;
  status?: PantryStatus;
  note?: string | null;
}

export interface PantryItemUpdateRequest {
  product_id?: string | null;
  category_id?: string | null;
  custom_name?: string | null;
  barcode?: string | null;
  quantity?: number | string;
  unit_type?: string;
  low_stock_threshold?: number | string;
  status?: PantryStatus;
  note?: string | null;
}

export interface PantrySyncMutation {
  id: string;
  product_id?: string | null;
  category_id?: string | null;
  custom_name?: string | null;
  barcode?: string | null;
  quantity: string;
  unit_type: string;
  low_stock_threshold: string;
  status: PantryStatus;
  updated_at: string;
  is_deleted: boolean;
  note?: string | null;
}

export interface PantrySyncRequest {
  last_synced_at: string | null;
  mutations: PantrySyncMutation[];
}

export interface PantrySyncResponse {
  synced_at: string;
  items: PantryItemResponse[];
  applied_mutations_count: number;
}

export interface HouseholdBasketItemResponse {
  id: string;
  product_id: string;
  product_name: string;
  quantity: string;
}

export interface HouseholdBasketResponse {
  id: string;
  home_id: string;
  name: string;
  created_at: string;
  items: HouseholdBasketItemResponse[];
}

export interface BasketItemRequest {
  product_id: string;
  quantity: number | string;
}

export interface BasketCalculationRequest {
  items: BasketItemRequest[];
  store_ids?: string[];
  retailer_slugs?: string[];
}

export interface StoreBasketItemDetail {
  product_id: string;
  product_name: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  is_promotional: boolean;
}

export interface MissingBasketItem {
  product_id: string;
  product_name: string;
  requested_quantity: string;
}

export interface StoreBasketTotal {
  store_id: string;
  store_name: string;
  branch_code?: string | null;
  retailer_name: string;
  total_price: string;
  is_complete_match: boolean;
  items_available_count: number;
  total_items_count: number;
  items: StoreBasketItemDetail[];
  missing_items: MissingBasketItem[];
}

export interface SplitStoreAllocation {
  store_id: string;
  store_name: string;
  retailer_name: string;
  items: StoreBasketItemDetail[];
  subtotal: string;
}

export interface OptimalSplitResult {
  stores: SplitStoreAllocation[];
  total_price: string;
  savings_amount: string;
  savings_percentage: string;
  is_complete_match: boolean;
  cheaper_than_single_store: boolean;
}

export interface BasketCalculationResponse {
  ranked_stores: StoreBasketTotal[];
  cheapest_single_store: StoreBasketTotal | null;
  optimal_split: OptimalSplitResult | null;
  total_items_requested: number;
}

export interface ProductResponse {
  id: string;
  name: string;
  brand: string | null;
  barcode: string | null;
  unit_size: string;
  unit_type: string;
  category_id: string | null;
}

export interface ProductListResponse {
  items: ProductResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface StorePriceItem {
  id: string;
  store_id: string;
  store_name: string;
  branch_code: string | null;
  retailer_name: string;
  price: string;
  is_promotional: boolean;
  is_in_stock: boolean;
  updated_at: string;
}

export interface ProductPricesResponse {
  product_id: string;
  product_name: string;
  prices: StorePriceItem[];
  total_stores: number;
}

export type WebSocketEventType = 'CONNECTED' | 'ITEM_UPDATED' | 'ITEM_DELETED';

export interface WebSocketEventPayload {
  event: WebSocketEventType;
  home_id: string;
  timestamp?: string;
  user_id?: string;
  role?: HouseholdRole;
  data?: Partial<PantryItemResponse> & { id: string; is_deleted?: boolean };
}
