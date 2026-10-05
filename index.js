const { Client, GatewayIntentBits, Partials, Collection, Events, REST, Routes, ContainerBuilder, TextDisplayBuilder, MessageFlags, ModalBuilder, TextInputBuilder, TextInputStyle, ActionRowBuilder: ModalRow } = require('discord.js');
const express = require('express');
const fs = require('fs');
const config = require('./config.json');

// --- RENDER + UPTIMEROBOT ---
const app = express();
app.get('/', (req, res) => res.send('Grey is Online'));
app.listen(process.env.PORT || 3000, () => console.log('Webserver running'));

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.GuildMembers, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildModeration],
  partials: [Partials.Message, Partials.Channel, Partials.GuildMember]
});

client.commands = new Collection();
client.slashCommands = [];
for (const file of fs.readdirSync('./commands').filter(f=>f.endsWith('.js'))) {
  const cmd = require(`./commands/${file}`);
  client.commands.set(cmd.name, cmd);
  if (cmd.slashData) client.slashCommands.push(cmd.slashData.toJSON());
}

// WELCOME
client.on(Events.GuildMemberAdd, async (member) => {
  const ch = member.guild.channels.cache.get(config.welcomeChannelId);
  if(!ch) return;
  const container = new ContainerBuilder().setAccentColor(config.accentColor)
   .addTextDisplayComponents(new TextDisplayBuilder().setContent(`# 🖤 Welcome to ${member.guild.name}\n**Hey ${member}, welcome!**\n\n> Thanks for joining us. Make sure to check rules and get support from ticket.`))
   .addTextDisplayComponents(new TextDisplayBuilder().setContent(`-# Member #${member.guild.memberCount} | ${member.user.tag}`));
  ch.send({ components: [container], flags: MessageFlags.IsComponentsV2 });
});

// MOD LOGS (same as before)
client.on(Events.MessageDelete, async (msg) => {
  if(!msg.guild || msg.author?.bot) return;
  const logCh = msg.guild.channels.cache.get(config.logChannelId);
  if(!logCh) return;
  const c = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 🗑️ Grey Logs | Deleted\n**Author:** ${msg.author} | ${msg.channel}\n**Content:** ${msg.content?.slice(0,1000)}`));
  logCh.send({ components:[c], flags: MessageFlags.IsComponentsV2 });
});
client.on(Events.MessageUpdate, async (o,n) => {
  if(!o.guild || o.content===n.content || o.author?.bot) return;
  const logCh = o.guild.channels.cache.get(config.logChannelId);
  if(!logCh) return;
  const c = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## ✏️ Edited\n**User:** ${o.author} in ${o.channel}\n**Before:** ${o.content.slice(0,500)}\n**After:** ${n.content.slice(0,500)}`));
  logCh.send({ components:[c], flags: MessageFlags.IsComponentsV2 });
});

// COMMAND HANDLER
client.on(Events.MessageCreate, async (msg) => {
  if(msg.author.bot ||!msg.content.startsWith(config.prefix)) return;
  if(!msg.member.roles.cache.has(config.allowedRoleId)) return;
  const args = msg.content.slice(config.prefix.length).trim().split(/ +/);
  const cmd = client.commands.get(args.shift().toLowerCase());
  if(cmd?.executePrefix) cmd.executePrefix(msg, args, config);
});

client.on(Events.InteractionCreate, async (i) => {
  // Slash
  if(i.isChatInputCommand()){
    if(!i.member.roles.cache.has(config.allowedRoleId)) return i.reply({ content:`You need <@&${config.allowedRoleId}>`, ephemeral:true });
    return client.commands.get(i.commandName)?.executeSlash(i, config);
  }

  // Ticket Dropdown -> Open MODAL for Issue
  if(i.isStringSelectMenu() && i.customId === 'ticket_select'){
    const modal = new ModalBuilder().setCustomId(`ticket_modal_${i.values[0]}`).setTitle('Grey Support - Describe your issue');
    const issueInput = new TextInputBuilder().setCustomId('issue').setLabel('What is your issue?').setStyle(TextInputStyle.Paragraph).setPlaceholder('Explain your issue in detail...').setRequired(true).setMaxLength(1000);
    modal.addComponents(new ModalRow().addComponents(issueInput));
    return i.showModal(modal);
  }

  // Modal Submit -> Create Ticket with N7 style interface
  if(i.isModalSubmit() && i.customId.startsWith('ticket_modal_')){
    const type = i.customId.replace('ticket_modal_','');
    const issue = i.fields.getTextInputValue('issue');
    await require('./utils/ticketHandler.js').createTicket(i, config, type, issue);
  }

  if(i.isButton()){
    if(i.customId === 'close_ticket') require('./utils/ticketHandler.js').closeTicket(i, config);
    if(i.customId === 'close_with_reason') require('./utils/ticketHandler.js').closeWithReasonModal(i);
  }

  if(i.isModalSubmit() && i.customId === 'close_reason_modal'){
    require('./utils/ticketHandler.js').closeWithReason(i, config);
  }
});

client.once(Events.ClientReady, async () => {
  console.log(`Grey ready as ${client.user.tag}`);
  const rest = new REST().setToken(process.env.TOKEN);
  await rest.put(Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID), { body: client.slashCommands });
});

client.login(process.env.TOKEN);