const {
  ContainerBuilder,
  TextDisplayBuilder,
  MediaGalleryBuilder,
  MessageFlags
} = require('discord.js');

const config = require('../config.json');

async function sendWelcome(member) {
  const channel = member.guild.channels.cache.get(config.welcomeChannelId);

  if (!channel?.isTextBased()) return false;

  const guildIcon = member.guild.iconURL({
    extension: 'png',
    size: 512
  });

  const box = new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))

    // Header
    .addTextDisplayComponents(
      new TextDisplayBuilder().setContent(
        `# 👋 Welcome to\n# RUNCANDELS`
      )
    )

    // Server icon
    ...(guildIcon
      ? [
          new MediaGalleryBuilder({
            items: [
              {
                description: 'RUNCANDELS server icon',
                media: {
                  url: guildIcon
                }
              }
            ]
          })
        ]
      : []
    )

    // Main message
    .addTextDisplayComponents(
      new TextDisplayBuilder().setContent(
        `## Welcome to our community, ${member}!\n\n` +
        `We're absolutely thrilled to have you here. 🌊\n\n` +
        `📚 Make sure to read through <#1493587392513183875> before you get started!\n\n` +
        `You are our **${member.guild.memberCount}th member!**`
      )
    )

    // Footer
    .addTextDisplayComponents(
      new TextDisplayBuilder().setContent(
        `\n*RUNCANDELS • Community*`
      )
    );

  await channel.send({
    flags: MessageFlags.IsComponentsV2,
    components: [box]
  });

  return true;
}

module.exports = { sendWelcome };