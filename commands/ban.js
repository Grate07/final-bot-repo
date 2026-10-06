const { SlashCommandBuilder } = require('discord.js');
const { componentsPayload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
const { getMember } = require('../utils/commandUtils');

async function run(guild, target, reason, moderator) {
  if (!target) return { ok: false, message: 'That user is not in this server.' };
  if (!target.bannable) return { ok: false, message: 'I cannot ban that member. Check my role position and Ban Members permission.' };
  await target.ban({ reason });
  await modLog(guild, '🔨 Member Banned', [
    `**User:** ${target.user.tag} (${target.id})`,
    `**Moderator:** ${moderator.tag} (${moderator.id})`,
    `**Reason:** ${reason}`
  ]);
  return { ok: true, message: `🔨 Banned **${target.user.tag}**.\n**Reason:** ${reason}` };
}

module.exports = {
  data: new SlashCommandBuilder().setName('ban').setDescription('Ban a member from the server.')
    .addUserOption(o => o.setName('user').setDescription('Member to ban').setRequired(true))
    .addStringOption(o => o.setName('reason').setDescription('Reason')),
  async execute(i) {
    const user = i.options.getUser('user');
    const member = await i.guild.members.fetch(user.id).catch(() => null);
    const reason = i.options.getString('reason') || 'No reason provided';
    const result = await run(i.guild, member, reason, i.user);
    return i.reply(componentsPayload(`## 🔨 Ban\n${result.message}`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const member = await getMember(message.guild, args[0]);
    const reason = args.slice(1).join(' ') || 'No reason provided';
    if (!member) return message.reply(componentsPayload('## 🔨 Ban\nUsage: `!ban <@user|id> [reason]`'));
    const result = await run(message.guild, member, reason, message.author);
    return message.reply(componentsPayload(`## 🔨 Ban\n${result.message}`));
  }
};
