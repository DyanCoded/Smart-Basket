/**
 * Authentication & Household Management context for SmartBasket & KitchenSync (#29).
 *
 * Persists JWT access token and active household ID in SQLite / localStorage,
 * exposes Sign In, Registration + Home Onboarding, Household Switching, and
 * Buyer / Consumer member invite & removal actions wired directly to FastAPI.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { getUserPreference, setUserPreference } from '@/db/sqlite';
import {
  addHomeMember,
  createHome,
  ensureAuthenticatedHousehold,
  fetchCurrentUser,
  fetchHomeDetail,
  listHomes,
  loginUser,
  registerUser,
  removeHomeMember,
  setActiveHomeId,
  setAuthToken,
} from '@/services/api';
import {
  type HomeDetailResponse,
  type HomeResponse,
  type HouseholdRole,
  type UserProfileResponse,
} from '@/types/api';

const AUTH_TOKEN_PREF_KEY = 'auth_access_token';
const ACTIVE_HOME_PREF_KEY = 'active_home_id';

export interface AuthContextValue {
  user: UserProfileResponse | null;
  homes: HomeResponse[];
  activeHomeId: string | null;
  activeHomeDetail: HomeDetailResponse | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  isBusy: boolean;
  signIn: (usernameOrEmail: string, password: string) => Promise<void>;
  registerAndOnboard: (params: {
    username: string;
    email: string;
    password: string;
    householdName?: string;
  }) => Promise<void>;
  signInDemoSession: () => Promise<void>;
  signOut: () => Promise<void>;
  selectHome: (homeId: string) => Promise<void>;
  createHousehold: (name: string) => Promise<HomeDetailResponse>;
  inviteMember: (
    usernameOrEmail: string,
    role: HouseholdRole
  ) => Promise<void>;
  removeMember: (userId: string) => Promise<void>;
  refreshHousehold: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfileResponse | null>(null);
  const [homes, setHomes] = useState<HomeResponse[]>([]);
  const [activeHomeIdState, setActiveHomeIdState] = useState<string | null>(
    null
  );
  const [activeHomeDetail, setActiveHomeDetail] =
    useState<HomeDetailResponse | null>(null);
  const [isHydrated, setIsHydrated] = useState<boolean>(false);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  const loadAuthenticatedState = useCallback(
    async (preferredHomeId?: string | null) => {
      const [profile, homeList] = await Promise.all([
        fetchCurrentUser(),
        listHomes(),
      ]);
      setUser(profile);
      setHomes(homeList);

      const chosenHome =
        homeList.find((h) => h.id === preferredHomeId) ?? homeList[0] ?? null;

      if (chosenHome) {
        setActiveHomeId(chosenHome.id);
        setActiveHomeIdState(chosenHome.id);
        void setUserPreference(ACTIVE_HOME_PREF_KEY, chosenHome.id);
        const detail = await fetchHomeDetail(chosenHome.id);
        setActiveHomeDetail(detail);
      } else {
        setActiveHomeId(null);
        setActiveHomeIdState(null);
        setActiveHomeDetail(null);
      }
    },
    []
  );

  // Hydrate persisted JWT token & active home ID on mount
  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const [storedToken, storedHomeId] = await Promise.all([
          getUserPreference(AUTH_TOKEN_PREF_KEY),
          getUserPreference(ACTIVE_HOME_PREF_KEY),
        ]);

        if (storedHomeId) {
          setActiveHomeId(storedHomeId);
          if (mounted) {
            setActiveHomeIdState(storedHomeId);
          }
        }

        if (storedToken) {
          setAuthToken(storedToken);
          try {
            await loadAuthenticatedState(storedHomeId);
          } catch {
            // Token expired or backend unreachable; keep graceful offline state
          }
        }
      } finally {
        if (mounted) {
          setIsHydrated(true);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, [loadAuthenticatedState]);

  const signIn = useCallback(
    async (usernameOrEmail: string, password: string) => {
      setIsBusy(true);
      try {
        const tokenRes = await loginUser(usernameOrEmail.trim(), password);
        await setUserPreference(AUTH_TOKEN_PREF_KEY, tokenRes.access_token);
        await loadAuthenticatedState(activeHomeIdState);
      } finally {
        setIsBusy(false);
      }
    },
    [activeHomeIdState, loadAuthenticatedState]
  );

  const registerAndOnboard = useCallback(
    async ({
      username,
      email,
      password,
      householdName,
    }: {
      username: string;
      email: string;
      password: string;
      householdName?: string;
    }) => {
      setIsBusy(true);
      try {
        await registerUser(username.trim(), email.trim().toLowerCase(), password);
        const tokenRes = await loginUser(email.trim().toLowerCase(), password);
        await setUserPreference(AUTH_TOKEN_PREF_KEY, tokenRes.access_token);

        let createdHomeId: string | null = null;
        const cleanHomeName = householdName?.trim();
        if (cleanHomeName) {
          const created = await createHome(cleanHomeName);
          createdHomeId = created.id;
        }
        await loadAuthenticatedState(createdHomeId);
      } finally {
        setIsBusy(false);
      }
    },
    [loadAuthenticatedState]
  );

  const signInDemoSession = useCallback(async () => {
    setIsBusy(true);
    try {
      const demoHomeId = await ensureAuthenticatedHousehold(
        '00000000-0000-4000-8000-000000000001'
      );
      await loadAuthenticatedState(demoHomeId);
    } finally {
      setIsBusy(false);
    }
  }, [loadAuthenticatedState]);

  const signOut = useCallback(async () => {
    setAuthToken(null);
    setActiveHomeId(null);
    setUser(null);
    setHomes([]);
    setActiveHomeIdState(null);
    setActiveHomeDetail(null);
    await Promise.all([
      setUserPreference(AUTH_TOKEN_PREF_KEY, ''),
      setUserPreference(ACTIVE_HOME_PREF_KEY, ''),
    ]);
  }, []);

  const selectHome = useCallback(async (homeId: string) => {
    setIsBusy(true);
    try {
      setActiveHomeId(homeId);
      setActiveHomeIdState(homeId);
      await setUserPreference(ACTIVE_HOME_PREF_KEY, homeId);
      const detail = await fetchHomeDetail(homeId);
      setActiveHomeDetail(detail);
    } finally {
      setIsBusy(false);
    }
  }, []);

  const createHousehold = useCallback(
    async (name: string): Promise<HomeDetailResponse> => {
      setIsBusy(true);
      try {
        const created = await createHome(name.trim());
        await loadAuthenticatedState(created.id);
        return created;
      } finally {
        setIsBusy(false);
      }
    },
    [loadAuthenticatedState]
  );

  const inviteMember = useCallback(
    async (usernameOrEmail: string, role: HouseholdRole) => {
      if (!activeHomeIdState) {
        throw new Error('Select or create a household before inviting members.');
      }
      setIsBusy(true);
      try {
        const cleaned = usernameOrEmail.trim();
        const payload = cleaned.includes('@')
          ? { email: cleaned.toLowerCase(), role }
          : { username: cleaned, role };
        await addHomeMember(activeHomeIdState, payload);
        await loadAuthenticatedState(activeHomeIdState);
      } finally {
        setIsBusy(false);
      }
    },
    [activeHomeIdState, loadAuthenticatedState]
  );

  const removeMember = useCallback(
    async (userId: string) => {
      if (!activeHomeIdState) {
        return;
      }
      setIsBusy(true);
      try {
        await removeHomeMember(activeHomeIdState, userId);
        const removingSelf = user?.id === userId;
        await loadAuthenticatedState(removingSelf ? null : activeHomeIdState);
      } finally {
        setIsBusy(false);
      }
    },
    [activeHomeIdState, loadAuthenticatedState, user?.id]
  );

  const refreshHousehold = useCallback(async () => {
    setIsBusy(true);
    try {
      await loadAuthenticatedState(activeHomeIdState);
    } finally {
      setIsBusy(false);
    }
  }, [activeHomeIdState, loadAuthenticatedState]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      homes,
      activeHomeId: activeHomeIdState,
      activeHomeDetail,
      isAuthenticated: Boolean(user),
      isHydrated,
      isBusy,
      signIn,
      registerAndOnboard,
      signInDemoSession,
      signOut,
      selectHome,
      createHousehold,
      inviteMember,
      removeMember,
      refreshHousehold,
    }),
    [
      user,
      homes,
      activeHomeIdState,
      activeHomeDetail,
      isHydrated,
      isBusy,
      signIn,
      registerAndOnboard,
      signInDemoSession,
      signOut,
      selectHome,
      createHousehold,
      inviteMember,
      removeMember,
      refreshHousehold,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
