const { SlashCommandBuilder } = require('discord.js');
const { payload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
module.exports = { data:new SlashCommandBuilder().setName('kick').setDescription('Kick a member.').addUserOption(o=>o.setName('user').setDescription('Member').setRequired(true)).addStringOption(o=>o.setName('reason').setDescription('Reason')), async execute(i){const u=i.options.getUser('user'),r=i.options.getString('reason')||'No reason provided',m=await i.guild.members.fetch(u.id).catch(()=>null);if(!m)return i.reply(payload('That user is not in this server.',true));if(!m.kickable)return i.reply(payload('I cannot kick that member.',true));await m.kick(r);await modLog(i.guild, `👢 **Kick**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Reason:** ${r}`);return i.reply(payload(`👢 Kicked ${u.tag}.\n**Reason:** ${r}`,true));}, async prefix(message,args){const id=args[0]?.replace(/[<@!>]/g,'');const r=args.slice(1).join(' ')||'No reason provided',m=await message.guild.members.fetch(id).catch(()=>null);if(!m)return message.reply(payload('Usage: `!kick <@user|id> [reason]`'));if(!m.kickable)return message.reply(payload('I cannot kick that member.'));await m.kick(r);await modLog(i.guild, `👢 **Kick**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Reason:** ${r}`);return message.reply(payload(`👢 Kicked ${m.user.tag}.\n**Reason:** ${r}`));} };
