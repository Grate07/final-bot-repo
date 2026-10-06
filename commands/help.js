const { SlashCommandBuilder } = require('discord.js');
const { ContainerBuilder, TextDisplayBuilder, MessageFlags } = require('discord.js');
const config = require('../config.json');

function helpBox() {
  const box = new ContainerBuilder().setAccentColor(Number(config.accentColor || 0x0F0F0F));
  box.addTextDisplayComponents(new TextDisplayBuilder().setContent('## Runcandels — Command Center\nAll commands are available as **slash commands** and, where shown, as **prefix commands**.'));
  box.addTextDisplayComponents(new TextDisplayBuilder().setContent(
    '**🛡️ Moderation**\n' +
    '`/ban` · `!ban` — Permanently ban a member.\n' +
    '`/kick` · `!kick` — Remove a member from the server.\n' +
    '`/mute` · `!mute` — Timeout a member for a number of minutes.\n' +
    '`/unmute` · `!unmute` — Remove a member timeout.\n' +
    '`/warn` · `!warn` — Record a moderation warning in the mod log.\n' +
    '`/clear` · `!clear` — Delete 1–100 recent messages.'
  ));
  box.addTextDisplayComponents(new TextDisplayBuilder().setContent(
    '**🎟️ Tickets**\n' +
    '`/ticketpanel` · `!ticketpanel` — Post the Runcandels Ticket Desk.\n' +
    'Users choose a category, submit an issue, and receive a private ticket.\n' +
    'Tickets support **Close** and **Close with reason**, both producing a 100-message HTML transcript.'
  ));
  box.addTextDisplayComponents(new TextDisplayBuilder().setContent(
    '**⚙️ Configuration**\n' +
    '`/set-transcript` · `!set-transcript` — Set where ticket HTML transcripts are sent.\n' +
    '`/set-welcome` · `!set-welcome` — Set where welcome messages are sent.\n' +
    '`/test-welcome` · `!test-welcome` — Send a test welcome message.\n' +
    '`/help` · `!help` — Show this command guide.'
  ));
  box.addTextDisplayComponents(new TextDisplayBuilder().setContent(
    '**🔐 Access**\nCommands are restricted to the role configured by `allowedRoleId`.\n' +
    'The role restriction does not block normal users from opening or closing their own tickets.'
  ));
  return box;
}

module.exports = {
  data: new SlashCommandBuilder().setName('help').setDescription('Show Runcandels command help.'),
  async execute(i) { return i.reply({ flags: MessageFlags.IsComponentsV2, components: [helpBox()] }); },
  async prefix(message) { return message.reply({ flags: MessageFlags.IsComponentsV2, components: [helpBox()] }); }
};
