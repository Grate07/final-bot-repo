const {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ChannelType,
  ContainerBuilder,
  ModalBuilder,
  PermissionFlagsBits,
  TextDisplayBuilder,
  TextInputBuilder,
  TextInputStyle,
  StringSelectMenuBuilder,
  MediaGalleryBuilder,
  MessageFlags
} = require('discord.js');
const config = require('../config.json');
const fs = require('fs');
const path = require('path');
const { generateTranscript } = require('./transcriptHandler');
const { componentsPayload } = require('./ui');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');

function saveConfig() {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
}

function safeName(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 24) || 'user';
}

function nextTicketId() {
  const number = Number(config.ticketCounter || 1);
  config.ticketCounter = number + 1;
  saveConfig();
  return `SUP-${String(number).padStart(5, '0')}`;
}

function optionByValue(value) {
  return config.ticketOptions.find(option => option.value === value);
}

function makePanel() {
  const menu = new StringSelectMenuBuilder()
    .setCustomId('runcandels:ticket:type')
    .setPlaceholder('Choose a support category')
    .setMinValues(1)
    .setMaxValues(1)
    .addOptions(config.ticketOptions.map(option => ({
      label: option.label,
      value: option.value,
      description: option.description,
      emoji: option.emoji
    })));

  return new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent('## 🎟️ Runcandels Ticket Desk'))
    .addMediaGalleryComponents(new MediaGalleryBuilder({ items: [{ description: 'Runcandels Ticket Desk support banner', media: { url: 'attachment://runcandels-ticket-banner.png' } }] }))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent('Need help? Open a private support ticket and our team will take a look.'))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(
      '**How it works**\n' +
      '1. Choose the category that best matches your issue.\n' +
      '2. Describe the issue in the form that appears.\n' +
      '3. A private ticket will be created for you and the support team.\n\n' +
      '**Available categories**\n' +
      config.ticketOptions.map(o => `${o.emoji} **${o.label}** — ${o.description}`).join('\n')
    ))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent('*Runcandels Ticket Desk • Please provide as much useful detail as possible.*'))
    .addActionRowComponents(new ActionRowBuilder().addComponents(menu));
}

function makeTicketCard(ticketId, option, member, issue, createdAt) {
  const close = new ButtonBuilder()
    .setCustomId(`runcandels:ticket:close:${ticketId}`)
    .setLabel('Close')
    .setStyle(ButtonStyle.Danger);

  const closeReason = new ButtonBuilder()
    .setCustomId(`runcandels:ticket:closereason:${ticketId}`)
    .setLabel('Close with reason')
    .setEmoji('📝')
    .setStyle(ButtonStyle.Secondary);

  return new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`## 🎟️ ${ticketId} — ${option.label}`))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(
      `**Opened by** ${member}\n` +
      `**Type** ${option.label}\n` +
      `**Status** Open\n` +
      `**Issue** ${issue}`
    ))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(`*Runcandels Ticket Desk | Today at ${createdAt}*`))
    .addActionRowComponents(new ActionRowBuilder().addComponents(close, closeReason));
}

function findExistingTicket(guild, userId) {
  return guild.channels.cache.find(channel =>
    channel.type === ChannelType.GuildText &&
    channel.parentId === config.ticketCategoryId &&
    typeof channel.topic === 'string' && channel.topic.includes(`owner=${userId}`)
  );
}

async function openTicket(interaction, optionValue, issue) {
  const option = optionByValue(optionValue);
  if (!option) return interaction.reply(componentsPayload('## 🎟️ Ticket\nThat ticket option is no longer configured.', { ephemeral: true }));

  const category = interaction.guild.channels.cache.get(config.ticketCategoryId);
  const supportRole = interaction.guild.roles.cache.get(config.ticketSupportRoleId);
  if (!category || category.type !== ChannelType.GuildCategory) return interaction.reply(componentsPayload('## 🎟️ Ticket\nThe configured ticket category is invalid.', { ephemeral: true }));
  if (!supportRole) return interaction.reply(componentsPayload('## 🎟️ Ticket\nThe configured support role is invalid.', { ephemeral: true }));

  const existing = findExistingTicket(interaction.guild, interaction.user.id);
  if (existing) return interaction.reply(componentsPayload(`## 🎟️ Ticket\nYou already have an open ticket: ${existing}`, { ephemeral: true }));

  const ticketId = nextTicketId();
  const name = `${option.value}-${safeName(interaction.user.username)}`;
  const topic = `Runcandels ticket ${ticketId} | owner=${interaction.user.id} | type=${option.value}`;

  let channel;
  try {
    channel = await interaction.guild.channels.create({
      name,
      type: ChannelType.GuildText,
      parent: category.id,
      topic,
      permissionOverwrites: [
        { id: interaction.guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
        { id: interaction.user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory, PermissionFlagsBits.AttachFiles] },
        { id: supportRole.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory, PermissionFlagsBits.AttachFiles, PermissionFlagsBits.ManageMessages] },
        { id: interaction.client.user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory, PermissionFlagsBits.ManageChannels, PermissionFlagsBits.ManageMessages, PermissionFlagsBits.AttachFiles] }
      ]
    });
  } catch (error) {
    console.error('Ticket channel creation failed:', error);
    return interaction.reply(componentsPayload('## 🎟️ Ticket\nI could not create the ticket channel. Check my **Manage Channels** permission and the configured category.', { ephemeral: true }));
  }

  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  await channel.send({ flags: MessageFlags.IsComponentsV2, components: [makeTicketCard(ticketId, option, interaction.member, issue, time)] });
  return interaction.reply(componentsPayload(`## 🎟️ Ticket\nYour ticket has been created: ${channel}`, { ephemeral: true }));
}

