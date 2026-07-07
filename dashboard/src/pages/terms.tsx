import Link from 'next/link';
import { LegalPage, LEGAL_CONTACT_EMAIL } from '@/components/LegalPage';

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" updated="July 7, 2026">
      <p>
        These Terms of Service (“Terms”) govern your use of OfficeGangBot — a Discord moderation
        bot and its companion web dashboard (together, the “Service”). By adding the bot to a
        Discord server, interacting with it, or signing in to the dashboard, you agree to these
        Terms. If you do not agree, do not use the Service.
      </p>
      <p>
        The Service is operated by an individual developer (“we”, “us”). Contact:{' '}
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>.
      </p>

      <h2>1. The Service</h2>
      <p>
        OfficeGangBot provides server-management features for Discord communities, including
        moderation commands and records (warnings, cases, strikes, notes), automatic moderation
        (spam, link and word filtering, raid protection), support tickets with transcripts, member
        levels and XP, role menus, verification, scheduled messages, welcome messages, logging,
        analytics, and a web dashboard for configuring these features.
      </p>
      <p>
        The Service is provided free of charge. There are no paid features, subscriptions, or
        purchases.
      </p>

      <h2>2. Eligibility and Discord’s terms</h2>
      <ul>
        <li>
          You must comply with Discord’s{' '}
          <a href="https://discord.com/terms" rel="noreferrer" target="_blank">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="https://discord.com/guidelines" rel="noreferrer" target="_blank">
            Community Guidelines
          </a>{' '}
          when using the Service.
        </li>
        <li>
          You must meet the minimum age required by Discord (13, or older where your local law
          requires).
        </li>
        <li>
          Signing in to the dashboard requires a Discord account; dashboard management features are
          available only to administrators of the relevant server.
        </li>
      </ul>

      <h2>3. Server administrators</h2>
      <p>
        Moderation actions performed by the bot (for example warnings, timeouts, kicks, bans,
        message deletion, anti-raid measures) are configured and triggered by the administrators
        and moderators of each server. The bot acts on their behalf. We do not review, approve, or
        take responsibility for moderation decisions made in individual servers; disputes about
        such decisions should be raised with that server’s staff (for bans, the bot may offer an
        appeal form where the server has enabled it).
      </p>
      <p>Administrators are responsible for:</p>
      <ul>
        <li>configuring the bot in line with their community’s rules and applicable law;</li>
        <li>
          informing their members, where required, that moderation records and ticket transcripts
          are kept (see the <Link href="/privacy">Privacy Policy</Link>);
        </li>
        <li>the content of any messages the bot posts on their instruction (welcome messages, rules, scheduled announcements).</li>
      </ul>

      <h2>4. Acceptable use</h2>
      <p>You must not:</p>
      <ul>
        <li>use the Service to break the law, Discord’s terms, or the rights of others;</li>
        <li>
          attempt to disrupt, overload, probe, or gain unauthorized access to the Service, its API,
          or its infrastructure;
        </li>
        <li>attempt to bypass the Service’s permission checks or act on servers you do not administer;</li>
        <li>scrape, resell, or repackage the Service or its data without our written permission;</li>
        <li>use the Service to harass, defraud, or harm other users.</li>
      </ul>
      <p>
        We may restrict, suspend, or remove the Service from any server, or block any user, if we
        reasonably believe these Terms are being violated or the Service is being abused.
      </p>

      <h2>5. Availability and changes</h2>
      <p>
        The Service is provided “as is” and “as available”, without any warranty of uninterrupted
        operation. We may add, change, or remove features, and may suspend or discontinue the
        Service (in whole or in part) at any time. Where reasonably possible we will give notice of
        significant changes, but we are not obliged to maintain any particular feature.
      </p>

      <h2>6. Intellectual property</h2>
      <p>
        The Service’s software, name, and branding belong to us or our licensors. Content created
        by you or your community (messages, rules text, configuration) remains yours; you grant us
        the limited right to store and process it as needed to operate the Service.
      </p>

      <h2>7. Disclaimer and limitation of liability</h2>
      <p>
        To the maximum extent permitted by applicable law: the Service is provided without
        warranties of any kind, express or implied; and we are not liable for indirect, incidental,
        special, or consequential damages, loss of data, or loss arising from moderation decisions
        made by server staff, third-party outages (including Discord or our hosting providers), or
        your use of or inability to use the Service. Nothing in these Terms excludes liability that
        cannot be excluded under applicable law, including mandatory consumer-protection rights in
        your country of residence.
      </p>

      <h2>8. Termination</h2>
      <p>
        Server owners can stop using the Service at any time by removing the bot from their server.
        You may request deletion of stored data as described in the{' '}
        <Link href="/privacy">Privacy Policy</Link>. We may terminate or suspend access as
        described in section 4.
      </p>

      <h2>9. Changes to these Terms</h2>
      <p>
        We may update these Terms from time to time. The “Last updated” date above reflects the
        latest revision. Material changes will be announced where reasonably possible (for example
        in the dashboard or the support channel). Continued use of the Service after changes take
        effect constitutes acceptance of the updated Terms.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about these Terms:{' '}
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>.
      </p>
    </LegalPage>
  );
}
