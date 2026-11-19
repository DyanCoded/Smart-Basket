/**
 * Unified FastAPI client for SmartBasket & KitchenSync endpoints.
 * Handles JWT authentication, household membership, pantry CRUD,
 * offline delta-sync, and multi-store basket price optimization.
 */

import {
  AuthTokenResponse,
  BasketCalculationRequest,
  BasketCalculationResponse,
  HomeDetailResponse,
  HomeResponse,
  HouseholdBasketResponse,
  PantryItemCreateRequest,
  PantryItemResponse,
  PantryItemUpdateRequest,
  PantrySyncRequest,
  PantrySyncResponse,
  ProductListResponse,
  UserProfileResponse,
} from '@/types/api';

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export function getApiBaseUrl(): string {
  const envUrl = process.env.EXPO_PUBLIC_API_URL;
  return envUrl ? envUrl.replace(/\/+$/, '') : DEFAULT_API_BASE_URL;
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
    throw new Error(`API ${response.status}: ${errorText || response.statusText}`);
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

export async function calculateMultiStoreBasket(
  payload: BasketCalculationRequest
): Promise<BasketCalculationResponse> {
  return apiRequest<BasketCalculationResponse>('/baskets/calculate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
