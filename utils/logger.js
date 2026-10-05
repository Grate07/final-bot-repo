const { ContainerBuilder, TextDisplayBuilder, MessageFlags } = require('discord.js');
const config = require('../config.json');
async function modLog(guild, text) {
  const channel = guild?.channels?.cache?.get(config.logChannelId);
  if (!channel?.isTextBased()) return;
  const box = new ContainerBuilder().setAccentColor(config.accentColor).addTextDisplayComponents(new TextDisplayBuilder().setContent(`## Grey Moderation Log\n${text}`));
  return channel.send({ flags: MessageFlags.IsComponentsV2, components: [box] }).catch(() => {});
}
module.exports = { modLog };
