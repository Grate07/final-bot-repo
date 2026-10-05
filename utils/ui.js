const { ContainerBuilder, TextDisplayBuilder, MessageFlags } = require('discord.js');
const config = require('../config.json');
function container(text, accent = config.accentColor) { return new ContainerBuilder().setAccentColor(accent).addTextDisplayComponents(new TextDisplayBuilder().setContent(text)); }
function payload(text, ephemeral = false) { return { flags: MessageFlags.IsComponentsV2 | (ephemeral ? MessageFlags.Ephemeral : 0), components: [container(text)] }; }
module.exports = { container, payload };
