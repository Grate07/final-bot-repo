const { SlashCommandBuilder } = require('discord.js');
const { componentsPayload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
const { getMember } = require('../utils/commandUtils');

async function run(guild, member, reason, moderator) {
  if (!member) return { message: 'That user is not in this server.' };
  if (!member.kickable) return { message: 'I cannot kick that member. Check my role position and Kick Members permission.' };
  await member.kick(reason);
  await modLog(guild, '👢 Member Kicked', [
    `**User:** ${member.user.tag} (${member.id})`,
    `**Moderator:** ${moderator.tag} (${moderator.id})`,
    `**Reason:** ${reason}`
  ]);
  return { message: `👢 Kicked **${member.user.tag}**.\n**Reason:** ${reason}` };
}

module.exports = {
  data: new SlashCommandBuilder().setName('kick').setDescription('Kick a member from the server.')
    .addUserOption(o => o.setName('user').setDescription('Member to kick').setRequired(true))
    .addStringOption(o => o.setName('reason').setDescription('Reason')),
  async execute(i) {
    const member = await i.guild.members.fetch(i.options.getUser('user').id).catch(() => null);
    const result = await run(i.guild, member, i.options.getString('reason') || 'No reason provided', i.user);
    return i.reply(componentsPayload(`## 👢 Kick\n${result.message}`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const member = await getMember(message.guild, args[0]);
    const result = await run(message.guild, member, args.slice(1).join(' ') || 'No reason provided', message.author);
    return message.reply(componentsPayload(`## 👢 Kick\n${result.message}`));
  }
};
