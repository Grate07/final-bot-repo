const { SlashCommandBuilder } = require('discord.js');
const { componentsPayload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
const { getMember } = require('../utils/commandUtils');

async function run(guild, member, minutes, reason, moderator) {
  if (!member) return { message: 'That user is not in this server.' };
  if (!member.moderatable) return { message: 'I cannot timeout that member. Check my role position and Moderate Members permission.' };
  await member.timeout(minutes * 60_000, reason);
  await modLog(guild, '🔇 Member Timed Out', [
    `**User:** ${member.user.tag} (${member.id})`,
    `**Moderator:** ${moderator.tag} (${moderator.id})`,
    `**Duration:** ${minutes} minute(s)`,
    `**Reason:** ${reason}`
  ]);
  return { message: `🔇 Timed out **${member.user.tag}** for **${minutes} minute(s)**.\n**Reason:** ${reason}` };
}

module.exports = {
  data: new SlashCommandBuilder().setName('mute').setDescription('Timeout a member.')
    .addUserOption(o => o.setName('user').setDescription('Member to timeout').setRequired(true))
    .addIntegerOption(o => o.setName('minutes').setDescription('Duration in minutes').setMinValue(1).setMaxValue(40320).setRequired(true))
    .addStringOption(o => o.setName('reason').setDescription('Reason')),
  async execute(i) {
    const member = await i.guild.members.fetch(i.options.getUser('user').id).catch(() => null);
    const result = await run(i.guild, member, i.options.getInteger('minutes'), i.options.getString('reason') || 'No reason provided', i.user);
    return i.reply(componentsPayload(`## 🔇 Mute\n${result.message}`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const member = await getMember(message.guild, args[0]);
    const minutes = Number(args[1]);
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 40320) return message.reply(componentsPayload('## 🔇 Mute\nUsage: `!mute <@user|id> <minutes> [reason]`'));
    const result = await run(message.guild, member, minutes, args.slice(2).join(' ') || 'No reason provided', message.author);
    return message.reply(componentsPayload(`## 🔇 Mute\n${result.message}`));
  }
};
