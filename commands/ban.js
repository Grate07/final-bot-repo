const { SlashCommandBuilder } = require('discord.js');
const { payload } = require('../utils/ui');
const { modLog } = require('../utils/logger');
module.exports = {
  data: new SlashCommandBuilder().setName('ban').setDescription('Ban a member.').addUserOption(o => o.setName('user').setDescription('Member to ban').setRequired(true)).addStringOption(o => o.setName('reason').setDescription('Reason').setRequired(false)),
  async execute(i) { const u=i.options.getUser('user'), reason=i.options.getString('reason')||'No reason provided'; const m=await i.guild.members.fetch(u.id).catch(()=>null); if(!m) return i.reply(payload('That user is not in this server.',true)); if(!m.bannable) return i.reply(payload('I cannot ban that member.',true)); await m.ban({reason}); await modLog(i.guild, `🔨 **Ban**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Reason:** ${reason}`); return i.reply(payload(`🔨 Banned ${u.tag}.\n**Reason:** ${reason}`,true)); },
  async prefix(message,args) { const id=args[0]?.replace(/[<@!>]/g,''); const reason=args.slice(1).join(' ')||'No reason provided'; const m=await message.guild.members.fetch(id).catch(()=>null); if(!m) return message.reply(payload('Usage: `!ban <@user|id> [reason]`')); if(!m.bannable) return message.reply(payload('I cannot ban that member.')); await m.ban({reason}); await modLog(i.guild, `🔨 **Ban**
**User:** ${u.tag} (${u.id})
**Moderator:** ${i.user.tag}
**Reason:** ${reason}`); return message.reply(payload(`🔨 Banned ${m.user.tag}.\n**Reason:** ${reason}`)); }
};
