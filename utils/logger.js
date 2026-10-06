const {
  ContainerBuilder,
  TextDisplayBuilder,
  MessageFlags
} = require('discord.js');
const config = require('../config.json');

async function modLog(guild, title, lines = []) {
  const channel = guild?.channels?.cache?.get(config.logChannelId);
  if (!channel?.isTextBased()) return;

  const text = [
    `## ${title}`,
    ...lines.map(line => String(line))
  ].join('\n');

  const box = new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(text));

  return channel.send({
    flags: MessageFlags.IsComponentsV2,
    components: [box]
  }).catch(error => console.error('Mod log send failed:', error));
}

module.exports = { modLog };
