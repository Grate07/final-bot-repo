# Grey Discord Bot

Components V2-only moderation and ticket bot using discord.js v14.

## Render
Set these environment variables:
- `TOKEN` — Discord bot token
- `CLIENT_ID` — Discord application/client ID
- `GUILD_ID` — Discord server ID

Start command: `npm start`

The built-in Express server listens on `process.env.PORT` and exposes `/` and `/health`. Use your Render URL + `/health` as the UptimeRobot monitor.

## Setup
1. Edit `config.json` and replace every `PUT_..._HERE` ID.
2. Keep the `accentColor` as `9808686` for Onyx `#0F0F0F`.
3. Invite the bot with the `bot` and `applications.commands` scopes and permissions needed for moderation/tickets.
4. Run the bot. Guild slash commands register automatically from `GUILD_ID`.

## Commands
Slash + configured prefix (`!` by default):
`ban`, `kick`, `mute`, `unmute`, `warn`, `clear`, `ticketpanel`, `set-transcript`, `set-welcome`.

Every command and ticket interaction requires the role configured by `allowedRoleId`.

## Important Discord Developer Portal setting
Because the bot logs message content and edited/deleted messages, enable the **Message Content Intent**. Also enable **Server Members Intent** for welcomes and member moderation events.
