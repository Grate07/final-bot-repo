const { SlashCommandBuilder } = require('discord.js');
const { payload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
module.exports = { data:new SlashCommandBuilder().setName('clear').setDescription('Delete messages.').addIntegerOption(o=>o.setName('amount').setDescription('1-100 messages').setMinValue(1).setMaxValue(100).setRequired(true)), async execute(i){const n=i.options.getInteger('amount');const deleted=await i.channel.bulkDelete(n,true);await modLog(i.guild, `🧹 **Clear**\n**Moderator:** ${i.user.tag}\n**Channel:** ${i.channel}
**Amount:** ${deleted.size}`);return i.reply(payload(`🧹 Deleted **${deleted.size}** message(s).`,true));}, async prefix(message,args){const n=Number(args[0]);if(!Number.isInteger(n)||n<1||n>100)return message.reply(payload('Usage: `!clear <1-100>`'));const deleted=await message.channel.bulkDelete(n,true);await modLog(message.guild, `🧹 **Clear**\n**Moderator:** ${message.author.tag}\n**Channel:** ${message.channel}
**Amount:** ${deleted.size}`);return message.reply(payload(`🧹 Deleted **${deleted.size}** message(s).`));} };
