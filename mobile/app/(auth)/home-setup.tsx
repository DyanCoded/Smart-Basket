/**
 * Step 2 of Two-Step Onboarding — Create a New Home or Join an Existing Home
 * by its Unique Home ID (POST /api/v1/homes or POST /api/v1/homes/join).
 */

import { type Href, useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  Typography,
} from '@/constants/Theme';
import { useAuth } from '@/context/AuthContext';
import { useAppTheme } from '@/context/ThemeContext';
import { type HouseholdRole } from '@/types/api';

type SetupMode = 'create' | 'join';

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function HomeSetupScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { colors, colorScheme } = useAppTheme();
  const { user, createHousehold, joinHousehold, isBusy } = useAuth();

  const [mode, setMode] = useState<SetupMode>('create');
  const [homeName, setHomeName] = useState<string>('');
  const [createRole, setCreateRole] = useState<HouseholdRole>('buyer');
  const [joinHomeId, setJoinHomeId] = useState<string>('');
  const [joinRole, setJoinRole] = useState<HouseholdRole>('consumer');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cardShadow = getCardShadow(colorScheme);

  const handleCreate = async () => {
    setErrorMessage(null);
    const cleanName = homeName.trim();
    if (!cleanName) {
      setErrorMessage('Enter a name for your new household.');
      return;
    }
    try {
      await createHousehold(cleanName, createRole);
      router.replace('/(tabs)/household' as Href);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Unable to create household.'
      );
    }
  };

  const handleJoin = async () => {
    setErrorMessage(null);
    const cleanId = joinHomeId.trim();
    if (!UUID_REGEX.test(cleanId)) {
      setErrorMessage(
        'Enter a valid Unique Home ID (UUID copied from another household phone).'
      );
      return;
    }
    try {
      await joinHousehold(cleanId, joinRole);
      router.replace('/(tabs)/household' as Href);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Unable to join household.'
      );
    }
  };

  const renderRolePicker = (
    selected: HouseholdRole,
    onSelect: (role: HouseholdRole) => void
  ) => (
    <View style={styles.fieldGroup}>
      <Text style={[Typography.caption, { color: colors.textSecondary }]}>
        Your Household Role
      </Text>
      <View style={styles.roleRow}>
        {(
          [
            {
              value: 'buyer' as HouseholdRole,
              label: 'Buyer',
              hint: 'Shops & manages invites',
            },
            {
              value: 'consumer' as HouseholdRole,
              label: 'Consumer',
              hint: 'Flags low/finished items',
            },
          ] as const
        ).map((opt) => {
          const isSelected = selected === opt.value;
          return (
            <Pressable
              key={opt.value}
              accessibilityRole="radio"
              accessibilityState={{ selected: isSelected }}
              onPress={() => onSelect(opt.value)}
              style={[
                styles.roleOptionCard,
                {
                  backgroundColor: isSelected
                    ? colors.primaryMuted
                    : colors.surfaceElevated,
                  borderColor: isSelected ? colors.primary : colors.border,
                },
              ]}>
              <Text
                style={[
                  Typography.bodySemiBold,
                  { color: isSelected ? colors.primary : colors.text },
                ]}>
                {opt.label}
              </Text>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                {opt.hint}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[
        styles.root,
        {
          backgroundColor: colors.background,
          paddingTop: Math.max(insets.top, Spacing.lg),
          paddingBottom: Math.max(insets.bottom, Spacing.lg),
        },
      ]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled">
        <View style={styles.topRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close home setup"
            onPress={() => router.replace('/(tabs)/household' as Href)}
            style={({ pressed }) => [
              styles.backPill,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
                opacity: pressed ? 0.75 : 1,
              },
            ]}>
            <IconSymbol name="xmark" size={16} color={colors.text} />
            <Text style={[styles.backPillText, { color: colors.text }]}>
              Skip for now
            </Text>
          </Pressable>
        </View>

        <View style={styles.heroBlock}>
          <View
            style={[
              styles.brandBadge,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <IconSymbol name="house.fill" size={16} color={colors.primary} />
            <Text style={[Typography.badge, { color: colors.primary }]}>
              STEP 2 OF 2 · HOUSEHOLD SETUP
            </Text>
          </View>
          <Text style={[Typography.hero, { color: colors.text }]}>
            {user ? `Welcome, ${user.username}` : 'Set up your Home'}
          </Text>
          <Text style={[Typography.body, { color: colors.textSecondary }]}>
            Create a new family pantry or join an existing household with its
            unique Home ID.
          </Text>
        </View>

        {/* Mode Switcher: Create New Home | Join Existing Home */}
        <View
          style={[
            styles.modeTrack,
            {
              backgroundColor: colors.surfaceMuted,
              borderColor: colors.borderSubtle,
            },
          ]}>
          {(
            [
              { key: 'create', label: 'Create a New Home' },
              { key: 'join', label: 'Join by Home ID' },
            ] as const
          ).map((tab) => {
            const selected = mode === tab.key;
            return (
              <Pressable
                key={tab.key}
                accessibilityRole="tab"
                accessibilityState={{ selected }}
                onPress={() => {
                  setMode(tab.key);
                  setErrorMessage(null);
                }}
                style={[
                  styles.modePill,
                  selected && { backgroundColor: colors.primary },
                ]}>
                <Text
                  style={[
                    styles.modeLabel,
                    {
                      color: selected
                        ? colors.primaryText
                        : colors.textSecondary,
                    },
                  ]}>
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <View
          style={[
            styles.card,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          {mode === 'create' ? (
            <>
              <View style={styles.fieldGroup}>
                <Text
                  style={[Typography.caption, { color: colors.textSecondary }]}>
                  Household Name
                </Text>
                <TextInput
                  placeholder="e.g. Demo Family Home"
                  placeholderTextColor={colors.textMuted}
                  value={homeName}
                  onChangeText={setHomeName}
                  returnKeyType="done"
                  onSubmitEditing={() => void handleCreate()}
                  style={[
                    styles.input,
                    {
                      backgroundColor: colors.surfaceElevated,
                      borderColor: colors.border,
                      color: colors.text,
                    },
                  ]}
                />
              </View>

              {renderRolePicker(createRole, setCreateRole)}
            </>
          ) : (
            <>
              <View style={styles.fieldGroup}>
                <Text
                  style={[Typography.caption, { color: colors.textSecondary }]}>
                  Unique Home ID
                </Text>
                <TextInput
                  autoCapitalize="none"
                  autoCorrect={false}
                  placeholder="Paste Home ID (e.g. 9f1c2e34-…)"
                  placeholderTextColor={colors.textMuted}
                  value={joinHomeId}
                  onChangeText={setJoinHomeId}
                  returnKeyType="done"
                  onSubmitEditing={() => void handleJoin()}
                  style={[
                    styles.input,
                    styles.monoInput,
                    {
                      backgroundColor: colors.surfaceElevated,
                      borderColor: colors.border,
                      color: colors.text,
                    },
                  ]}
                />
                <Text style={[Typography.caption, { color: colors.textMuted }]}>
                  Ask another household member to tap &ldquo;Copy ID&rdquo; on
                  their Home tab.
                </Text>
              </View>

              {renderRolePicker(joinRole, setJoinRole)}
            </>
          )}

          {errorMessage ? (
            <View
              style={[
                styles.errorBox,
                { backgroundColor: colors.statusFinishedBg },
              ]}>
              <Text
                style={[Typography.caption, { color: colors.statusFinished }]}>
                {errorMessage}
              </Text>
            </View>
          ) : null}

          <Pressable
            accessibilityRole="button"
            onPress={() =>
              void (mode === 'create' ? handleCreate() : handleJoin())
            }
            disabled={isBusy}
            style={({ pressed }) => [
              styles.primaryCta,
              {
                backgroundColor: pressed ? colors.primaryPressed : colors.primary,
                opacity: isBusy ? 0.8 : 1,
              },
            ]}>
            {isBusy ? (
              <ActivityIndicator size="small" color={colors.primaryText} />
            ) : (
              <Text
                style={[styles.primaryCtaText, { color: colors.primaryText }]}>
                {mode === 'create' ? 'Create Household' : 'Join Household'}
              </Text>
            )}
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  scrollContent: {
    padding: Spacing.lg,
    gap: Spacing.lg,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  backPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  backPillText: {
    fontSize: 13,
    fontWeight: '700',
  },
  heroBlock: {
    gap: Spacing.sm,
  },
  brandBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: Radii.pill,
  },
  modeTrack: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: Radii.md,
    borderWidth: 1,
    gap: 4,
  },
  modePill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: Radii.sm,
    alignItems: 'center',
  },
  modeLabel: {
    fontSize: 13,
    fontWeight: '700',
  },
  card: {
    borderRadius: Radii.xl,
    padding: Spacing.xl,
    borderWidth: 1,
    gap: Spacing.md,
  },
  fieldGroup: {
    gap: 6,
  },
  input: {
    borderRadius: Radii.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    fontSize: 15,
  },
  monoInput: {
    fontFamily: Platform.select({
      ios: 'Menlo',
      android: 'monospace',
      default: 'monospace',
    }),
    fontSize: 13,
  },
  roleRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  roleOptionCard: {
    flex: 1,
    borderRadius: Radii.md,
    borderWidth: 1.5,
    padding: Spacing.md,
    gap: 2,
  },
  errorBox: {
    padding: Spacing.md,
    borderRadius: Radii.md,
  },
  primaryCta: {
    paddingVertical: 14,
    borderRadius: Radii.pill,
    alignItems: 'center',
    marginTop: Spacing.xs,
  },
  primaryCtaText: {
    fontSize: 16,
    fontWeight: '800',
  },
});
