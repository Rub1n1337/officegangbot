import type { AuditEntry } from '@/config/types/custom-types';
import type { Languages } from '@/config/translations/provider';

/** Relative "time ago" for a nullable ISO timestamp. Empty string when absent/invalid. */
export function timeAgo(iso: string | null, lang: Languages = 'ru'): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.max(0, Math.floor((Date.now() - d) / 1000));
  const ru = lang === 'ru';
  if (s < 60) return ru ? 'только что' : 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return ru ? `${m} мин назад` : `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return ru ? `${h} ч назад` : `${h} h ago`;
  const days = Math.floor(h / 24);
  return ru ? `${days} д назад` : `${days} d ago`;
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
const AUDIT_LABEL: Record<Languages, Record<string, (e: AuditEntry) => string>> = {
  ru: {
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
  },
  en: {
    warn: () => 'issued a warning',
    mute: () => 'muted a member',
    unmute: () => 'unmuted a member',
    kick: () => 'kicked a member',
    ban: () => 'banned a member',
    enable_feature: (e) => `enabled ${e.target ?? 'a feature'}`,
    disable_feature: (e) => `disabled ${e.target ?? 'a feature'}`,
    update_feature: (e) => `updated ${e.target ?? 'feature'} settings`,
    set_locale: (e) => `changed the bot language to ${e.detail ?? ''}`.trim(),
    delete_warning: () => 'deleted a warning',
  },
};

// Short labels for the action-filter dropdown.
const ACTION_LABEL: Record<Languages, Record<string, string>> = {
  ru: {
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
  },
  en: {
    warn: 'Warning',
    mute: 'Mute',
    unmute: 'Unmute',
    kick: 'Kick',
    ban: 'Ban',
    enable_feature: 'Feature enabled',
    disable_feature: 'Feature disabled',
    update_feature: 'Feature updated',
    set_locale: 'Language change',
    delete_warning: 'Warning deleted',
  },
};

export function describeAudit(e: AuditEntry, lang: Languages = 'ru'): string {
  const f = AUDIT_LABEL[lang][e.action];
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

/** Short label for the action itself (for the filter dropdown). */
export function actionLabel(action: string, lang: Languages = 'ru'): string {
  if (ACTION_LABEL[lang][action]) return ACTION_LABEL[lang][action];
  const s = action.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Serialize audit entries to CSV (RFC-4180 quoting) for export. Prefixed with a
 * BOM so Excel reads the UTF-8 correctly. */
export function auditToCsv(entries: AuditEntry[], lang: Languages = 'ru'): string {
  const esc = (v: string | null | undefined): string => {
    const s = v == null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = ['Timestamp', 'Actor', 'Action', 'Description', 'Target', 'Detail'];
  const lines = [header.join(',')];
  for (const e of entries) {
    lines.push(
      [e.createdAt ?? '', e.actorName ?? '', e.action, describeAudit(e, lang), e.target ?? '', e.detail ?? '']
        .map(esc)
        .join(',')
    );
  }
  return '﻿' + lines.join('\r\n');
}
