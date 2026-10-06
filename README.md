# Runcandels

Runcandels is a Node.js Discord moderation + ticket bot built around Discord Components V2 and a pure Onyx visual theme.

## Render

**Build Command**
```text
npm install
```

**Start Command**
```text
npm start
```

Required Render environment variables:
```text
TOKEN=YOUR_DISCORD_BOT_TOKEN
CLIENT_ID=YOUR_DISCORD_APPLICATION_ID
GUILD_ID=YOUR_DISCORD_SERVER_ID
```

UptimeRobot URL:
```text
https://YOUR-RENDER-SERVICE.onrender.com/health
```

The Express server listens on `process.env.PORT` and exposes `/` and `/health`.

## Discord Developer Portal

Enable these privileged intents under **Bot → Privileged Gateway Intents**:
- Server Members Intent
- Message Content Intent

Invite the bot with:
- `bot`
- `applications.commands`

Recommended bot permissions:
- View Channels
- Send Messages
- Read Message History
- Manage Channels
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members
- Attach Files

## config.json

Replace every `PUT_..._HERE` value with your real Discord IDs.

`accentColor` is `986895`, which is the decimal value of `0x0F0F0F` (Onyx).

## Commands

All commands are restricted to `allowedRoleId`.

### Moderation
- `/ban` / `!ban` — ban a member.
- `/kick` / `!kick` — kick a member.
- `/mute` / `!mute` — timeout a member.
- `/unmute` / `!unmute` — remove a timeout.
- `/warn` / `!warn` — write a warning to the moderation log.
- `/clear` / `!clear` — bulk-delete up to 100 recent messages.

### Tickets
- `/ticketpanel` / `!ticketpanel` — post the Runcandels Ticket Desk.
- Users select General Support, Query System, or Report Issue, then complete an Issue modal.
- Ticket channels are private to the ticket owner + support role + bot.
- Ticket panel and ticket messages use Components V2 with Onyx accenting.
- Close buttons are exactly: `Close` and `Close with reason`.
- Closing creates an HTML transcript containing up to 100 messages and sends it to `transcriptChannelId`.

### Configuration
- `/set-transcript` / `!set-transcript` — set transcript channel.
- `/set-welcome` / `!set-welcome` — set welcome channel.
- `/test-welcome` / `!test-welcome` — send a test welcome.
- `/help` / `!help` — show the complete command guide.

## Important

If slash commands appear but do not respond, check the Render logs for `[SLASH] Successfully registered` and make sure `CLIENT_ID`, `GUILD_ID`, and `TOKEN` are correct.

If `!` commands do not respond, make sure **Message Content Intent** is enabled in the Discord Developer Portal and the user has the role configured in `allowedRoleId`.
