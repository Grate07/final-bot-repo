const { SlashCommandBuilder } = require('discord.js');
const config = require('../config.json');
const { sendWelcome } = require('../utils/welcome');
const { componentsPayload } = require('../utils/ui');

module.exports = {
  data: new SlashCommandBuilder().setName('test-welcome').setDescription('Test the welcome message in the configured welcome channel.'),
  async execute(i) {
    const channel = i.guild.channels.cache.get(config.welcomeChannelId);
    if (!channel?.isTextBased()) return i.reply(componentsPayload('## 👋 Test Welcome\nSet a welcome channel first with `/set-welcome`.', { ephemeral: true }));
    await sendWelcome(i.member);
    return i.reply(componentsPayload(`## 👋 Test Welcome\nSent a test welcome for ${i.member}.`, { ephemeral: true }));
  },
  async prefix(message) {
    const channel = message.guild.channels.cache.get(config.welcomeChannelId);
    if (!channel?.isTextBased()) return message.reply(componentsPayload('## 👋 Test Welcome\nSet a welcome channel first with `!set-welcome #channel`.'));
    await sendWelcome(message.member);
    return message.reply(componentsPayload(`## 👋 Test Welcome\nSent a test welcome for ${message.member}.`));
  }
};
