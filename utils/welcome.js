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

  /*
   * Give the member their permanent explorer number.
   *
   * 1st person  -> 1st explorer
   * 2nd person  -> 2nd explorer
   * 3rd person  -> 3rd explorer
   * 4th person  -> 4th explorer
   */
  config.explorerCount = Number(config.explorerCount || 0) + 1;

  const explorerNumber = config.explorerCount;

  saveConfig();

  const ordinal = getOrdinal(explorerNumber);

  const serverIcon = member.guild.iconURL({
    extension: 'png',
    size: 512
  });

  const components = [];

  // Header
  components.push(
    new TextDisplayBuilder().setContent(
      `# 👋 Welcome to\n# RUNCANDELS`
    )
  );

  // Server icon
  if (serverIcon) {
    components.push(
      new MediaGalleryBuilder({
        items: [
          {
            description: 'RUNCANDELS',
            media: {
              url: serverIcon
            }
          }
        ]
      })
    );
  }

  // Welcome message
  components.push(
    new TextDisplayBuilder().setContent(
      `## Welcome to our community,\n${member}!\n\n` +
      `We are absolutely thrilled to have you here. 🌊\n\n` +
      `📚 Make sure to read through <#1493587392513183875> before you get started!\n\n` +
      `You are our **${ordinal} explorer!**`
    )
  );

  // Footer
  components.push(
    new TextDisplayBuilder().setContent(
      `\n*RUNCANDELS • Community*`
    )
  );

  const container = new ContainerBuilder()
    .setAccentColor(Number(config.accentColor || 0x0F0F0F));

  for (const component of components) {
    if (component instanceof TextDisplayBuilder) {
      container.addTextDisplayComponents(component);
    } else {
      container.addMediaGalleryComponents(component);
    }
  }

  await channel.send({
    flags: MessageFlags.IsComponentsV2,
    components: [container]
  });

  return true;
}

module.exports = {
  sendWelcome
};