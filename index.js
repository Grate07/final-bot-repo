const express = require('express');
const fs = require('fs');
const path = require('path');
const {
  Client, GatewayIntentBits, Partials, REST, Routes, MessageFlags,
  ContainerBuilder, TextDisplayBuilder
} = require('discord.js');
const config = require('./config.json');
const { payload } = require('./utils/ui');
const { handleInteraction } = require('./utils/ticketHandler');
const { modLog } = require('./utils/logger');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
app.get('/', (_req, res) => res.status(200).send('Grey is online.'));
app.get('/health', (_req, res) => res.status(200).json({ status: 'ok', bot: 'Grey', uptime: process.uptime() }));
app.listen(PORT, '0.0.0.0', () => console.log(`Web server listening on port ${PORT}`));

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
  partials: [Partials.Channel, Partials.Message, Partials.GuildMember]
});

const commands = new Map();
const commandDir = path.join(__dirname, 'commands');
for (const file of fs.readdirSync(commandDir).filter(f => f.endsWith('.js'))) {
  const filePath = path.join(commandDir, file);
  try {
    const command = require(filePath);
    // Ignore unrelated legacy/helper JS files that may still exist in a Render repo.
    if (!command || !command.data || typeof command.data.toJSON !== 'function' || typeof command.execute !== 'function') {
      console.warn(`Skipping ${file}: not a valid Grey slash command module.`);
      continue;
    }
    commands.set(command.data.name, command);
  } catch (error) {
    console.error(`Failed to load command ${file}:`, error);
  }
}
if (!commands.size) throw new Error('No valid commands were loaded from ./commands.');
console.log(`Loaded commands: ${[...commands.keys()].join(', ')}`);

function hasAccess(member) { return Boolean(member?.roles?.cache?.has(config.allowedRoleId)); }
function isComponentsMessage(options) { return { ...options, flags: (options.flags || 0) | MessageFlags.IsComponentsV2 }; }

async function registerCommands() {
  if (!process.env.CLIENT_ID || !process.env.GUILD_ID) throw new Error('CLIENT_ID and GUILD_ID are required.');
  const rest = new REST({ version: '10' }).setToken(process.env.TOKEN);
  await rest.put(Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID), { body: [...commands.values()].map(c => c.data.toJSON()) });
  console.log(`Registered ${commands.size} guild slash commands.`);
}

client.once('ready', async () => {
  console.log(`Grey logged in as ${client.user.tag}`);
  try { await registerCommands(); } catch (e) { console.error('Slash command registration failed:', e); }
  client.user.setActivity('Grey Ticket Desk', { type: 3 });
});

client.on('interactionCreate', async interaction => {
  try {
    if (interaction.isButton() || interaction.isStringSelectMenu() || interaction.isModalSubmit()) {
      if (!hasAccess(interaction.member)) return interaction.reply(payload('You do not have the configured Grey role.', true));
      const ticketIds = ['grey:ticket:type'];
      const isTicket = interaction.customId?.startsWith('grey:ticket:');
      if (isTicket) return handleInteraction(interaction);
    }
    if (!interaction.isChatInputCommand()) return;
    if (!hasAccess(interaction.member)) return interaction.reply(payload('You do not have the configured Grey role.', true));
    const command = commands.get(interaction.commandName);
    if (command) await command.execute(interaction);
  } catch (error) {
    console.error('Interaction error:', error);
    const response = payload('Something went wrong while processing that command.', true);
    if (interaction.replied || interaction.deferred) await interaction.followUp(response).catch(() => {}); else await interaction.reply(response).catch(() => {});
  }
});

client.on('messageCreate', async message => {
  if (message.author.bot || !message.guild || !message.content.startsWith(config.prefix)) return;
  if (!hasAccess(message.member)) return message.reply(payload('You do not have the configured Grey role.')).catch(() => {});
  const parts = message.content.slice(config.prefix.length).trim().split(/\s+/);
  const name = (parts.shift() || '').toLowerCase();
  const command = commands.get(name);
  if (!command) return;
  try { await command.prefix(message, parts); } catch (error) { console.error('Prefix command error:', error); await message.reply(payload('Something went wrong while processing that command.')).catch(() => {}); }
});

client.on('messageDelete', async message => {
  if (!message.guild || message.author?.bot) return;
  await modLog(message.guild, `🗑️ **Message Deleted**\n**Author:** ${message.author?.tag || 'Unknown'} (${message.author?.id || 'unknown'})\n**Channel:** ${message.channel}\n**Content:** ${message.content || '[no cached content]'}`);
});
client.on('messageUpdate', async (oldMessage, newMessage) => {
  if (!newMessage.guild || newMessage.author?.bot || oldMessage.content === newMessage.content) return;
  await modLog(newMessage.guild, `✏️ **Message Edited**\n**Author:** ${newMessage.author?.tag || 'Unknown'} (${newMessage.author?.id || 'unknown'})\n**Channel:** ${newMessage.channel}\n**Before:** ${oldMessage.content || '[empty]'}\n**After:** ${newMessage.content || '[empty]'}`);
});
client.on('guildBanAdd', async ban => { await modLog(ban.guild, `🔨 **Member Banned**\n**User:** ${ban.user.tag} (${ban.user.id})`); });
client.on('guildMemberUpdate', async (oldMember, newMember) => {
  const oldTimeout = oldMember.communicationDisabledUntilTimestamp || 0;
  const newTimeout = newMember.communicationDisabledUntilTimestamp || 0;
  if (newTimeout > oldTimeout) await modLog(newMember.guild, `🔇 **Member Muted / Timed Out**\n**User:** ${newMember.user.tag} (${newMember.id})\n**Until:** ${newMember.communicationDisabledUntil ? newMember.communicationDisabledUntil.toLocaleString() : 'unknown'}`);
  else if (oldTimeout && !newTimeout) await modLog(newMember.guild, `🔊 **Member Unmuted**\n**User:** ${newMember.user.tag} (${newMember.id})`);
});
client.on('guildMemberRemove', async member => {
  try {
    const logs = await member.guild.fetchAuditLogs({ type: 20, limit: 5 });
    const entry = logs.entries.find(e => e.target?.id === member.id && Date.now() - e.createdTimestamp < 10000);
    if (entry) await modLog(member.guild, `👢 **Member Kicked**\n**User:** ${member.user.tag} (${member.id})\n**Moderator:** ${entry.executor?.tag || 'Unknown'}\n**Reason:** ${entry.reason || 'No reason provided'}`);
  } catch {}
});
client.on('guildMemberAdd', async member => {
  const channel = member.guild.channels.cache.get(config.welcomeChannelId);
  if (!channel?.isTextBased()) return;
  const box = new ContainerBuilder().setAccentColor(config.accentColor)
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 👋 Welcome to ${member.guild.name}\nWelcome ${member}!\n\nYou are member **#${member.guild.memberCount}**. Enjoy your stay!`));
  await channel.send({ flags: MessageFlags.IsComponentsV2, components: [box] }).catch(() => {});
});

process.on('unhandledRejection', reason => console.error('Unhandled rejection:', reason));
process.on('uncaughtException', error => console.error('Uncaught exception:', error));

if (!process.env.TOKEN) console.error('TOKEN is missing. Set TOKEN in Render environment variables.');
else client.login(process.env.TOKEN);
