/**
 * Real-time household WebSocket client backed by Redis Pub/Sub
 * (`WS /api/v1/homes/{home_id}/ws`).
 */

import { upsertLocalPantryItem } from '@/db/sqlite';
import { getAuthToken, getWebSocketBaseUrl } from '@/services/api';
import { PantryItemResponse, WebSocketEventPayload } from '@/types/api';

export type PantryEventListener = (payload: WebSocketEventPayload) => void;

export class HouseholdRealtimeStream {
  private ws: WebSocket | null = null;
  private homeId: string;
  private listener: PantryEventListener;

  constructor(homeId: string, listener: PantryEventListener) {
    this.homeId = homeId;
    this.listener = listener;
  }

  public connect(): void {
    const token = getAuthToken();
    if (!token) {
      return;
    }

    const wsUrl = `${getWebSocketBaseUrl()}/homes/${this.homeId}/ws?token=${encodeURIComponent(token)}`;
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onmessage = async (event: MessageEvent) => {
        try {
          const payload = JSON.parse(String(event.data)) as WebSocketEventPayload;
          if (payload.event === 'ITEM_UPDATED' && payload.data) {
            await upsertLocalPantryItem(payload.data as PantryItemResponse);
          }
          this.listener(payload);
        } catch {
          // Ignore malformed event frames
        }
      };

      this.ws.onerror = () => {
        this.disconnect();
      };
    } catch {
      this.ws = null;
    }
  }

  public disconnect(): void {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // Ignore close errors
      }
      this.ws = null;
    }
  }
}
