const express = require('express');
const fs = require('fs');
const path = require('path');
const {
  Client,
  GatewayIntentBits,
  Partials,
  REST,
  Routes,
  MessageFlags
} = require('discord.js');
const config = require('./config.json');
const { componentsPayload } = require('./utils/ui');
const { handleInteraction } = require('./utils/ticketHandler');
const { modLog } = require('./utils/logger');
const { sendWelcome } = require('./utils/welcome');

// -------------------- Render / UptimeRobot --------------------
const app = express();
const PORT = Number(process.env.PORT) || 3000;

app.get('/', (_req, res) => res.status(200).send('Runcandels is online.'));
app.get('/health', (_req, res) => res.status(200).json({
  status: 'ok',
  bot: 'Runcandels',
  uptime: Math.floor(process.uptime())
}));
app.listen(PORT, '0.0.0.0', () => console.log(`[WEB] Listening on 0.0.0.0:${PORT}`));

// -------------------- Discord client --------------------
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ],
  partials: [Partials.Channel, Partials.Message, Partials.GuildMember]
});

// -------------------- Command loader --------------------
const commands = new Map();
const commandDir = path.join(__dirname, 'commands');

for (const file of fs.readdirSync(commandDir).filter(file => file.endsWith('.js'))) {
  const filePath = path.join(commandDir, file);
  try {
    const command = require(filePath);
    if (!command?.data || typeof command.data.toJSON !== 'function' || typeof command.execute !== 'function') {
      console.warn(`[COMMAND] Skipping invalid module: ${file}`);
      continue;
    }
    const json = command.data.toJSON();
    if (!json.name) {
      console.warn(`[COMMAND] Skipping ${file}: missing command name.`);
      continue;
    }
    commands.set(json.name, command);
    console.log(`[COMMAND] Loaded /${json.name}`);
  } catch (error) {
    console.error(`[COMMAND] Failed to load ${file}:`, error);
  }
}

if (!commands.size) throw new Error('No valid slash commands were loaded from ./commands.');

function hasAllowedRole(member) {
  return Boolean(member?.roles?.cache?.has(config.allowedRoleId));
}

function configReady() {
  return [
    ['allowedRoleId', config.allowedRoleId],
    ['logChannelId', config.logChannelId],
    ['ticketCategoryId', config.ticketCategoryId],
    ['ticketSupportRoleId', config.ticketSupportRoleId],
    ['welcomeChannelId', config.welcomeChannelId],
    ['transcriptChannelId', config.transcriptChannelId]
  ];
}

async function registerCommands() {
  if (!process.env.CLIENT_ID) throw new Error('CLIENT_ID is missing.');
  if (!process.env.GUILD_ID) throw new Error('GUILD_ID is missing.');
  if (!process.env.TOKEN) throw new Error('TOKEN is missing.');

  const rest = new REST({ version: '10' }).setToken(process.env.TOKEN);
  const body = [...commands.values()].map(command => command.data.toJSON());

  console.log(`[SLASH] Registering ${body.length} guild commands...`);
  await rest.put(
    Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
    { body }
  );
  console.log(`[SLASH] Successfully registered: ${body.map(c => `/${c.name}`).join(', ')}`);
}

client.once('ready', async () => {
  console.log(`[BOT] Logged in as ${client.user.tag}`);
  console.log(`[BOT] Guilds: ${client.guilds.cache.size}`);
  console.log(`[BOT] Prefix: ${config.prefix}`);
  console.log(`[BOT] Allowed role: ${config.allowedRoleId}`);

  const placeholders = configReady().filter(([, value]) => !value || String(value).startsWith('PUT_'));
  if (placeholders.length) {
    console.warn(`[CONFIG] Replace these values before using Runcandels: ${placeholders.map(([key]) => key).join(', ')}`);
  }

  try {
    await registerCommands();
  } catch (error) {
    console.error('[SLASH] Registration failed:', error);
    console.error('[SLASH] Check TOKEN, CLIENT_ID, GUILD_ID and that the bot was invited with the applications.commands scope.');
  }

  client.user.setActivity('Runcandels Ticket Desk', { type: 3 });
});

// -------------------- Slash commands + ticket components --------------------
client.on('interactionCreate', async interaction => {
  try {
    if (interaction.isButton() || interaction.isStringSelectMenu() || interaction.isModalSubmit()) {
      if (interaction.customId?.startsWith('runcandels:ticket:')) {
        return handleInteraction(interaction);
      }
      return;
    }

    if (!interaction.isChatInputCommand()) return;

    if (!hasAllowedRole(interaction.member)) {
      return interaction.reply(componentsPayload(
        '## 🔒 Runcandels Access Denied\nYou do not have the role configured in `allowedRoleId`.',
        { ephemeral: true }
      ));
    }

    const command = commands.get(interaction.commandName);
    if (!command) {
      return interaction.reply(componentsPayload('## Runcandels\nThat command is not loaded. Restart the bot to resync commands.', { ephemeral: true }));
    }

    await command.execute(interaction);
  } catch (error) {
    console.error('[INTERACTION] Error:', error);
    const response = componentsPayload('## ⚠️ Runcandels Error\nSomething went wrong while processing that interaction. Check the Render logs.', { ephemeral: true });
    if (interaction.replied || interaction.deferred) await interaction.followUp(response).catch(() => {});
    else await interaction.reply(response).catch(() => {});
  }
});

