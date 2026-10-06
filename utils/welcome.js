const { ContainerBuilder, TextDisplayBuilder, MessageFlags } = require('discord.js');
const config = require('../config.json');

async function sendWelcome(member) {
  const channel = member.guild.channels.cache.get(config.welcomeChannelId);
  if (!channel?.isTextBased()) return false;

  const box = new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(
      `## 👋 Welcome to ${member.guild.name}\n` +
      `Welcome ${member}!\n\n` +
      `You are member **#${member.guild.memberCount}**. Enjoy your stay!\n\n` +
      `*Runcandels • Community Desk*`
    ));

  await channel.send({ flags: MessageFlags.IsComponentsV2, components: [box] });
  return true;
}

module.exports = { sendWelcome };
