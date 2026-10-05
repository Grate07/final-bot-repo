const { SlashCommandBuilder } = require('discord.js');
const { payload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
module.exports = { data:new SlashCommandBuilder().setName('unmute').setDescription('Remove a timeout.').addUserOption(o=>o.setName('user').setDescription('Member').setRequired(true)), async execute(i){const u=i.options.getUser('user'),m=await i.guild.members.fetch(u.id).catch(()=>null);if(!m)return i.reply(payload('That user is not in this server.',true));if(!m.moderatable)return i.reply(payload('I cannot modify that member.',true));await m.timeout(null,'Unmuted by moderator');await modLog(i.guild, `🔊 **Unmute**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}`);return i.reply(payload(`🔊 Unmuted ${u.tag}.`,true));}, async prefix(message,args){const id=args[0]?.replace(/[<@!>]/g,''),m=await message.guild.members.fetch(id).catch(()=>null);if(!m)return message.reply(payload('Usage: `!unmute <@user|id>`'));if(!m.moderatable)return message.reply(payload('I cannot modify that member.'));await m.timeout(null,'Unmuted by moderator');await modLog(i.guild, `🔊 **Unmute**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}`);return message.reply(payload(`🔊 Unmuted ${m.user.tag}.`));} };
