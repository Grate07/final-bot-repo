const {
  ContainerBuilder,
  TextDisplayBuilder,
  SeparatorBuilder,
  SeparatorSpacingSize,
  MessageFlags
} = require('discord.js');
const config = require('../config.json');

const ONYX = Number(config.accentColor || 0x0F0F0F);

function container(...parts) {
  const box = new ContainerBuilder().setAccentColor(ONYX);
  for (const part of parts.flat()) {
    if (!part) continue;
    if (typeof part === 'string') {
      box.addTextDisplayComponents(new TextDisplayBuilder().setContent(part));
    } else {
      box.addTextDisplayComponents(part);
    }
  }
  return box;
}

function separator() {
  return new SeparatorBuilder().setSpacing(SeparatorSpacingSize.Small);
}

function componentsPayload(text, { ephemeral = false, extra = [] } = {}) {
  const box = new ContainerBuilder()
    .setAccentColor(ONYX)
    .addTextDisplayComponents(new TextDisplayBuilder().setContent(text));
  for (const item of extra) box.addTextDisplayComponents(item);
  return {
    flags: MessageFlags.IsComponentsV2 | (ephemeral ? MessageFlags.Ephemeral : 0),
    components: [box]
  };
}

function componentMessage(components, { ephemeral = false, files = [] } = {}) {
  return {
    flags: MessageFlags.IsComponentsV2 | (ephemeral ? MessageFlags.Ephemeral : 0),
    components,
    ...(files.length ? { files } : {})
  };
}

module.exports = { ONYX, container, separator, componentsPayload, componentMessage };
