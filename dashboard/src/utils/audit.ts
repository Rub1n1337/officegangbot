import type { AuditEntry } from '@/config/types/custom-types';

/** Relative "time ago" for a nullable ISO timestamp. Empty string when absent/invalid. */
export function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.max(0, Math.floor((Date.now() - d) / 1000));
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** Absolute, locale-aware date-time for a nullable ISO timestamp. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Maps an audit action to a human sentence, using the entry's target/detail. */
export const AUDIT_LABEL: Record<string, (e: AuditEntry) => string> = {
  warn: () => 'warned a member',
  mute: () => 'muted a member',
  unmute: () => 'removed a timeout',
  kick: () => 'kicked a member',
  ban: () => 'banned a member',
  enable_feature: (e) => `enabled ${e.target ?? 'a feature'}`,
  disable_feature: (e) => `disabled ${e.target ?? 'a feature'}`,
  update_feature: (e) => `updated ${e.target ?? 'a feature'} settings`,
  set_locale: (e) => `set the bot language to ${e.detail ?? ''}`.trim(),
  delete_warning: () => 'deleted a warning',
};

export function describeAudit(e: AuditEntry): string {
  const f = AUDIT_LABEL[e.action];
  return f ? f(e) : e.action.replace(/_/g, ' ');
}

/** Moderation actions whose `detail` (reason) is worth surfacing. */
const MODERATION_ACTIONS = new Set(['warn', 'mute', 'unmute', 'kick', 'ban']);

export function isModerationAction(action: string): boolean {
  return MODERATION_ACTIONS.has(action);
}

/** Chakra colorScheme for an action badge, grouped by kind. */
export function auditActionColor(action: string): string {
  if (action === 'ban' || action === 'kick') return 'red';
  if (action === 'warn' || action === 'mute') return 'orange';
  if (action === 'unmute' || action === 'delete_warning' || action.startsWith('enable')) return 'green';
  if (action.startsWith('disable')) return 'gray';
  return 'purple';
}

/** Short label for the action itself, e.g. "delete_warning" -> "Delete warning". */
export function actionLabel(action: string): string {
  const s = action.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}
