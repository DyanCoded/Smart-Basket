// Fallback for using MaterialIcons on Android and web.

import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { SymbolViewProps, SymbolWeight } from 'expo-symbols';
import { ComponentProps } from 'react';
import { OpaqueColorValue, type StyleProp, type TextStyle } from 'react-native';

type IconMapping = Partial<
  Record<
    Extract<SymbolViewProps['name'], string>,
    ComponentProps<typeof MaterialIcons>['name']
  >
>;

/**
 * SF Symbols to Material Icons mappings for SmartBasket's 3-tab navigation
 * (Pantry | Basket | Home) and Warm Grocery chrome controls.
 */
const MAPPING = {
  'tray.full.fill': 'kitchen',
  'basket.fill': 'shopping-basket',
  'house.fill': 'home',
  'person.fill': 'person',
  'person.badge.plus': 'person-add',
  'doc.on.doc': 'content-copy',
  trash: 'delete-outline',
  'sun.max.fill': 'light-mode',
  'moon.fill': 'dark-mode',
  'checkmark.circle.fill': 'check-circle',
  checkmark: 'check',
  magnifyingglass: 'search',
  plus: 'add',
  xmark: 'close',
  'chevron.down': 'keyboard-arrow-down',
  'chevron.up': 'keyboard-arrow-up',
  'exclamationmark.triangle.fill': 'warning',
  'arrow.triangle.2.circlepath': 'sync',
  'paperplane.fill': 'send',
  'chevron.left.forwardslash.chevron.right': 'code',
  'chevron.right': 'chevron-right',
} as const satisfies IconMapping;

export type IconSymbolName = keyof typeof MAPPING;

export function IconSymbol({
  name,
  size = 24,
  color,
  style,
}: {
  name: IconSymbolName;
  size?: number;
  color: string | OpaqueColorValue;
  style?: StyleProp<TextStyle>;
  weight?: SymbolWeight;
}) {
  return (
    <MaterialIcons
      color={color}
      size={size}
      name={MAPPING[name]}
      style={style}
    />
  );
}
