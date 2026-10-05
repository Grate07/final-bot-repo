const {
  ActionRowBuilder, ButtonBuilder, ButtonStyle, ChannelType, ContainerBuilder,
  ModalBuilder, PermissionFlagsBits, TextDisplayBuilder, TextInputBuilder, TextInputStyle,
  StringSelectMenuBuilder, MessageFlags
} = require('discord.js');
const config = require('../config.json');
const fs = require('fs');
const path = require('path');
const { generateTranscript } = require('./transcriptHandler');
const { payload } = require('./ui');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');
const pendingTickets = new Map();

function saveConfig() { fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2)); }
function safeName(s) { return s.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 24) || 'user'; }
function nextTicketId() { const n = Number(config.ticketCounter || 1); config.ticketCounter = n + 1; saveConfig(); return `SUP-${String(n).padStart(5, '0')}`; }
function optionByValue(value) { return config.ticketOptions.find(o => o.value === value); }

function makePanel() {
  const menu = new StringSelectMenuBuilder().setCustomId('grey:ticket:type').setPlaceholder('Choose a support category').setMinValues(1).setMaxValues(1)
    .addOptions(config.ticketOptions.map(o => ({ label: o.label, value: o.value, description: o.description, emoji: o.emoji })));
  return new ContainerBuilder().setAccentColor(config.accentColor)
    .addTextDisplayComponents(new TextDisplayBuilder().setContent('## 🎟️ Grey Ticket Desk\nSelect a category below to open a private support ticket.'))
    .addActionRowComponents(new ActionRowBuilder().addComponents(menu));
}

function makeTicketCard(ticketId, option, member, issue, createdAt) {
  const close = new ButtonBuilder().setCustomId(`grey:ticket:close:${ticketId}`).setLabel('Close').setStyle(ButtonStyle.Danger);
  const reason = new ButtonBuilder().setCustomId(`grey:ticket:closereason:${ticketId}`).setLabel('Close with reason').setEmoji('📝').setStyle(ButtonStyle.Secondary);
  return new ContainerBuilder().setAccentColor(config.accentColor)
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 🎟️ ${ticketId} — ${option.label}`))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`**Opened by** ${member}\n**Type** ${option.label}\n**Status** Open\n**Issue** ${issue}`))
    .addSeparatorComponents()
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`*Grey Ticket Desk | Today at ${createdAt}*`))
    .addActionRowComponents(new ActionRowBuilder().addComponents(close, reason));
}

async function openTicket(interaction, optionValue, issue) {
  const option = optionByValue(optionValue);
  if (!option) return interaction.reply(payload('That ticket option is not configured.', true));
  const category = interaction.guild.channels.cache.get(config.ticketCategoryId);
  const supportRole = interaction.guild.roles.cache.get(config.ticketSupportRoleId);
  if (!category || category.type !== ChannelType.GuildCategory) return interaction.reply(payload('The ticket category is not configured correctly.', true));
  if (!supportRole) return interaction.reply(payload('The ticket support role is not configured correctly.', true));

  const ticketId = nextTicketId();
  const channel = await interaction.guild.channels.create({ name: `${option.value}-${safeName(interaction.user.username)}`, type: ChannelType.GuildText, parent: category.id,
    permissionOverwrites: [
      { id: interaction.guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
      { id: interaction.user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory] },
      { id: supportRole.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory, PermissionFlagsBits.ManageMessages] }
    ]
  });
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  await channel.send({ flags: MessageFlags.IsComponentsV2, components: [makeTicketCard(ticketId, option, interaction.member, issue, time)] });
  await interaction.reply(payload(`Ticket created: ${channel}`, true));
}

async function handleInteraction(interaction) {
  if (interaction.isStringSelectMenu() && interaction.customId === 'grey:ticket:type') {
    const option = optionByValue(interaction.values[0]);
    if (!option) return interaction.reply(payload('That option no longer exists.', true));
    pendingTickets.set(interaction.user.id, option.value);
    const modal = new ModalBuilder().setCustomId(`grey:ticket:issue:${option.value}`).setTitle(`${option.label} — Issue`);
    const input = new TextInputBuilder().setCustomId('issue').setLabel('Issue').setStyle(TextInputStyle.Paragraph).setPlaceholder('Describe what you need help with...').setRequired(true).setMaxLength(2000);
    modal.addComponents(new ActionRowBuilder().addComponents(input));
    return interaction.showModal(modal);
  }
  if (interaction.isModalSubmit() && interaction.customId.startsWith('grey:ticket:issue:')) {
    const value = interaction.customId.slice('grey:ticket:issue:'.length);
    pendingTickets.delete(interaction.user.id);
    return openTicket(interaction, value, interaction.fields.getTextInputValue('issue'));
  }
  if (interaction.isButton() && interaction.customId.startsWith('grey:ticket:close:')) return closeTicket(interaction, null);
  if (interaction.isButton() && interaction.customId.startsWith('grey:ticket:closereason:')) {
    const ticketId = interaction.customId.slice('grey:ticket:closereason:'.length);
    const modal = new ModalBuilder().setCustomId(`grey:ticket:reason:${ticketId}`).setTitle('Close ticket with reason');
    modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('reason').setLabel('Reason').setStyle(TextInputStyle.Paragraph).setRequired(true).setMaxLength(1000)));
    return interaction.showModal(modal);
  }
  if (interaction.isModalSubmit() && interaction.customId.startsWith('grey:ticket:reason:')) {
    return closeTicket(interaction, interaction.fields.getTextInputValue('reason'));
  }
}

async function closeTicket(interaction, reason) {
  await interaction.deferReply({ ephemeral: true });
  const channel = interaction.channel;
  const transcriptChannel = interaction.guild.channels.cache.get(config.transcriptChannelId);
  if (!transcriptChannel || !transcriptChannel.isTextBased()) return interaction.editReply(payload('Transcript channel is not configured correctly. The ticket was not deleted.', true));
  try {
    const result = await generateTranscript(channel, reason);
    await transcriptChannel.send({ content: `📄 **Ticket transcript:** ${channel.name}${reason ? `\n📝 **Reason:** ${reason}` : ''}`, files: [result.attachment] });
    await interaction.editReply(payload('Transcript saved. This ticket will be deleted in 3 seconds.', true));
    setTimeout(() => channel.delete('Ticket closed').catch(() => {}), 3000);
  } catch (error) {
    console.error('Ticket close error:', error);
    await interaction.editReply(payload('I could not generate the transcript, so the ticket was not deleted.', true));
  }
}

module.exports = { makePanel, handleInteraction };