// -------------------- Prefix commands --------------------
client.on('messageCreate', async message => {
  try {
    if (message.author.bot || !message.guild) return;
    if (!message.content.startsWith(config.prefix)) return;

    if (!hasAllowedRole(message.member)) {
      await message.reply(componentsPayload('## 🔒 Runcandels Access Denied\nYou do not have the role configured in `allowedRoleId`.')).catch(() => {});
      return;
    }

    const args = message.content.slice(config.prefix.length).trim().split(/\s+/).filter(Boolean);
    const name = (args.shift() || '').toLowerCase();
    if (!name) return;

    const command = commands.get(name);
    if (!command?.prefix) return;

    await command.prefix(message, args);
  } catch (error) {
    console.error('[PREFIX] Error:', error);
    await message.reply(componentsPayload('## ⚠️ Runcandels Error\nSomething went wrong while processing that command. Check the Render logs.')).catch(() => {});
  }
});

// -------------------- Moderation logs --------------------
client.on('messageDelete', async message => {
  if (!message.guild || message.author?.bot) return;
  await modLog(message.guild, '🗑️ Message Deleted', [
    `**Author:** ${message.author?.tag || 'Unknown'} (${message.author?.id || 'unknown'})`,
    `**Channel:** ${message.channel || 'Unknown'}`,
    `**Content:** ${message.content || '[no cached content]'}`
  ]);
});

client.on('messageUpdate', async (oldMessage, newMessage) => {
  if (!newMessage.guild || newMessage.author?.bot) return;
  if (oldMessage.content === newMessage.content) return;
  await modLog(newMessage.guild, '✏️ Message Edited', [
    `**Author:** ${newMessage.author?.tag || 'Unknown'} (${newMessage.author?.id || 'unknown'})`,
    `**Channel:** ${newMessage.channel || 'Unknown'}`,
    `**Before:** ${oldMessage.content || '[empty]'}`,
    `**After:** ${newMessage.content || '[empty]'}`
  ]);
});

client.on('guildBanAdd', async ban => {
  await modLog(ban.guild, '🔨 Member Banned', [
    `**User:** ${ban.user.tag} (${ban.user.id})`
  ]);
});

client.on('guildMemberUpdate', async (oldMember, newMember) => {
  const oldUntil = oldMember.communicationDisabledUntilTimestamp || 0;
  const newUntil = newMember.communicationDisabledUntilTimestamp || 0;

  if (newUntil > oldUntil) {
    await modLog(newMember.guild, '🔇 Member Muted / Timed Out', [
      `**User:** ${newMember.user.tag} (${newMember.id})`,
      `**Until:** ${newMember.communicationDisabledUntil?.toLocaleString() || 'Unknown'}`
    ]);
  } else if (oldUntil && !newUntil) {
    await modLog(newMember.guild, '🔊 Member Unmuted', [
      `**User:** ${newMember.user.tag} (${newMember.id})`
    ]);
  }
});

client.on('guildMemberRemove', async member => {
  try {
    const audit = await member.guild.fetchAuditLogs({ type: 20, limit: 5 });
    const entry = audit.entries.find(e => e.target?.id === member.id && Date.now() - e.createdTimestamp < 10_000);
    if (!entry) return;
    await modLog(member.guild, '👢 Member Kicked', [
      `**User:** ${member.user.tag} (${member.id})`,
      `**Moderator:** ${entry.executor?.tag || 'Unknown'}`,
      `**Reason:** ${entry.reason || 'No reason provided'}`
    ]);
  } catch (error) {
    console.error('[AUDIT] Kick log failed:', error);
  }
});

// -------------------- Welcome system --------------------
client.on('guildMemberAdd', async member => {
  try {
    await sendWelcome(member);
  } catch (error) {
    console.error('[WELCOME] Failed:', error);
  }
});

process.on('unhandledRejection', reason => console.error('[PROCESS] Unhandled rejection:', reason));
process.on('uncaughtException', error => console.error('[PROCESS] Uncaught exception:', error));

if (!process.env.TOKEN) {
  console.error('[BOT] TOKEN is missing. Render will keep the web server online, but Discord will not connect.');
} else {
  client.login(process.env.TOKEN).catch(error => console.error('[BOT] Login failed:', error));
}
