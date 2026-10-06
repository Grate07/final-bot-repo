const { SlashCommandBuilder, ChannelType } = require('discord.js');
const fs = require('fs');
const path = require('path');
const config = require('../config.json');
const { componentsPayload } = require('../utils/ui');

function save() { fs.writeFileSync(path.join(__dirname, '..', 'config.json'), JSON.stringify(config, null, 2)); }
function id(value = '') { return value.replace(/[<#>]/g, ''); }

module.exports = {
  data: new SlashCommandBuilder().setName('set-transcript').setDescription('Set the transcript channel.')
    .addChannelOption(o => o.setName('channel').setDescription('Text channel for ticket transcripts').addChannelTypes(ChannelType.GuildText).setRequired(true)),
  async execute(i) {
    const channel = i.options.getChannel('channel'); config.transcriptChannelId = channel.id; save();
    return i.reply(componentsPayload(`## 📄 Transcript\nTranscript channel set to ${channel}.`, { ephemeral: true }));
  },
  async prefix(message, args) {
    const channel = message.guild.channels.cache.get(id(args[0]));
    if (!channel || channel.type !== ChannelType.GuildText) return message.reply(componentsPayload('## 📄 Transcript\nUsage: `!set-transcript #channel`'));
    config.transcriptChannelId = channel.id; save();
    return message.reply(componentsPayload(`## 📄 Transcript\nTranscript channel set to ${channel}.`));
  }
};
