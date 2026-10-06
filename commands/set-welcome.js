const { SlashCommandBuilder, ChannelType } = require('discord.js');
const fs = require('fs');
const path = require('path');
const config = require('../config.json');
const { componentsPayload } = require('../utils/ui');

function save() { fs.writeFileSync(path.join(__dirname, '..', 'config.json'), JSON.stringify(config, null, 2)); }
function id(value = '') { return value.replace(/[<#>]/g, ''); }

module.exports = {
  data: new SlashCommandBuilder().setName('set-welcome').setDescription('Set the welcome channel.')
    .addChannelOption(o => o.setName('channel').setDescription('Text channel for welcomes').addChannelTypes(ChannelType.GuildText).setRequired(true)),
  async execute(i) {
    const channel = i.options.getChannel('channel'); config.welcomeChannelId = channel.id; save();
    return i.reply(componentsPayload(`## 👋 Welcome\nWelcome channel set to ${channel}.`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const channel = message.guild.channels.cache.get(id(args[0]));
    if (!channel || channel.type !== ChannelType.GuildText) return message.reply(componentsPayload('## 👋 Welcome\nUsage: `!set-welcome #channel`'));
    config.welcomeChannelId = channel.id; save();
    return message.reply(componentsPayload(`## 👋 Welcome\nWelcome channel set to ${channel}.`));
  }
};
