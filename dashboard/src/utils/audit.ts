import type { AuditEntry } from '@/config/types/custom-types';

/** Relative "time ago" for a nullable ISO timestamp. Empty string when absent/invalid. */
export function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.max(0, Math.floor((Date.now() - d) / 1000));
  if (s < 60) return 'только что';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} мин назад`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ч назад`;
  return `${Math.floor(h / 24)} д назад`;
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
  warn: () => 'выдал предупреждение',
  mute: () => 'замутил участника',
  unmute: () => 'снял мут',
  kick: () => 'кикнул участника',
  ban: () => 'забанил участника',
  enable_feature: (e) => `включил ${e.target ?? 'функцию'}`,
  disable_feature: (e) => `выключил ${e.target ?? 'функцию'}`,
  update_feature: (e) => `изменил настройки ${e.target ?? 'функции'}`,
  set_locale: (e) => `сменил язык бота на ${e.detail ?? ''}`.trim(),
  delete_warning: () => 'удалил предупреждение',
};

// Russian short labels for the action-filter dropdown.
const ACTION_LABEL_RU: Record<string, string> = {
  warn: 'Предупреждение',
  mute: 'Мут',
  unmute: 'Снятие мута',
  kick: 'Кик',
  ban: 'Бан',
  enable_feature: 'Включение функции',
  disable_feature: 'Выключение функции',
  update_feature: 'Изменение функции',
  set_locale: 'Смена языка',
  delete_warning: 'Удаление предупреждения',
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

/** Short Russian label for the action itself (for the filter dropdown). */
export function actionLabel(action: string): string {
  if (ACTION_LABEL_RU[action]) return ACTION_LABEL_RU[action];
  const s = action.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Serialize audit entries to CSV (RFC-4180 quoting) for export. Prefixed with a
 * BOM so Excel reads the UTF-8 correctly. */
export function auditToCsv(entries: AuditEntry[]): string {
  const esc = (v: string | null | undefined): string => {
    const s = v == null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = ['Timestamp', 'Actor', 'Action', 'Description', 'Target', 'Detail'];
  const lines = [header.join(',')];
  for (const e of entries) {
    lines.push(
      [e.createdAt ?? '', e.actorName ?? '', e.action, describeAudit(e), e.target ?? '', e.detail ?? '']
        .map(esc)
        .join(',')
    );
  }
  return '﻿' + lines.join('\r\n');
}
