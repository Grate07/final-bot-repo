const { SlashCommandBuilder, ContainerBuilder, TextDisplayBuilder, MessageFlags } = require('discord.js');
module.exports = {
  name: 'set-welcome',
  slashData: new SlashCommandBuilder().setName('set-welcome').setDescription('Set welcome channel').addChannelOption(o=>o.setName('channel').setDescription('Channel').setRequired(true)),
  async executePrefix(msg, args, config){ msg.reply('Use slash: /set-welcome'); },
  async executeSlash(i, config){
    const ch = i.options.getChannel('channel');
    config.welcomeChannelId = ch.id;
    require('fs').writeFileSync('./config.json', JSON.stringify(config, null, 2));
    const c = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## Grey | Welcome channel set to ${ch}`));
    i.reply({ components:[c], flags: MessageFlags.IsComponentsV2 });
  }
}