async function closeTicket(interaction, reason = '') {
  const channel = interaction.channel;
  if (!channel?.isTextBased()) return interaction.reply(componentsPayload('## 🎟️ Ticket\nThis is not a text ticket channel.', { ephemeral: true }));

  await interaction.deferReply({ flags: MessageFlags.Ephemeral });

  const transcriptChannel = interaction.guild.channels.cache.get(config.transcriptChannelId);
  if (!transcriptChannel?.isTextBased()) return interaction.editReply(componentsPayload('## 🎟️ Ticket\nTranscript channel is not configured correctly. The ticket was not deleted.', { ephemeral: true }));

  try {
    const transcript = await generateTranscript(channel, reason);
    const box = new ContainerBuilder()
      .setAccentColor(Number(config.accentColor || 0x0F0F0F))
      .addTextDisplayComponents(new TextDisplayBuilder().setContent(
        `## 📄 Ticket Transcript\n` +
        `**Channel:** ${channel.name}\n` +
        `**Messages:** ${transcript.count}\n` +
        (reason ? `**Close reason:** ${reason}\n` : '') +
        `**Closed by:** ${interaction.user}`
      ));

    await transcriptChannel.send({
      flags: MessageFlags.IsComponentsV2,
      components: [box],
      files: [transcript.attachment]
    });

    await interaction.editReply(componentsPayload('## 🎟️ Ticket Closed\nTranscript saved. This ticket will be deleted in **3 seconds**.', { ephemeral: true }));
    setTimeout(() => channel.delete('Runcandels ticket closed').catch(() => {}), 3000);
  } catch (error) {
    console.error('Ticket close failed:', error);
    await interaction.editReply(componentsPayload('## 🎟️ Ticket\nI could not generate the transcript, so the ticket was **not** deleted.', { ephemeral: true }));
  }
}

async function handleInteraction(interaction) {
  if (interaction.isStringSelectMenu() && interaction.customId === 'runcandels:ticket:type') {
    const option = optionByValue(interaction.values[0]);
    if (!option) return interaction.reply(componentsPayload('## 🎟️ Ticket\nThat category is no longer available.', { ephemeral: true }));

    const existing = findExistingTicket(interaction.guild, interaction.user.id);
    if (existing) return interaction.reply(componentsPayload(`## 🎟️ Ticket\nYou already have an open ticket: ${existing}`, { ephemeral: true }));

    const modal = new ModalBuilder()
      .setCustomId(`runcandels:ticket:issue:${option.value}`)
      .setTitle(`${option.label} — Issue`);
    const issue = new TextInputBuilder()
      .setCustomId('issue')
      .setLabel('Issue')
      .setStyle(TextInputStyle.Paragraph)
      .setPlaceholder('Describe your issue clearly...')
      .setRequired(true)
      .setMinLength(1)
      .setMaxLength(2000);
    modal.addComponents(new ActionRowBuilder().addComponents(issue));
    return interaction.showModal(modal);
  }

  if (interaction.isModalSubmit() && interaction.customId.startsWith('runcandels:ticket:issue:')) {
    return openTicket(interaction, interaction.customId.slice('runcandels:ticket:issue:'.length), interaction.fields.getTextInputValue('issue').trim());
  }

  if (interaction.isButton() && interaction.customId.startsWith('runcandels:ticket:close:')) {
    return closeTicket(interaction);
  }

  if (interaction.isButton() && interaction.customId.startsWith('runcandels:ticket:closereason:')) {
    const modal = new ModalBuilder().setCustomId(`runcandels:ticket:reason:${interaction.customId.slice('runcandels:ticket:closereason:'.length)}`).setTitle('Close ticket with reason');
    const reason = new TextInputBuilder().setCustomId('reason').setLabel('Reason').setStyle(TextInputStyle.Paragraph).setPlaceholder('Why is this ticket being closed?').setRequired(true).setMaxLength(1000);
    modal.addComponents(new ActionRowBuilder().addComponents(reason));
    return interaction.showModal(modal);
  }

  if (interaction.isModalSubmit() && interaction.customId.startsWith('runcandels:ticket:reason:')) {
    return closeTicket(interaction, interaction.fields.getTextInputValue('reason').trim());
  }
}

module.exports = { makePanel, handleInteraction };
