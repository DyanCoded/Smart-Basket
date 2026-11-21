/**
 * Unified FastAPI client for SmartBasket & KitchenSync endpoints.
 * Handles JWT authentication, household membership, pantry CRUD,
 * offline delta-sync, and multi-store basket price optimization.
 */

import Constants from 'expo-constants';

import {
  AddHomeMemberRequest,
  AuthTokenResponse,
  BasketCalculationRequest,
  BasketCalculationResponse,
  HomeDetailResponse,
  HomeMemberDetail,
  HomeResponse,
  HouseholdBasketResponse,
  PantryItemCreateRequest,
  PantryItemResponse,
  PantryItemUpdateRequest,
  PantrySyncRequest,
  PantrySyncResponse,
  ProductListResponse,
  ProductPricesResponse,
  ProductResponse,
  UserProfileResponse,
} from '@/types/api';

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export function getApiBaseUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  if (envUrl) {
    return envUrl.replace(/\/+$/, '');
  }

  // In Expo Go on a physical phone, automatically resolve the developer PC LAN IP
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const lanHost = hostUri.split(':')[0];
    if (lanHost && lanHost !== 'localhost' && lanHost !== '127.0.0.1') {
      return `http://${lanHost}:8000/api/v1`;
    }
  }

  return DEFAULT_API_BASE_URL;
}

export function getWebSocketBaseUrl(): string {
  const httpBase = getApiBaseUrl();
  if (httpBase.startsWith('https://')) {
    return httpBase.replace(/^https:\/\//, 'wss://');
  }
  return httpBase.replace(/^http:\/\//, 'ws://');
}

let accessToken: string | null = null;
let activeHomeId: string | null = null;

export function setAuthToken(token: string | null): void {
  accessToken = token;
}

export function getAuthToken(): string | null {
  return accessToken;
}

export function setActiveHomeId(homeId: string | null): void {
  activeHomeId = homeId;
}

export function getActiveHomeId(): string | null {
  return activeHomeId;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${getApiBaseUrl()}${endpoint}`;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof URLSearchParams) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let detailMessage = errorText || response.statusText;
    try {
      const parsed = JSON.parse(errorText) as { detail?: string };
      if (parsed && typeof parsed.detail === 'string') {
        detailMessage = parsed.detail;
      }
    } catch {
      // Keep raw error text when response is not JSON
    }
    throw new Error(detailMessage || `Request failed (${response.status})`);
  }

  return (await response.json()) as T;
}

export async function registerUser(
  username: string,
  email: string,
  password: string
): Promise<UserProfileResponse> {
  return apiRequest<UserProfileResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
}

export async function loginUser(
  usernameOrEmail: string,
  password: string
): Promise<AuthTokenResponse> {
  const tokenRes = await apiRequest<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username: usernameOrEmail, password }),
  });
  setAuthToken(tokenRes.access_token);
  return tokenRes;
}

export async function fetchCurrentUser(): Promise<UserProfileResponse> {
  return apiRequest<UserProfileResponse>('/auth/me');
}

export async function listHomes(): Promise<HomeResponse[]> {
  return apiRequest<HomeResponse[]>('/homes');
}

export async function createHome(name: string): Promise<HomeDetailResponse> {
  const home = await apiRequest<HomeDetailResponse>('/homes', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
  setActiveHomeId(home.id);
  return home;
}

export async function fetchHomeDetail(
  homeId: string
): Promise<HomeDetailResponse> {
  return apiRequest<HomeDetailResponse>(`/homes/${encodeURIComponent(homeId)}`);
}

export async function addHomeMember(
  homeId: string,
  payload: AddHomeMemberRequest
): Promise<HomeMemberDetail> {
  return apiRequest<HomeMemberDetail>(
    `/homes/${encodeURIComponent(homeId)}/members`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );
}

export async function removeHomeMember(
  homeId: string,
  userId: string
): Promise<{ detail: string }> {
  return apiRequest<{ detail: string }>(
    `/homes/${encodeURIComponent(homeId)}/members/${encodeURIComponent(userId)}`,
    {
      method: 'DELETE',
    }
  );
}

export async function ensureAuthenticatedHousehold(
  preferredHomeId: string
): Promise<string> {
  if (accessToken && activeHomeId) {
    return activeHomeId;
  }

  const demoUsername = 'kitchensync_demo_buyer';
  const demoEmail = 'demo_buyer@smartbasket.co.za';
  const demoPassword = 'DemoBuyerPassword123!';

  try {
    await loginUser(demoEmail, demoPassword);
  } catch {
    await registerUser(demoUsername, demoEmail, demoPassword);
    await loginUser(demoEmail, demoPassword);
  }

  const homes = await listHomes();
  if (homes.length > 0) {
    setActiveHomeId(homes[0].id);
    return homes[0].id;
  }

  const created = await createHome('KitchenSync Family Home');
  return created.id || preferredHomeId;
}

export async function fetchPantryItems(
  homeId: string,
  statusFilter?: string
): Promise<PantryItemResponse[]> {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
  return apiRequest<PantryItemResponse[]>(`/homes/${homeId}/pantry${query}`);
}

export async function createPantryItem(
  homeId: string,
  payload: PantryItemCreateRequest
): Promise<PantryItemResponse> {
  return apiRequest<PantryItemResponse>(`/homes/${homeId}/pantry`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function patchPantryItem(
  homeId: string,
  itemId: string,
  payload: PantryItemUpdateRequest
): Promise<PantryItemResponse> {
  return apiRequest<PantryItemResponse>(`/homes/${homeId}/pantry/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function removePantryItem(
  homeId: string,
  itemId: string
): Promise<{ detail: string }> {
  return apiRequest<{ detail: string }>(`/homes/${homeId}/pantry/${itemId}`, {
    method: 'DELETE',
  });
}

export async function postPantryDeltaSync(
  homeId: string,
  payload: PantrySyncRequest
): Promise<PantrySyncResponse> {
  return apiRequest<PantrySyncResponse>(`/homes/${homeId}/pantry/sync`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchHouseholdBasket(
  homeId: string
): Promise<HouseholdBasketResponse> {
  return apiRequest<HouseholdBasketResponse>(`/homes/${homeId}/basket`);
}

export async function searchCatalogProducts(
  query = '',
  limit = 20
): Promise<ProductListResponse> {
  const qs = `?q=${encodeURIComponent(query)}&limit=${limit}`;
  return apiRequest<ProductListResponse>(`/products${qs}`);
}

export async function fetchProductById(
  productId: string
): Promise<ProductResponse> {
  return apiRequest<ProductResponse>(`/products/${encodeURIComponent(productId)}`);
}

export async function fetchProductPrices(
  productId: string
): Promise<ProductPricesResponse> {
  return apiRequest<ProductPricesResponse>(
    `/products/${encodeURIComponent(productId)}/prices`
  );
}

export async function calculateMultiStoreBasket(
  payload: BasketCalculationRequest
): Promise<BasketCalculationResponse> {
  return apiRequest<BasketCalculationResponse>('/baskets/calculate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
