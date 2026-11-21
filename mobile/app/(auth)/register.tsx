/**
 * Warm Grocery Option B Registration & Household Onboarding Screen (#29).
 *
 * Registers the user (POST /api/v1/auth/register), authenticates them
 * (POST /api/v1/auth/login), and creates their initial Household as `buyer`
 * (POST /api/v1/homes) in a single warm onboarding flow.
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

export default function RegisterScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { colors, colorScheme } = useAppTheme();
  const { registerAndOnboard, isBusy } = useAuth();

  const [username, setUsername] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [householdName, setHouseholdName] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cardShadow = getCardShadow(colorScheme);

  const handleSubmit = async () => {
    setErrorMessage(null);
    if (!username.trim() || !email.trim() || !password) {
      setErrorMessage('Username, email, and password are required.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    try {
      await registerAndOnboard({
        username: username.trim(),
        email: email.trim(),
        password,
        householdName: householdName.trim() || `${username.trim()}'s Home`,
      });
      router.replace('/(tabs)/household' as Href);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Unable to complete registration right now.'
      );
    }
  };

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
            accessibilityLabel="Close registration"
            onPress={() => router.back()}
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
              Close
            </Text>
          </Pressable>
        </View>

        <View style={styles.heroBlock}>
          <View
            style={[
              styles.brandBadge,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <IconSymbol name="house.fill" size={18} color={colors.primary} />
            <Text style={[Typography.badge, { color: colors.primary }]}>
              HOUSEHOLD ONBOARDING
            </Text>
          </View>
          <Text style={[Typography.hero, { color: colors.text }]}>
            Set up your kitchen
          </Text>
          <Text style={[Typography.body, { color: colors.textSecondary }]}>
            Create your account and household space. You&apos;ll start as a
            Buyer so you can invite family members right away.
          </Text>
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
          <View style={styles.fieldGroup}>
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              Username
            </Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="e.g. lerato_m"
              placeholderTextColor={colors.textMuted}
              value={username}
              onChangeText={setUsername}
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

          <View style={styles.fieldGroup}>
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              Email Address
            </Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              placeholder="e.g. lerato@example.co.za"
              placeholderTextColor={colors.textMuted}
              value={email}
              onChangeText={setEmail}
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

          <View style={styles.fieldGroup}>
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              Password (min. 8 characters)
            </Text>
            <TextInput
              secureTextEntry
              placeholder="Create a secure password"
              placeholderTextColor={colors.textMuted}
              value={password}
              onChangeText={setPassword}
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

          <View style={styles.fieldGroup}>
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              Household Name
            </Text>
            <TextInput
              placeholder="e.g. The Mokoena Kitchen"
              placeholderTextColor={colors.textMuted}
              value={householdName}
              onChangeText={setHouseholdName}
              returnKeyType="done"
              onSubmitEditing={() => void handleSubmit()}
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
            onPress={() => void handleSubmit()}
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
                Create Account &amp; Home
              </Text>
            )}
          </Pressable>
        </View>

        <View style={styles.footerLinkRow}>
          <Text style={[Typography.body, { color: colors.textSecondary }]}>
            Already have an account?
          </Text>
          <Pressable
            onPress={() => router.replace('/(auth)/login' as Href)}
            hitSlop={8}>
            <Text style={[styles.footerLinkText, { color: colors.primary }]}>
              Sign In
            </Text>
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
  footerLinkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 6,
  },
  footerLinkText: {
    fontSize: 15,
    fontWeight: '800',
  },
});
