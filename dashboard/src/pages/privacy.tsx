import { LegalPage, ContactLink } from '@/components/LegalPage';

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="July 7, 2026">
      <p>
        This policy explains what data OfficeGangBot (the Discord bot and its web dashboard — the
        “Service”) collects, why, and what your choices are. It is written to match what the
        Service actually does, in plain language.
      </p>
      <p>
        Data controller: the individual developer operating the Service. Contact:{' '}
        <ContactLink />.
      </p>

      <h2>1. What we collect and why</h2>

      <h3>Server configuration</h3>
      <p>
        Settings that server administrators configure: feature toggles, channel and role IDs,
        thresholds, welcome/rules texts, filter word lists, AutoMod rules, scheduled message
        content, role menus. Collected because the Service cannot work without its configuration.
      </p>

      <h3>Moderation records</h3>
      <p>
        When moderators use the Service’s tools, we store the resulting records: warnings, numbered
        moderation cases, AutoMod strikes, moderator notes, temporary punishments and temporary
        roles, and ban appeals. Each record typically contains the affected member’s Discord user
        ID, the moderator’s ID and name, a reason or note text, and a timestamp. Ban appeals
        additionally contain the text the appealing user submits. These records exist so that
        server staff can moderate consistently; they are visible to the server’s staff, not to
        other members.
      </p>

      <h3>Ticket transcripts</h3>
      <p>
        If a server uses the Tickets feature, the messages written inside a ticket channel are
        captured as a text transcript when the ticket is closed, stored with the ticket record, and
        made available to that server’s staff (and sent to the ticket opener). This is the{' '}
        <strong>only</strong> case where the Service stores conversation content in its database.
      </p>

      <h3>Levels and XP</h3>
      <p>
        If a server uses the Levels feature: your Discord user ID, XP, level, prestige, and display
        name (for leaderboards).
      </p>

      <h3>Aggregate activity statistics</h3>
      <p>
        For the analytics heatmap we count messages per server, per weekday and hour, as plain
        counters. These counters contain <strong>no message content, no author, and no per-message
        timestamps</strong> — only totals like “Monday, 14:00–15:00: 52 messages”.
      </p>

      <h3>Dashboard sign-in</h3>
      <p>
        The dashboard uses Discord OAuth with the <code>identify</code> and <code>guilds</code>{' '}
        scopes: we learn your Discord ID, username, and the list of servers you belong to (to check
        which ones you administer). Your Discord access token is kept in a cookie in your own
        browser (HTTP-only; encrypted at rest when configured) — we do not store it in our
        database. Actions you take in the dashboard (for example issuing a warning or changing a
        setting) are recorded in that server’s audit log with your Discord ID and username, so
        server staff can see who changed what.
      </p>

      <h3>Technical data</h3>
      <p>
        Standard server logs (such as IP addresses in web-server logs) are processed by our hosting
        providers for security and operations. If error tracking is enabled, error reports
        (stack traces and technical context) are sent to Sentry. Short-lived operational data
        (anti-spam counters, cooldowns) is kept in Redis and expires automatically.
      </p>

      <h3>What we do not do</h3>
      <ul>
        <li>
          We do not store your messages in our database (except ticket transcripts, as described
          above). AutoMod inspects messages in real time and may delete them, but does not save
          their content; servers may separately configure Discord-side log channels that quote
          deleted or edited messages inside their own server.
        </li>
        <li>We do not sell or rent any data, and we show no advertising.</li>
        <li>
          The dashboard uses no analytics or tracking cookies — only the functional session cookie
          and a short-lived cookie protecting the sign-in flow.
        </li>
      </ul>

      <h2>2. Legal bases</h2>
      <p>
        Where GDPR or similar laws apply, we process this data to perform the service that server
        administrators request by adding and configuring the bot (performance of a contract /
        legitimate interest in operating a moderation service), and, for optional features, on the
        basis of the server’s configuration choices. You can object or ask questions at the contact
        address above.
      </p>

      <h2>3. Who processes the data</h2>
      <p>We use the following infrastructure providers as processors:</p>
      <ul>
        <li>Discord (the platform itself and its API);</li>
        <li>Railway (bot and API hosting);</li>
        <li>Vercel (dashboard hosting);</li>
        <li>Supabase (PostgreSQL database);</li>
        <li>Upstash (Redis, ephemeral operational data);</li>
        <li>Sentry (error reports, where enabled).</li>
      </ul>
      <p>
        These providers may process data in countries other than yours (including the United
        States) under their own compliance frameworks. We do not share data with anyone else,
        except if legally required.
      </p>

      <h2>4. Retention</h2>
      <ul>
        <li>
          Server data (configuration, moderation records, transcripts, levels) is kept while the
          bot is used on that server, and until deletion is requested.
        </li>
        <li>
          A server owner can request deletion of everything stored for their server after removing
          the bot.
        </li>
        <li>
          AutoMod strikes stop counting after the server’s configured decay window; moderation
          records remain visible to staff until deleted by staff or by a deletion request.
        </li>
        <li>Redis data (spam counters, cooldowns) expires automatically within minutes or hours.</li>
        <li>The dashboard session cookie expires automatically; signing out deletes it and revokes the token.</li>
      </ul>

      <h2>5. Your rights</h2>
      <p>
        Depending on your jurisdiction (for example under the GDPR), you may have the right to
        access, correct, delete, restrict, or receive a copy of your personal data, and to lodge a
        complaint with your data-protection authority. To exercise any of these rights, contact us
        (see “Contact” below) in a way that lets us verify the request relates to you (for
        example, from the Discord account concerned). Note that moderation records are kept
        on behalf of the server that created them; where a request concerns a specific server’s
        records, we may coordinate with that server’s owner.
      </p>

      <h2>6. Children</h2>
      <p>
        The Service is intended for users who meet Discord’s minimum age (13, or older where local
        law requires). We do not knowingly collect data from children below that age.
      </p>

      <h2>7. Security</h2>
      <p>
        Data is transmitted over encrypted connections, access to production systems is restricted,
        dashboard sessions use HTTP-only cookies (encrypted at rest when configured), and dashboard
        management endpoints verify server-administrator permissions on every request. No system is
        perfectly secure; if we learn of a breach affecting your data we will notify affected
        parties as required by law.
      </p>

      <h2>8. Changes</h2>
      <p>
        We may update this policy; the “Last updated” date above reflects the latest revision.
        Material changes will be announced where reasonably possible.
      </p>

      <h2>9. Contact</h2>
      <p>
        Privacy questions and requests: <ContactLink />.
      </p>
    </LegalPage>
  );
}
