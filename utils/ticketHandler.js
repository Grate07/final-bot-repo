const { ContainerBuilder, TextDisplayBuilder, SeparatorBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ChannelType, PermissionsBitField, MessageFlags, AttachmentBuilder } = require('discord.js');
const { generateTranscript } = require('./transcriptHandler.js');

let ticketCount = 1;

async function createPanel(channel, config){
  const c = new ContainerBuilder().setAccentColor(config.accentColor)
 .addTextDisplayComponents(new TextDisplayBuilder().setContent(`# 🖤 Grey - Ticket Desk\nSelect a category below to get help.`));
  const row = new ActionRowBuilder().addComponents(
    new (require('discord.js').StringSelectMenuBuilder)().setCustomId('ticket_select').setPlaceholder('Choose ticket type').addOptions(config.ticketOptions)
  );
  channel.send({ components:[c,row], flags: MessageFlags.IsComponentsV2 });
}

async function createTicket(interaction, config, type, issueText){
  const category = config.ticketOptions.find(o=>o.value===type);
  const id = `SUP-${String(ticketCount++).padStart(5,'0')}`;

  const channel = await interaction.guild.channels.create({
    name: `${type}-grate`.toLowerCase().replace(' ', '-'),
    type: ChannelType.GuildText,
    parent: config.ticketCategoryId,
    permissionOverwrites: [
      { id: interaction.guild.id, deny:[PermissionsBitField.Flags.ViewChannel] },
      { id: interaction.user.id, allow:[PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages, PermissionsBitField.Flags.ReadMessageHistory] },
      { id: config.ticketSupportRoleId, allow:[PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
    ]
  });

  // EXACT INTERFACE LIKE YOUR IMAGE - Components V2 Onyx
  const container = new ContainerBuilder().setAccentColor(config.accentColor)
 .addTextDisplayComponents(new TextDisplayBuilder().setContent(`### 🎟️ ${id} — ${category.label}\n\n**Opened by**\n${interaction.user}\n\n**Type**\n${category.label}\n\n**Status**\nOpen\n\n**Issue**\n${issueText}\n\n-# Grey Ticket Desk | Today at <t:${Math.floor(Date.now()/1000)}:t>`));

  // Only 2 buttons like you said - No Claim button
  const row = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('close_ticket').setLabel('Close').setStyle(ButtonStyle.Danger).setEmoji('🔒'),
    new ButtonBuilder().setCustomId('close_with_reason').setLabel('Close with reason').setStyle(ButtonStyle.Secondary).setEmoji('📝')
  );

  await channel.send({ content: `${interaction.user} <@&${config.ticketSupportRoleId}>`, components:[container, row], flags: MessageFlags.IsComponentsV2 });
  await interaction.reply({ content:`Ticket created: ${channel}`, ephemeral:true });
}

async function closeTicket(interaction, config){
  await interaction.deferReply();
  const transcript = await generateTranscript(interaction.channel);

  const logCh = interaction.guild.channels.cache.get(config.transcriptChannelId);
  if(logCh){
    const c = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 📄 Transcript | ${interaction.channel.name}\n**Closed by:** ${interaction.user}\n**Channel:** ${interaction.channel.name}`));
    logCh.send({ components:[c], files:[transcript], flags: MessageFlags.IsComponentsV2 });
  }
  await interaction.editReply({ content:'Closing ticket and sending transcript...' });
  setTimeout(()=>interaction.channel.delete().catch(()=>{}), 3000);
}

async function closeWithReasonModal(interaction){
  const { ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');
  const modal = new ModalBuilder().setCustomId('close_reason_modal').setTitle('Close with reason');
  const reason = new TextInputBuilder().setCustomId('reason').setLabel('Reason for closing').setStyle(TextInputStyle.Paragraph).setRequired(true);
  modal.addComponents(new ActionRowBuilder().addComponents(reason));
  interaction.showModal(modal);
}

async function closeWithReason(interaction, config){
  await interaction.deferReply();
  const reason = interaction.fields.getTextInputValue('reason');
  const transcript = await generateTranscript(interaction.channel);
  const logCh = interaction.guild.channels.cache.get(config.transcriptChannelId);
  if(logCh){
    const c = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 📄 Transcript | ${interaction.channel.name}\n**Closed by:** ${interaction.user}\n**Reason:** ${reason}`));
    logCh.send({ components:[c], files:[transcript], flags: MessageFlags.IsComponentsV2 });
  }
  await interaction.editReply({ content:`Closed with reason: ${reason}` });
  setTimeout(()=>interaction.channel.delete().catch(()=>{}), 3000);
}

module.exports = { createPanel, createTicket, closeTicket, closeWithReasonModal, closeWithReason };