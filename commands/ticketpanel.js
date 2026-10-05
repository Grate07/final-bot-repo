const { SlashCommandBuilder } = require('discord.js');
const { MessageFlags } = require('discord.js');
const { makePanel } = require('../utils/ticketHandler');
const { payload } = require('../utils/ui');
module.exports = { data:new SlashCommandBuilder().setName('ticketpanel').setDescription('Send the Grey ticket panel.'), async execute(i){await i.channel.send({flags:MessageFlags.IsComponentsV2,components:[makePanel()]});return i.reply(payload('Ticket panel sent.',true));}, async prefix(message){await message.channel.send({flags:MessageFlags.IsComponentsV2,components:[makePanel()]});return message.reply(payload('Ticket panel sent.'));} };
