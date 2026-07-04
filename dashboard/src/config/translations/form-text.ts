import { provider } from './provider';

// Russian translations for the feature-form UI strings (labels, descriptions,
// placeholders, section headers, buttons). Keyed by the exact English source so
// a missing entry falls back to English automatically — and cn/en render the
// source as-is. This lets us localize the form internals without threading
// translation keys through every form component.
const RU: Record<string, string> = {
  // --- Shared ---------------------------------------------------------------
  Channel: 'Канал',
  Role: 'Роль',
  Level: 'Уровень',
  Message: 'Сообщение',
  Title: 'Заголовок',
  Description: 'Описание',

  // --- AutoMod --------------------------------------------------------------
  'Content filter': 'Контент-фильтр',
  'Block invite links': 'Блокировать инвайты',
  'Delete messages containing Discord invite links (discord.gg/…).':
    'Удалять сообщения со ссылками-приглашениями Discord (discord.gg/…).',
  'Block external links': 'Блокировать внешние ссылки',
  'Delete messages that contain links, except to the allowed domains below.':
    'Удалять сообщения со ссылками, кроме разрешённых доменов ниже.',
  'Allowed domains': 'Разрешённые домены',
  'Links to these domains (and their subdomains) are allowed.':
    'Ссылки на эти домены (и их поддомены) разрешены.',
  'e.g. youtube.com — press Enter to add': 'напр. youtube.com — Enter, чтобы добавить',
  'Block @everyone / @here': 'Блокировать @everyone / @here',
  'Delete messages that mention @everyone or @here.':
    'Удалять сообщения с упоминанием @everyone или @here.',
  'Anti-spam & mentions': 'Анти-спам и упоминания',
  'These limits run whenever AutoMod is enabled. Tune the thresholds to fit your server.':
    'Эти лимиты работают, пока включён AutoMod. Настройте пороги под свой сервер.',
  'Spam message threshold': 'Порог спама (сообщений)',
  'Messages within the window that trigger a 10-minute timeout.':
    'Сколько сообщений за окно вызывает таймаут на 10 минут.',
  'Spam window (seconds)': 'Окно спама (секунды)',
  'Time window the spam threshold is measured over.':
    'Промежуток времени, за который считается порог спама.',
  'Mention limit': 'Лимит упоминаний',
  'Delete a message with more than this many user/role mentions.':
    'Удалять сообщение, где упоминаний пользователей/ролей больше этого числа.',
  'Warning auto-escalation': 'Авто-эскалация предупреждений',
  'Automatically mute/kick/ban a member once their warnings reach a threshold.':
    'Автоматически мут/кик/бан участнику при достижении порога предупреждений.',
  'Mute at (warnings)': 'Мут при (предупреждений)',
  'Timeout the member for 10 minutes at this many warnings. 0 = off.':
    'Таймаут на 10 минут при таком числе предупреждений. 0 = выкл.',
  'Kick at (warnings)': 'Кик при (предупреждений)',
  'Kick the member at this many warnings. 0 = off.':
    'Кикнуть участника при таком числе предупреждений. 0 = выкл.',
  'Ban at (warnings)': 'Бан при (предупреждений)',
  'Ban the member at this many warnings. 0 = off.':
    'Забанить участника при таком числе предупреждений. 0 = выкл.',
  'Warning expiry (hours)': 'Срок предупреждения (часы)',
  'Warnings older than this stop counting toward escalation. 0 = never expire.':
    'Предупреждения старше этого срока не учитываются в эскалации. 0 = не сгорают.',
  'Exemptions': 'Исключения',
  'Channels and roles listed here are ignored by AutoMod entirely.':
    'Каналы и роли из этого списка полностью игнорируются AutoMod.',
  'Ignored channels': 'Игнорируемые каналы',
  'AutoMod skips messages in these channels (and their categories).':
    'AutoMod пропускает сообщения в этих каналах (и их категориях).',
  'Ignored roles': 'Игнорируемые роли',
  'Members with any of these roles bypass AutoMod.':
    'Участники с любой из этих ролей не проверяются AutoMod.',
  'Dry-run (test mode)': 'Пробный режим (без действий)',
  'Detect and log violations to your log channel without deleting messages, timing out members or adding strikes. Use it to tune your rules safely before enforcing them.':
    'Находит и записывает нарушения в лог-канал, но не удаляет сообщения, не выдаёт таймауты и не начисляет страйки. Удобно, чтобы безопасно настроить правила перед включением.',
  'Dry-run is on — AutoMod will only log what it would do (needs the Logging feature and a punishment log channel). No messages are deleted and no strikes are added.':
    'Пробный режим включён — AutoMod только записывает, что сделал бы (нужны функция «Логирование» и канал лога наказаний). Сообщения не удаляются, страйки не начисляются.',
  'Auto-close after inactivity (hours)': 'Автозакрытие при простое (часы)',
  'Idle tickets close automatically after this many hours.':
    'Неактивные тикеты закрываются автоматически через столько часов.',
  '0 = never auto-close.': '0 = не закрывать автоматически.',
  'Single-select (exclusive)': 'Только один вариант (эксклюзивно)',
  'Members can hold only one role from this menu — picking another swaps it.':
    'Из этого меню участник может держать только одну роль — выбор другой заменит текущую.',
  'Strike system': 'Система страйков',
  'Enable strikes': 'Включить страйки',
  'Every AutoMod violation adds a strike; crossing a threshold escalates the punishment.':
    'Каждое нарушение AutoMod добавляет страйк; при достижении порога наказание усиливается.',
  'Strike expiry (hours)': 'Срок страйка (часы)',
  'Strikes older than this stop counting. 0 = never expire.':
    'Страйки старше этого срока перестают считаться. 0 = не сгорают.',
  'Mute at (strikes)': 'Мут при (страйков)',
  'Timeout the member for 10 minutes at this many strikes. 0 = off.':
    'Таймаут на 10 минут при таком числе страйков. 0 = выкл.',
  'Kick at (strikes)': 'Кик при (страйков)',
  'Kick the member at this many strikes. 0 = off.':
    'Кикнуть участника при таком числе страйков. 0 = выкл.',
  'Ban at (strikes)': 'Бан при (страйков)',
  'Ban the member at this many strikes. 0 = off.':
    'Забанить участника при таком числе страйков. 0 = выкл.',
  'Custom filters (regex)': 'Свои фильтры (regex)',
  'Delete messages matching a pattern. “Strike” also adds a strike (when strikes are on). Up to 25 rules.':
    'Удалять сообщения по шаблону. «Страйк» ещё и добавляет страйк (если страйки включены). До 25 правил.',
  'Add rule': 'Добавить правило',
  'No custom filters yet.': 'Пока нет своих фильтров.',
  'regex pattern, e.g. free\\s*nitro': 'regex-шаблон, напр. free\\s*nitro',
  Delete: 'Удалить',
  Strike: 'Страйк',
  'Members with “Manage Messages” bypass all AutoMod rules. Actions are recorded in your punishment log when the Logging feature is enabled.':
    'Участники с правом «Управление сообщениями» обходят все правила AutoMod. Действия пишутся в лог наказаний, если включено Логирование.',

  // --- Levels ---------------------------------------------------------------
  How: 'Как',
  'looks to members': 'выглядит для участников',
  Season: 'Сезон',
  'Level-up announcement channel': 'Канал анонса повышения уровня',
  'Where to post when a member levels up. Leave unset to announce in the channel they were chatting in.':
    'Куда писать при повышении уровня. Оставьте пустым — анонс будет в канале, где участник общался.',
  'Voice XP': 'Опыт за войс',
  'End the current season with': 'Завершите текущий сезон командой',
  '— standings are archived (see': '— результаты архивируются (см.',
  ") and everyone's XP resets, keeping prestige.":
    '), а опыт всех сбрасывается, престиж сохраняется.',
  'Award XP every minute to members active in a voice channel (not alone, not deafened).':
    'Выдавать опыт каждую минуту активным в войсе (не в одиночку, без выкл. звука).',
  'Voice XP per minute': 'Опыт за минуту в войсе',
  'Base XP granted each minute in voice (before multipliers).':
    'Базовый опыт за минуту в войсе (до множителей).',
  'XP multipliers': 'Множители опыта',
  "A member's XP is multiplied by the global value times their best role multiplier.":
    'Опыт участника умножается на глобальный множитель и лучший множитель его ролей.',
  'Global multiplier': 'Глобальный множитель',
  'Applies to all XP (e.g. 2 for a double-XP weekend). 0.1–10.':
    'Применяется ко всему опыту (напр. 2 — двойной опыт на выходных). 0.1–10.',
  'Stacks with the per-role multipliers below: a member’s XP = base × this × their best role multiplier.':
    'Складывается с множителями по ролям ниже: опыт участника = база × этот множитель × лучший множитель его ролей.',
  'Prestige level': 'Уровень престижа',
  'Members can /prestige at this level. 0 disables prestige.':
    'На этом уровне участники могут /prestige. 0 отключает престиж.',
  'Per-role multipliers': 'Множители по ролям',
  'Give boosters or supporters bonus XP.': 'Давайте бустерам или саппортерам бонусный опыт.',
  'Add role': 'Добавить роль',
  'Members with this role': 'Участники с этой ролью',
  Multiplier: 'Множитель',
  '0.1–10 (e.g. 2 = double XP)': '0.1–10 (напр. 2 = двойной опыт)',
  'Role rewards': 'Награды-роли',
  'Automatically grant a role when a member reaches a level.':
    'Автоматически выдавать роль при достижении уровня.',
  'No role rewards yet. Add one below.': 'Пока нет наград-ролей. Добавьте ниже.',
  'Reach this level to earn the role': 'Достигните этого уровня, чтобы получить роль',
  'Role to grant at this level': 'Роль, выдаваемая на этом уровне',
  'Add reward': 'Добавить награду',

  // --- Filter ---------------------------------------------------------------
  'Filtered Words': 'Запрещённые слова',
  'Words to automatically delete. Case-insensitive; duplicates are removed.':
    'Слова для автоудаления. Без учёта регистра; дубликаты удаляются.',
  'Type a word and press Enter': 'Введите слово и нажмите Enter',

  // --- Logging --------------------------------------------------------------
  'Punishment Log Channel': 'Канал лога наказаний',
  'Bans, kicks, mutes, warns and filtered messages':
    'Баны, кики, муты, предупреждения и отфильтрованные сообщения',
  'Command Usage Log Channel': 'Канал лога команд',
  'Logs every bot command that is run': 'Логирует каждую запущенную команду бота',
  'Message Log Channel': 'Канал лога сообщений',
  'Edited and deleted messages': 'Изменённые и удалённые сообщения',
  'Leave Log Channel': 'Канал лога выходов',
  'Notifications when a member leaves': 'Уведомления, когда участник покидает сервер',

  // --- Moderation (permission roles) ---------------------------------------
  'Grant roles access to each moderation command. Server administrators always have full access.':
    'Дайте ролям доступ к каждой команде модерации. Администраторы сервера всегда имеют полный доступ.',
  Config: 'Настройки',
  'Can use /config and /setup': 'Может использовать /config и /setup',
  Kick: 'Кик',
  'Can use /kick': 'Может использовать /kick',
  Ban: 'Бан',
  'Can use /ban and /unban': 'Может использовать /ban и /unban',
  Mute: 'Мут',
  'Can use /mute and /unmute': 'Может использовать /mute и /unmute',
  Warn: 'Предупреждение',
  'Can use /warn, /warnings, /clearwarnings':
    'Может использовать /warn, /warnings, /clearwarnings',
  Clear: 'Очистка',
  'Can use /clear (bulk-delete)': 'Может использовать /clear (массовое удаление)',

  // --- Reaction menus -------------------------------------------------------
  'No role menus yet. Add one and the bot will post an embed members can react to for roles.':
    'Пока нет меню ролей. Добавьте — бот опубликует эмбед, на который участники реагируют для получения ролей.',
  Roles: 'Роли',
  'No roles yet. Add an emoji → role pair below.':
    'Пока нет ролей. Добавьте пару эмодзи → роль ниже.',
  'Add menu': 'Добавить меню',
  'Where the menu message is posted': 'Где публикуется сообщение меню',
  'Heading of the menu embed': 'Заголовок эмбеда меню',
  'Pick your roles': 'Выберите свои роли',
  'Shown above the role list (optional).': 'Показывается над списком ролей (необязательно).',
  'React below to choose your roles.': 'Реагируйте ниже, чтобы выбрать роли.',

  // --- Reaction role --------------------------------------------------------
  'No reaction roles yet. Add one to grant a role when a member reacts to a message.':
    'Пока нет ролей за реакцию. Добавьте, чтобы выдавать роль за реакцию на сообщение.',
  'Preview: React': 'Превью: реакция',
  '→ get': '→ выдать',
  'a role': 'роль',
  'Add reaction role': 'Добавить роль за реакцию',
  'Channel containing the message': 'Канал, где находится сообщение',
  'Message ID': 'ID сообщения',
  'Developer Mode → right-click the message → Copy Message ID.':
    'Режим разработчика → ПКМ по сообщению → «Копировать ID сообщения».',
  'Turn on Developer Mode in Discord (User Settings → Advanced). Then right-click (or long-press on mobile) the message and choose “Copy Message ID”. It is an 18–19 digit number.':
    'Включите режим разработчика в Discord (Настройки → Расширенные). Затем ПКМ (или долгое нажатие на телефоне) по сообщению → «Копировать ID сообщения». Это число из 18–19 цифр.',
  Emoji: 'Эмодзи',
  'Emoji members react with': 'Эмодзи, которым реагируют участники',
  'Role to grant on reaction': 'Роль, выдаваемая за реакцию',

  // --- Rules ----------------------------------------------------------------
  'Rules Channel': 'Канал правил',
  'Select the channel where rules will be posted':
    'Выберите канал, где будут опубликованы правила',
  'Rules Message': 'Текст правил',
  'Enter the server rules. A scrollbar appears when the text is longer than the box.':
    'Введите правила сервера. Полоса прокрутки появится, если текст длиннее поля.',
  'Be respectful...': 'Будьте вежливы...',
  'Reaction Role': 'Роль за реакцию',
  'Add a reaction to the rules message that grants a role when clicked':
    'Добавить реакцию к сообщению с правилами, выдающую роль при нажатии',
  'Reaction Emoji': 'Эмодзи реакции',
  'Emoji members react with to accept the rules':
    'Эмодзи, которым участники соглашаются с правилами',
  'Role granted when a member reacts': 'Роль, выдаваемая при реакции участника',

  // --- Scheduled messages ---------------------------------------------------
  'No scheduled messages yet. Add one to post an announcement at a set time (optionally repeating daily or weekly).':
    'Пока нет отложенных сообщений. Добавьте, чтобы опубликовать анонс в заданное время (по желанию — с повтором ежедневно или еженедельно).',
  Active: 'Активно',
  Paused: 'На паузе',
  Repeat: 'Повтор',
  'Add scheduled message': 'Добавить отложенное сообщение',
  'Where to post the message': 'Куда отправлять сообщение',
  'Date & time (your local time)': 'Дата и время (по вашему местному времени)',
  'When to first post it': 'Когда отправить впервые',
  'Entered in your browser’s timezone and converted automatically — the bot posts at that exact moment. Recurring schedules repeat from this time.':
    'Указывается в часовом поясе вашего браузера и конвертируется автоматически — бот отправит ровно в этот момент. Повторяющиеся расписания считаются от этого времени.',
  'Up to 2000 characters.': 'До 2000 символов.',
  '📢 Weekly reminder: read the rules and have a great week!':
    '📢 Еженедельное напоминание: прочтите правила и хорошей недели!',
  Once: 'Один раз',
  Daily: 'Ежедневно',
  Weekly: 'Еженедельно',

  // --- Tickets --------------------------------------------------------------
  'Support role': 'Роль поддержки',
  'Role that can see and respond to ticket channels':
    'Роль, которая видит тикеты и может отвечать в них',
  'Ticket category': 'Категория тикетов',
  'New ticket channels are created under this category':
    'Новые каналы тикетов создаются в этой категории',

  // --- Welcome --------------------------------------------------------------
  'Where to send the welcome message': 'Куда отправлять приветствие',
  'The welcome message. Use {user.mention} to mention the new member and {server.name} for the server name.':
    'Текст приветствия. {user.mention} — упоминание нового участника, {server.name} — название сервера.',
  "Welcome {user.mention} to {server.name}! We're glad to have you.":
    'Добро пожаловать, {user.mention}, на {server.name}! Рады тебя видеть.',
  'Auto-role (optional)': 'Авто-роль (необязательно)',
  'Automatically given to every member when they join.':
    'Автоматически выдаётся каждому участнику при входе.',
};

export function useFormText() {
  const lang = provider.useLang();
  return (en: string): string => (lang === 'ru' ? RU[en] ?? en : en);
}
