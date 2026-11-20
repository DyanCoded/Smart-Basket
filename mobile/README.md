# KitchenSync Mobile (`mobile/`) 📱🛒

Expo SDK 58 / React Native mobile frontend for **Smart Basket & KitchenSync**, providing offline-first household pantry tracking (`react-native-sqlite-storage`), real-time WebSocket updates, and automated multi-store grocery basket price comparison.

## Architecture & Directory Layout

```text
mobile/
├── app/
│   ├── _layout.tsx               # Root Stack Navigator & Web setImmediate polyfill
│   └── (tabs)/
│       ├── _layout.tsx           # Bottom Tab Navigator (Pantry & SmartBasket)
│       ├── index.tsx             # KitchenSync Pantry & Offline SQLite Sync Queue Screen
│       └── explore.tsx           # SmartBasket Multi-Store Price Optimizer Screen
├── db/
│   ├── sqlite.ts                 # Local SQLite schema (local_pantry_items, pending_sync, sync_meta)
│   └── index.ts
├── services/
│   ├── api.ts                    # Unified FastAPI REST client, JWT Auth & LAN IP auto-resolution
│   ├── sync.ts                   # Offline-to-online delta sync (/pantry/sync) & basket bridge
│   ├── websocket.ts              # Redis Pub/Sub real-time stream (/homes/{home_id}/ws)
│   └── index.ts
└── types/
    ├── api.ts                    # TypeScript interfaces matching FastAPI Pydantic v2 schemas
    └── react-native-sqlite-storage.d.ts
```

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install --legacy-peer-deps
   ```

2. **Run static checks (TypeScript & ESLint):**
   ```bash
   npm run typecheck
   npm run lint
   ```

3. **Start the Expo development server:**
   ```bash
   npx expo start --clear
   ```
   - Press **`w`** to open in your web browser (`http://localhost:8081`).
   - Or scan the QR code using **Expo Go (SDK 58)** on your iOS/Android phone.
