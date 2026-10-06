const { SlashCommandBuilder } = require('discord.js');
const { MessageFlags, AttachmentBuilder } = require('discord.js');
const path = require('path');
const { makePanel } = require('../utils/ticketHandler');
const { componentsPayload } = require('../utils/ui');

module.exports = {
  data: new SlashCommandBuilder().setName('ticketpanel').setDescription('Send the Runcandels Ticket Desk panel.'),
  async execute(i) {
    await i.channel.send({ flags: MessageFlags.IsComponentsV2, components: [makePanel()], files: [new AttachmentBuilder(path.join(__dirname, '..', 'assets', 'runcandels-ticket-banner.png'), { name: 'runcandels-ticket-banner.png' })] });
    return i.reply(componentsPayload('## 🎟️ Ticket Panel\nThe ticket panel has been posted.', { ephemeral: true }));
  },
  async prefix(message) {
    await message.channel.send({ flags: MessageFlags.IsComponentsV2, components: [makePanel()], files: [new AttachmentBuilder(path.join(__dirname, '..', 'assets', 'runcandels-ticket-banner.png'), { name: 'runcandels-ticket-banner.png' })] });
    return message.reply(componentsPayload('## 🎟️ Ticket Panel\nThe ticket panel has been posted.'));
  }
};
