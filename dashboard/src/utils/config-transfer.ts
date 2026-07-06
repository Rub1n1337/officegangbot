// Config export/import for guild settings. Only *portable* values transfer —
// texts, thresholds, toggles and AutoMod rules. Channel/role ids never do:
// they're meaningless on another server, so they are excluded from the export
// and, on import, the portable subset is merged over the target guild's
// current payload (preserving its own ids) before being saved through the
// normal, validated update path.

export const TRANSFER_VERSION = 1;

// Whitelist of portable keys per feature. Anything not listed here is dropped
// both on export and on import (so a hand-crafted file can't inject id fields).
export const PORTABLE_KEYS: Record<string, string[]> = {
  'automod': [
    'blockInvites', 'blockLinks', 'allowedDomains', 'blockMassMentions',
    'spamCount', 'spamWindow', 'mentionLimit',
    'strikesEnabled', 'strikeExpiryHours', 'strikeMuteAt', 'strikeKickAt', 'strikeBanAt',
    'dryRun', 'rules', 'bannedWords',
  ],
  'moderation': [
    'warnEscalationEnabled', 'warnExpiryHours', 'warnMuteAt', 'warnKickAt', 'warnBanAt',
  ],
  'anti-raid': ['joinCount', 'joinWindow', 'action', 'duration'],
  'tickets': ['autoCloseHours'],
  'levels': ['voiceXpEnabled', 'voiceXpPerMin', 'xpMultiplier', 'prestigeLevel'],
  'welcome-message': ['message'],
  'rules': ['message'],
};

export const TRANSFER_FEATURES = Object.keys(PORTABLE_KEYS);

function pick(obj: Record<string, unknown>, keys: string[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const k of keys) {
    if (obj != null && k in obj && obj[k] !== undefined) out[k] = obj[k];
  }
  return out;
}

export type TransferFile = {
  app: 'officegangbot';
  version: number;
  exportedAt: string;
  features: Record<string, Record<string, unknown>>;
};

/** Builds the export file from fetched feature payloads (already keyed by feature id). */
export function buildExport(payloads: Record<string, Record<string, unknown>>): TransferFile {
  const features: Record<string, Record<string, unknown>> = {};
  for (const [feature, keys] of Object.entries(PORTABLE_KEYS)) {
    const payload = payloads[feature];
    if (payload) features[feature] = pick(payload, keys);
  }
  return {
    app: 'officegangbot',
    version: TRANSFER_VERSION,
    exportedAt: new Date().toISOString(),
    features,
  };
}

/**
 * Parses + sanitizes an import file. Returns only known features, each reduced
 * to its portable-keys whitelist, or an error string.
 */
export function parseImport(raw: string):
  | { ok: true; features: Record<string, Record<string, unknown>> }
  | { ok: false; error: string } {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return { ok: false, error: 'Not a valid JSON file.' };
  }
  const file = data as Partial<TransferFile>;
  if (file?.app !== 'officegangbot' || typeof file.features !== 'object' || file.features == null) {
    return { ok: false, error: 'Not an OfficeGangBot config export.' };
  }
  if ((file.version ?? 0) > TRANSFER_VERSION) {
    return { ok: false, error: 'This export was made by a newer version of the dashboard.' };
  }
  const incoming: Record<string, unknown> = { ...(file.features as Record<string, unknown>) };
  // Legacy: exports made before the word filter merged into AutoMod carried a
  // 'filter' feature with { words } — map it onto automod.bannedWords.
  const legacyFilter = incoming['filter'] as Record<string, unknown> | undefined;
  if (legacyFilter && Array.isArray(legacyFilter.words)) {
    incoming['automod'] = {
      ...((incoming['automod'] as Record<string, unknown>) ?? {}),
      bannedWords: legacyFilter.words,
    };
  }
  const features: Record<string, Record<string, unknown>> = {};
  for (const [feature, keys] of Object.entries(PORTABLE_KEYS)) {
    const subset = incoming[feature];
    if (subset && typeof subset === 'object') {
      const picked = pick(subset as Record<string, unknown>, keys);
      if (Object.keys(picked).length > 0) features[feature] = picked;
    }
  }
  if (Object.keys(features).length === 0) {
    return { ok: false, error: 'The file contains no importable settings.' };
  }
  return { ok: true, features };
}
