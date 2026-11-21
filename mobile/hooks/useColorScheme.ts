import { useColorScheme as useRNColorScheme } from 'react-native';

import { useOptionalAppTheme } from '@/context/ThemeContext';

export function useColorScheme(): 'light' | 'dark' {
  const themeCtx = useOptionalAppTheme();
  const systemScheme = useRNColorScheme();

  if (themeCtx) {
    return themeCtx.colorScheme;
  }
  return systemScheme === 'light' ? 'light' : 'dark';
}
