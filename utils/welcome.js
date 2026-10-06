const {
  ContainerBuilder,
  TextDisplayBuilder,
  MediaGalleryBuilder,
  MessageFlags
} = require('discord.js');

const fs = require('fs');
const path = require('path');

const configPath = path.join(__dirname, '..', 'config.json');
const config = require('../config.json');

function saveConfig() {
  fs.writeFileSync(
    configPath,
    JSON.stringify(config, null, 2),
    'utf8'
  );
}

function getOrdinal(number) {
  const lastTwo = number % 100;

  if (lastTwo >= 11 && lastTwo <= 13) {
    return `${number}th`;
  }

  switch (number % 10) {
    case 1:
      return `${number}st`;
    case 2:
      return `${number}nd`;
    case 3:
      return `${number}rd`;
    default:
      return `${number}th`;
  }
}

async function sendWelcome(member) {
  const channel = member.guild.channels.cache.get(
    config.welcomeChannelId
  );

  if (!channel || !channel.isTextBased()) {
    return false;
  }

  // Give the new member their permanent explorer number
  config.explorerCount = Number(config.explorerCount || 0) + 1;

  const explorerNumber = config.explorerCount;
  const ordinal = getOrdinal(explorerNumber);

  saveConfig();

  // Get THE MEMBER'S avatar, not the server icon
  const memberAvatar = member.displayAvatarURL({
    extension: 'png',
    size: 512,
    forceStatic: false
  });

  const container = new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F))

    // Header
    .addTextDisplayComponents(
      new TextDisplayBuilder().setContent(
        `# 👋 Welcome to\n# RUNCANDELS`
      )
    )

    // New member's avatar
    .addMediaGalleryComponents(
      new MediaGalleryBuilder({
        items: [
          {
            description: `${member.user.username}'s avatar`,
            media: {
              url: memberAvatar
            }
          }
        ]
      })
    )

    // Welcome text
    .addTextDisplayComponents(
      new TextDisplayBuilder().setContent(
        `## Welcome to our community,\n${member}!\n\n` +
        `We are absolutely thrilled to have you here. 🌊\n\n` +
        `📚 Make sure to read through <#1493587392513183875> before you get started!\n\n` +
        `You are our **${ordinal} explorer!**`
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
    components: [container]
  });

  return true;
}

module.exports = {
  sendWelcome
};