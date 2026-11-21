import { useEffect, useState } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

import { useOptionalAppTheme } from '@/context/ThemeContext';

/**
 * Hydration-safe web color scheme hook backed by AppThemeProvider (Dark primary).
 */
export function useColorScheme(): 'light' | 'dark' {
  const themeCtx = useOptionalAppTheme();
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    setHasHydrated(true);
  }, []);

  const systemScheme = useRNColorScheme();

  if (themeCtx) {
    return themeCtx.colorScheme;
  }

  if (hasHydrated && systemScheme === 'light') {
    return 'light';
  }

  return 'dark';
}
