/**
 * Home Tab — Household Management, Buyer / Consumer RBAC Roster & Warm Grocery
 * Appearance Settings (#29).
 *
 * Features:
 * - Account session card with Sign In / Register / Quick Demo Session / Sign Out
 * - Household switcher pills + inline "+ New Household" creation
 * - Member roster with clear Buyer (emerald) & Consumer (amber) role badges,
 *   Buyer-gated member invite form, and member remove / self-leave actions
 * - Instant persisted Appearance switcher (Dark / Light / System)
 * - Live Sync & national catalog price freshness telemetry
 */

import { type Href, useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  type ThemePreference,
  Typography,
} from '@/constants/Theme';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/context/SyncStatusContext';
import { useAppTheme } from '@/context/ThemeContext';
import { getApiBaseUrl } from '@/services/api';
import { type HouseholdRole } from '@/types/api';

const THEME_OPTIONS: {
  value: ThemePreference;
  label: string;
  description: string;
}[] = [
  {
    value: 'dark',
    label: 'Dark',
    description: 'Deep charcoal-forest & emerald (Primary)',
  },
  {
    value: 'light',
    label: 'Light',
    description: 'Warm cream stone & forest green',
  },
  {
    value: 'system',
    label: 'System',
    description: 'Match device appearance automatically',
  },
];

