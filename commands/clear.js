const { SlashCommandBuilder } = require('discord.js');
const { componentsPayload } = require('../utils/ui');
const { modLog } = require('../utils/logger');

async function run(channel, guild, amount, moderator) {
  const deleted = await channel.bulkDelete(amount, true);
  await modLog(guild, '🧹 Messages Cleared', [
    `**Moderator:** ${moderator.tag} (${moderator.id})`,
    `**Channel:** ${channel}`,
    `**Requested:** ${amount}`,
    `**Deleted:** ${deleted.size}`
  ]);
  return deleted.size;
}

module.exports = {
  data: new SlashCommandBuilder().setName('clear').setDescription('Delete up to 100 recent messages.')
    .addIntegerOption(o => o.setName('amount').setDescription('1–100 messages').setMinValue(1).setMaxValue(100).setRequired(true)),
  async execute(i) {
    const amount = i.options.getInteger('amount');
    const deleted = await run(i.channel, i.guild, amount, i.user);
    return i.reply(componentsPayload(`## 🧹 Clear\nDeleted **${deleted}** message(s).`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const amount = Number(args[0]);
    if (!Number.isInteger(amount) || amount < 1 || amount > 100) return message.reply(componentsPayload('## 🧹 Clear\nUsage: `!clear <1-100>`'));
    const deleted = await run(message.channel, message.guild, amount, message.author);
    return message.reply(componentsPayload(`## 🧹 Clear\nDeleted **${deleted}** message(s).`));
  }
};
