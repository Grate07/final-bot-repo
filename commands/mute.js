const { SlashCommandBuilder } = require('discord.js');
const { payload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
module.exports = { data:new SlashCommandBuilder().setName('mute').setDescription('Timeout a member.').addUserOption(o=>o.setName('user').setDescription('Member').setRequired(true)).addIntegerOption(o=>o.setName('minutes').setDescription('Duration in minutes').setMinValue(1).setMaxValue(40320).setRequired(true)).addStringOption(o=>o.setName('reason').setDescription('Reason')), async execute(i){const u=i.options.getUser('user'),min=i.options.getInteger('minutes'),r=i.options.getString('reason')||'No reason provided',m=await i.guild.members.fetch(u.id).catch(()=>null);if(!m)return i.reply(payload('That user is not in this server.',true));if(!m.moderatable)return i.reply(payload('I cannot timeout that member.',true));await m.timeout(min*60000,r);await modLog(i.guild, `🔇 **Mute / Timeout**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Duration:** ${min} minute(s)
**Reason:** ${r}`);return i.reply(payload(`🔇 Muted ${u.tag} for **${min} minute(s)**.\n**Reason:** ${r}`,true));}, async prefix(message,args){const id=args[0]?.replace(/[<@!>]/g,''),min=Number(args[1]),r=args.slice(2).join(' ')||'No reason provided',m=await message.guild.members.fetch(id).catch(()=>null);if(!m||!Number.isInteger(min)||min<1||min>40320)return message.reply(payload('Usage: `!mute <@user|id> <minutes> [reason]`'));if(!m.moderatable)return message.reply(payload('I cannot timeout that member.'));await m.timeout(min*60000,r);await modLog(i.guild, `🔇 **Mute / Timeout**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Duration:** ${min} minute(s)
**Reason:** ${r}`);return message.reply(payload(`🔇 Muted ${m.user.tag} for **${min} minute(s)**.\n**Reason:** ${r}`));} };
