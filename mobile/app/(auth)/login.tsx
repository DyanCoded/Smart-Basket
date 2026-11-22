/**
 * Warm Grocery Option B Sign-In Screen (#29).
 * Authenticates against POST /api/v1/auth/login and loads user's households.
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

export default function LoginScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { colors, colorScheme } = useAppTheme();
  const { signIn, isBusy } = useAuth();

  const [identifier, setIdentifier] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cardShadow = getCardShadow(colorScheme);

  const handleSubmit = async () => {
    setErrorMessage(null);
    if (!identifier.trim() || !password) {
      setErrorMessage('Enter both your email or username and password.');
      return;
    }

    try {
      const homesCount = await signIn(identifier.trim(), password);
      if (homesCount === 0) {
        router.replace('/(auth)/home-setup' as Href);
      } else {
        router.replace('/(tabs)/household' as Href);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Unable to sign in right now.'
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
        {/* Top Back / Dismiss */}
        <View style={styles.topRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Back to app"
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

        {/* Hero Heading */}
        <View style={styles.heroBlock}>
          <View
            style={[
              styles.brandBadge,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <IconSymbol name="basket.fill" size={20} color={colors.primary} />
            <Text style={[Typography.badge, { color: colors.primary }]}>
              SMARTBASKET & KITCHENSYNC
            </Text>
          </View>
          <Text style={[Typography.hero, { color: colors.text }]}>
            Welcome back
          </Text>
          <Text style={[Typography.body, { color: colors.textSecondary }]}>
            Sign in to sync your household pantry in real time and compare
            national grocery prices.
          </Text>
        </View>

        {/* Sign-In Form Card */}
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
              Email or Username
            </Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              placeholder="e.g. lerato@example.co.za"
              placeholderTextColor={colors.textMuted}
              value={identifier}
              onChangeText={setIdentifier}
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
              Password
            </Text>
            <TextInput
              secureTextEntry
              placeholder="Enter your password"
              placeholderTextColor={colors.textMuted}
              value={password}
              onChangeText={setPassword}
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
                Sign In
              </Text>
            )}
          </Pressable>
        </View>

        {/* Secondary Register Link */}
        <View style={styles.footerLinkRow}>
          <Text style={[Typography.body, { color: colors.textSecondary }]}>
            New to SmartBasket?
          </Text>
          <Pressable
            onPress={() => router.replace('/(auth)/register' as Href)}
            hitSlop={8}>
            <Text style={[styles.footerLinkText, { color: colors.primary }]}>
              Create account &amp; home
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