function formatFreshnessTimestamp(iso: string | null): string {
  if (!iso) {
    return 'Not yet verified';
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function HouseholdTabScreen() {
  const router = useRouter();
  const { colors, colorScheme, preference, setPreference } = useAppTheme();
  const {
    user,
    homes,
    activeHomeId,
    activeHomeDetail,
    isAuthenticated,
    isBusy,
    signInDemoSession,
    signOut,
    selectHome,
    createHousehold,
    inviteMember,
    removeMember,
    refreshHousehold,
  } = useAuth();
  const {
    status,
    pendingCount,
    lastSyncedAt,
    catalogLastSyncAt,
    trackedPricesCount,
    probeBackendHealth,
  } = useSyncStatus();

  const [newHomeName, setNewHomeName] = useState<string>('');
  const [inviteIdentifier, setInviteIdentifier] = useState<string>('');
  const [inviteRole, setInviteRole] = useState<HouseholdRole>('consumer');
  const [copiedId, setCopiedId] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{
    kind: 'ok' | 'error';
    text: string;
  } | null>(null);

  const handleCopyHomeId = async (homeIdToCopy: string) => {
    try {
      if (
        Platform.OS === 'web' &&
        typeof navigator !== 'undefined' &&
        navigator.clipboard?.writeText
      ) {
        await navigator.clipboard.writeText(homeIdToCopy);
      } else {
        await Share.share({
          message: homeIdToCopy,
          title: 'SmartBasket Unique Home ID',
        });
      }
      setCopiedId(true);
      setFeedback({
        kind: 'ok',
        text: 'Unique Home ID ready to paste on another phone.',
      });
      setTimeout(() => setCopiedId(false), 3000);
    } catch {
      setFeedback({
        kind: 'error',
        text: 'Unable to copy Home ID automatically — long-press the ID to copy.',
      });
    }
  };

  const cardShadow = getCardShadow(colorScheme);
  const currentRole: HouseholdRole | undefined = activeHomeDetail?.role;
  const isBuyer = currentRole === 'buyer';
  const members = activeHomeDetail?.members ?? [];

  const handleCreateHousehold = async () => {
    const clean = newHomeName.trim();
    if (!clean) {
      return;
    }
    setFeedback(null);
    try {
      const created = await createHousehold(clean);
      setNewHomeName('');
      setFeedback({
        kind: 'ok',
        text: `Created "${created.name}" and switched to it as Buyer.`,
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Failed to create household.',
      });
    }
  };

  const handleInvite = async () => {
    const clean = inviteIdentifier.trim();
    if (!clean) {
      return;
    }
    setFeedback(null);
    try {
      await inviteMember(clean, inviteRole);
      setInviteIdentifier('');
      setFeedback({
        kind: 'ok',
        text: `Added ${clean} as ${inviteRole === 'buyer' ? 'Buyer' : 'Consumer'}.`,
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Could not invite member.',
      });
    }
  };

  const handleRemoveMember = async (memberUserId: string, username: string) => {
    setFeedback(null);
    try {
      await removeMember(memberUserId);
      setFeedback({
        kind: 'ok',
        text:
          user?.id === memberUserId
            ? 'You left the household.'
            : `Removed ${username} from the household.`,
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Could not remove member.',
      });
    }
  };

  const handleDemoLogin = async () => {
    setFeedback(null);
    try {
      await signInDemoSession();
      setFeedback({
        kind: 'ok',
        text: 'Connected to demo Buyer household session.',
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text:
          err instanceof Error
            ? err.message
            : 'Backend unreachable. Ensure FastAPI is running on port 8000.',
      });
    }
  };

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled">
      {/* Feedback Toast Banner */}
      {feedback ? (
        <View
          style={[
            styles.feedbackBanner,
            {
              backgroundColor:
                feedback.kind === 'ok'
                  ? colors.statusOkBg
                  : colors.statusFinishedBg,
              borderColor:
                feedback.kind === 'ok' ? colors.statusOk : colors.statusFinished,
            },
          ]}>
          <Text
            style={[
              Typography.caption,
              {
                color:
                  feedback.kind === 'ok'
                    ? colors.statusOk
                    : colors.statusFinished,
                flex: 1,
              },
            ]}>
            {feedback.text}
          </Text>
          <Pressable onPress={() => setFeedback(null)} hitSlop={8}>
            <IconSymbol
              name="xmark"
              size={15}
              color={
                feedback.kind === 'ok' ? colors.statusOk : colors.statusFinished
              }
            />
          </Pressable>
        </View>
      ) : null}

      {/* 1. Account & Authentication Card */}
      <View
        style={[
          styles.heroCard,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.sectionHeader}>
          <View
            style={[
              styles.eyebrowBadge,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <Text style={[Typography.badge, { color: colors.primary }]}>
              HOUSEHOLD ACCOUNT
            </Text>
          </View>
          {isAuthenticated && currentRole ? (
            <View
              style={[
                styles.rolePill,
                {
                  backgroundColor: isBuyer
                    ? colors.statusOkBg
                    : colors.statusLowBg,
                },
              ]}>
              <Text
                style={[
                  Typography.badge,
                  { color: isBuyer ? colors.statusOk : colors.statusLow },
                ]}>
                {isBuyer ? 'Buyer' : 'Consumer'}
              </Text>
            </View>
          ) : null}
        </View>

        {isAuthenticated && user ? (
          <>
            <View style={styles.profileRow}>
              <View
                style={[
                  styles.avatarCircle,
                  { backgroundColor: colors.primary },
                ]}>
                <Text style={[styles.avatarInitial, { color: colors.primaryText }]}>
                  {user.username.slice(0, 1).toUpperCase()}
                </Text>
              </View>
              <View style={styles.profileInfo}>
                <Text style={[Typography.subtitle, { color: colors.text }]}>
                  {user.username}
                </Text>
                <Text style={[Typography.caption, { color: colors.textSecondary }]}>
                  {user.email}
                </Text>
              </View>
              <Pressable
                onPress={() => void signOut()}
                style={[
                  styles.signOutPill,
                  {
                    backgroundColor: colors.surfaceElevated,
                    borderColor: colors.border,
                  },
                ]}>
                <Text
                  style={[
                    styles.signOutText,
                    { color: colors.statusFinished },
                  ]}>
                  Sign Out
                </Text>
              </Pressable>
            </View>
          </>
        ) : (
          <>
            <Text style={[Typography.title, { color: colors.text }]}>
              Share your kitchen
            </Text>
            <Text style={[Typography.body, { color: colors.textSecondary }]}>
              Sign in or create a household to sync pantry items across family
              phones and manage Buyer &amp; Consumer roles.
            </Text>
            <View style={styles.authActionRow}>
              <Pressable
                onPress={() => router.push('/(auth)/login' as Href)}
                style={({ pressed }) => [
                  styles.primaryButton,
                  styles.flexButton,
                  {
                    backgroundColor: pressed
                      ? colors.primaryPressed
                      : colors.primary,
                  },
                ]}>
                <Text
                  style={[
                    styles.primaryButtonText,
                    { color: colors.primaryText },
                  ]}>
                  Sign In
                </Text>
              </Pressable>
              <Pressable
                onPress={() => router.push('/(auth)/register' as Href)}
                style={[
                  styles.secondaryButton,
                  styles.flexButton,
                  {
                    backgroundColor: colors.surfaceElevated,
                    borderColor: colors.border,
                  },
                ]}>
                <Text
                  style={[styles.secondaryButtonText, { color: colors.text }]}>
                  Create Account
                </Text>
              </Pressable>
            </View>
            <Pressable
              onPress={() => void handleDemoLogin()}
              disabled={isBusy}
              style={styles.demoLinkBtn}>
              <Text style={[Typography.caption, { color: colors.primary }]}>
                {isBusy
                  ? 'Connecting demo household…'
                  : 'Or connect with Demo Buyer session'}
              </Text>
            </Pressable>
          </>
        )}
      </View>

      {/* 2. Household Switcher & Create Home (when authenticated) */}
      {isAuthenticated ? (
        <View
          style={[
            styles.card,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          <View style={styles.sectionHeader}>
            <Text style={[Typography.subtitle, { color: colors.text }]}>
              Your Households
            </Text>
            <Pressable
              onPress={() => void refreshHousehold()}
              disabled={isBusy}
              hitSlop={8}>
              {isBusy ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <IconSymbol
                  name="arrow.triangle.2.circlepath"
                  size={18}
                  color={colors.primary}
                />
              )}
            </Pressable>
          </View>

          {homes.length > 0 ? (
            <View style={styles.homePillWrap}>
              {homes.map((home) => {
                const isSelected = home.id === activeHomeId;
                return (
                  <Pressable
                    key={home.id}
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    onPress={() => void selectHome(home.id)}
                    style={({ pressed }) => [
                      styles.homePill,
                      {
                        backgroundColor: isSelected
                          ? colors.primaryMuted
                          : colors.surfaceElevated,
                        borderColor: isSelected ? colors.primary : colors.border,
                        opacity: pressed ? 0.8 : 1,
                      },
                    ]}>
                    <IconSymbol
                      name="house.fill"
                      size={15}
                      color={isSelected ? colors.primary : colors.textMuted}
                    />
                    <Text
                      style={[
                        styles.homePillText,
                        {
                          color: isSelected
                            ? colors.primary
                            : colors.textSecondary,
                        },
                      ]}>
                      {home.name}
                    </Text>
                    {home.member_count ? (
                      <Text
                        style={[
                          Typography.caption,
                          { color: colors.textMuted },
                        ]}>
                        ({home.member_count})
                      </Text>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          ) : (
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              No household yet — create your first shared kitchen below.
            </Text>
          )}

          {/* Inline Create Household + Join by ID Shortcut */}
          <View style={styles.inlineFormRow}>
            <TextInput
              placeholder="New household name…"
              placeholderTextColor={colors.textMuted}
              value={newHomeName}
              onChangeText={setNewHomeName}
              returnKeyType="done"
              onSubmitEditing={() => void handleCreateHousehold()}
              style={[
                styles.inlineInput,
                {
                  backgroundColor: colors.surfaceElevated,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
            />
            <Pressable
              onPress={() => void handleCreateHousehold()}
              disabled={isBusy || !newHomeName.trim()}
              style={[
                styles.inlineActionBtn,
                {
                  backgroundColor: colors.primary,
                  opacity: isBusy || !newHomeName.trim() ? 0.5 : 1,
                },
              ]}>
              <Text
                style={[styles.inlineActionText, { color: colors.primaryText }]}>
                + Create
              </Text>
            </Pressable>
          </View>

          <Pressable
            onPress={() => router.push('/(auth)/home-setup' as Href)}
            style={[
              styles.secondaryButton,
              {
                backgroundColor: colors.surfaceElevated,
                borderColor: colors.border,
              },
            ]}>
            <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
              Join Another Home by Unique ID
            </Text>
          </Pressable>
        </View>
      ) : null}

      {/* 3. Household Members & Unique Home ID Share Card */}
      {isAuthenticated && activeHomeDetail ? (
        <View
          style={[
            styles.card,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          <View style={styles.sectionHeader}>
            <View style={{ flex: 1 }}>
              <Text style={[Typography.subtitle, { color: colors.text }]}>
                Members · {activeHomeDetail.name}
              </Text>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                Share this Unique Home ID so family phones can join directly
              </Text>
            </View>
          </View>

          {/* Unique Home ID + One-Tap Copy ID Button */}
          <View
            style={[
              styles.homeIdBox,
              {
                backgroundColor: colors.surfaceElevated,
                borderColor: colors.border,
              },
            ]}>
            <View style={styles.homeIdTextBlock}>
              <Text style={[Typography.badge, { color: colors.textMuted }]}>
                UNIQUE HOME ID
              </Text>
              <Text
                selectable
                numberOfLines={1}
                style={[styles.homeIdCode, { color: colors.text }]}>
                {activeHomeDetail.id}
              </Text>
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Copy Unique Home ID"
              onPress={() => void handleCopyHomeId(activeHomeDetail.id)}
              style={({ pressed }) => [
                styles.copyIdButton,
                {
                  backgroundColor: copiedId
                    ? colors.statusOkBg
                    : colors.primaryMuted,
                  opacity: pressed ? 0.78 : 1,
                },
              ]}>
              <IconSymbol
                name={copiedId ? 'checkmark' : 'doc.on.doc'}
                size={15}
                color={copiedId ? colors.statusOk : colors.primary}
              />
              <Text
                style={[
                  styles.copyIdText,
                  { color: copiedId ? colors.statusOk : colors.primary },
                ]}>
                {copiedId ? 'Copied!' : 'Copy ID'}
              </Text>
            </Pressable>
          </View>

          <View style={styles.memberStack}>
            {members.map((member) => {
              const memberIsBuyer = member.role === 'buyer';
              const isSelf = user?.id === member.user_id;
              const canRemove = isBuyer || isSelf;

              return (
                <View
                  key={member.id}
                  style={[
                    styles.memberRow,
                    {
                      backgroundColor: colors.surfaceElevated,
                      borderColor: colors.borderSubtle,
                    },
                  ]}>
                  <View
                    style={[
                      styles.memberAvatar,
                      {
                        backgroundColor: memberIsBuyer
                          ? colors.primaryMuted
                          : colors.statusLowBg,
                      },
                    ]}>
                    <Text
                      style={[
                        styles.memberAvatarText,
                        {
                          color: memberIsBuyer
                            ? colors.primary
                            : colors.statusLow,
                        },
                      ]}>
                      {member.username.slice(0, 1).toUpperCase()}
                    </Text>
                  </View>

                  <View style={styles.memberInfo}>
                    <View style={styles.memberNameLine}>
                      <Text
                        numberOfLines={1}
                        style={[Typography.bodySemiBold, { color: colors.text }]}>
                        {member.username}
                        {isSelf ? ' (You)' : ''}
                      </Text>
                      <View
                        style={[
                          styles.rolePill,
                          {
                            backgroundColor: memberIsBuyer
                              ? colors.statusOkBg
                              : colors.statusLowBg,
                          },
                        ]}>
                        <Text
                          style={[
                            Typography.badge,
                            {
                              color: memberIsBuyer
                                ? colors.statusOk
                                : colors.statusLow,
                            },
                          ]}>
                          {memberIsBuyer ? 'Buyer' : 'Consumer'}
                        </Text>
                      </View>
                    </View>
                    <Text
                      numberOfLines={1}
                      style={[Typography.caption, { color: colors.textMuted }]}>
                      {member.email}
                    </Text>
                  </View>

                  {canRemove ? (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={
                        isSelf
                          ? 'Leave household'
                          : `Remove ${member.username} from household`
                      }
                      onPress={() =>
                        void handleRemoveMember(member.user_id, member.username)
                      }
                      disabled={isBusy}
                      style={({ pressed }) => [
                        styles.removeBtn,
                        {
                          backgroundColor: colors.statusFinishedBg,
                          opacity: pressed ? 0.72 : 1,
                        },
                      ]}>
                      <IconSymbol
                        name="trash"
                        size={15}
                        color={colors.statusFinished}
                      />
                    </Pressable>
                  ) : null}
                </View>
              );
            })}
          </View>

          {/* Invite Member Form (Buyer Role Only) */}
          {isBuyer ? (
            <View
              style={[
                styles.inviteBox,
                {
                  backgroundColor: colors.surfaceMuted,
                  borderColor: colors.borderSubtle,
                },
              ]}>
              <View style={styles.inviteHeaderRow}>
                <IconSymbol
                  name="person.badge.plus"
                  size={18}
                  color={colors.primary}
                />
                <Text style={[Typography.cardTitle, { color: colors.text }]}>
                  Invite Member
                </Text>
              </View>

              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                placeholder="Member username or email…"
                placeholderTextColor={colors.textMuted}
                value={inviteIdentifier}
                onChangeText={setInviteIdentifier}
                style={[
                  styles.inlineInput,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                    color: colors.text,
                  },
                ]}
              />

              <View style={styles.roleSelectorRow}>
                {(['consumer', 'buyer'] as HouseholdRole[]).map((roleOpt) => {
                  const selected = inviteRole === roleOpt;
                  return (
                    <Pressable
                      key={roleOpt}
                      onPress={() => setInviteRole(roleOpt)}
                      style={[
                        styles.roleChoicePill,
                        {
                          backgroundColor: selected
                            ? colors.primary
                            : colors.surface,
                          borderColor: selected ? colors.primary : colors.border,
                        },
                      ]}>
                      <Text
                        style={[
                          styles.roleChoiceText,
                          {
                            color: selected
                              ? colors.primaryText
                              : colors.textSecondary,
                          },
                        ]}>
                        {roleOpt === 'buyer' ? 'Buyer' : 'Consumer'}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              <Pressable
                onPress={() => void handleInvite()}
                disabled={isBusy || !inviteIdentifier.trim()}
                style={[
                  styles.primaryButton,
                  {
                    backgroundColor: colors.primary,
                    opacity: isBusy || !inviteIdentifier.trim() ? 0.55 : 1,
                  },
                ]}>
                <Text
                  style={[
                    styles.primaryButtonText,
                    { color: colors.primaryText },
                  ]}>
                  Add to {activeHomeDetail.name}
                </Text>
              </Pressable>
            </View>
          ) : (
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Only household Buyers can invite or remove other members.
            </Text>
          )}
        </View>
      ) : null}

      {/* 4. Appearance Switcher (Dark / Light / System) */}
      <View
        style={[
          styles.card,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.sectionHeader}>
          <Text style={[Typography.subtitle, { color: colors.text }]}>
            Appearance
          </Text>
          <Text style={[Typography.caption, { color: colors.textMuted }]}>
            Saved automatically
          </Text>
        </View>

        <View
          style={[
            styles.segmentedTrack,
            {
              backgroundColor: colors.surfaceMuted,
              borderColor: colors.borderSubtle,
            },
          ]}>
          {THEME_OPTIONS.map((option) => {
            const isSelected = preference === option.value;
            return (
              <Pressable
                key={option.value}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                onPress={() => setPreference(option.value)}
                style={[
                  styles.segmentPill,
                  isSelected && { backgroundColor: colors.primary },
                ]}>
                <Text
                  style={[
                    styles.segmentLabel,
                    {
                      color: isSelected
                        ? colors.primaryText
                        : colors.textSecondary,
                    },
                  ]}>
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text style={[Typography.caption, { color: colors.textSecondary }]}>
          {THEME_OPTIONS.find((opt) => opt.value === preference)?.description}
        </Text>
      </View>

      {/* 5. Sync & National Price Freshness Telemetry */}
      <View
        style={[
          styles.card,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.sectionHeader}>
          <Text style={[Typography.subtitle, { color: colors.text }]}>
            Sync &amp; Price Freshness
          </Text>
          <View
            style={[
              styles.rolePill,
              {
                backgroundColor:
                  status === 'synced'
                    ? colors.statusOkBg
                    : status === 'syncing'
                      ? colors.statusLowBg
                      : colors.statusFinishedBg,
              },
            ]}>
            <Text
              style={[
                Typography.badge,
                {
                  color:
                    status === 'synced'
                      ? colors.statusOk
                      : status === 'syncing'
                        ? colors.statusLow
                        : colors.statusFinished,
                },
              ]}>
              {status === 'synced'
                ? 'Synced'
                : status === 'syncing'
                  ? 'Syncing'
                  : 'Offline'}
            </Text>
          </View>
        </View>

        <View
          style={[
            styles.metaList,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.borderSubtle,
            },
          ]}>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Pending Offline Edits
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {pendingCount}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Last Pantry Sync
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {formatFreshnessTimestamp(lastSyncedAt)}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              National Prices Updated
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {formatFreshnessTimestamp(catalogLastSyncAt)}
            </Text>
          </View>
          {trackedPricesCount !== null ? (
            <View style={styles.metaRow}>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                Tracked Chain Prices
              </Text>
              <Text style={[styles.metaValue, { color: colors.accentSavings }]}>
                {trackedPricesCount} across 5 chains
              </Text>
            </View>
          ) : null}
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              API Host
            </Text>
            <Text
              numberOfLines={1}
              style={[styles.metaValue, { color: colors.textSecondary }]}>
              {getApiBaseUrl()}
            </Text>
          </View>
        </View>

        <Pressable
          onPress={() => void probeBackendHealth()}
          style={[
            styles.secondaryButton,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.border,
            },
          ]}>
          <Text style={[styles.secondaryButtonText, { color: colors.text }]}>
            Refresh Connection &amp; Freshness
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: Spacing.lg,
    gap: Spacing.md,
    paddingBottom: Spacing.xxl + 16,
  },
  feedbackBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  heroCard: {
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.md,
  },
  card: {
    borderRadius: Radii.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  eyebrowBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radii.pill,
  },
  rolePill: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: Radii.pill,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  avatarCircle: {
    width: 44,
    height: 44,
    borderRadius: Radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitial: {
    fontSize: 18,
    fontWeight: '800',
  },
  profileInfo: {
    flex: 1,
    gap: 2,
  },
  signOutPill: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  signOutText: {
    fontSize: 12,
    fontWeight: '800',
  },
  authActionRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  flexButton: {
    flex: 1,
  },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: Spacing.md,
    borderRadius: Radii.pill,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 14,
    fontWeight: '800',
  },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: Spacing.md,
    borderRadius: Radii.pill,
    borderWidth: 1,
    alignItems: 'center',
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  demoLinkBtn: {
    alignItems: 'center',
    paddingVertical: 4,
  },
  homePillWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  homePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  homePillText: {
    fontSize: 13,
    fontWeight: '700',
  },
  inlineFormRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  inlineInput: {
    flex: 1,
    borderRadius: Radii.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    fontSize: 14,
  },
  inlineActionBtn: {
    paddingHorizontal: Spacing.md,
    borderRadius: Radii.md,
    justifyContent: 'center',
  },
  inlineActionText: {
    fontSize: 13,
    fontWeight: '800',
  },
  homeIdBox: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    padding: Spacing.md,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  homeIdTextBlock: {
    flex: 1,
    gap: 3,
  },
  homeIdCode: {
    fontSize: 12,
    fontWeight: '700',
    fontFamily: Platform.select({
      ios: 'Menlo',
      android: 'monospace',
      default: 'monospace',
    }),
  },
  copyIdButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radii.pill,
  },
  copyIdText: {
    fontSize: 12,
    fontWeight: '800',
  },
  memberStack: {
    gap: Spacing.sm,
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm + 2,
    padding: Spacing.md,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  memberAvatar: {
    width: 36,
    height: 36,
    borderRadius: Radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  memberAvatarText: {
    fontSize: 15,
    fontWeight: '800',
  },
  memberInfo: {
    flex: 1,
    gap: 2,
  },
  memberNameLine: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
  },
  removeBtn: {
    width: 32,
    height: 32,
    borderRadius: Radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inviteBox: {
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.sm + 2,
  },
  inviteHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  roleSelectorRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  roleChoicePill: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: Radii.md,
    borderWidth: 1,
    alignItems: 'center',
  },
  roleChoiceText: {
    fontSize: 13,
    fontWeight: '700',
  },
  segmentedTrack: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: Radii.md,
    borderWidth: 1,
    gap: 4,
  },
  segmentPill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: Radii.sm,
    alignItems: 'center',
  },
  segmentLabel: {
    fontSize: 14,
    fontWeight: '700',
  },
  metaList: {
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: Spacing.md,
  },
  metaValue: {
    fontSize: 13,
    fontWeight: '600',
    flexShrink: 1,
    textAlign: 'right',
  },
});
