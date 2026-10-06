const { PermissionsBitField } = require('discord.js');
const { componentsPayload } = require('./ui');

function memberIdFromArg(value = '') {
  const match = value.match(/^(?:<@!?(\d+)>|(\d+))$/);
  return match ? (match[1] || match[2]) : null;
}

async function getMember(guild, value) {
  const id = memberIdFromArg(value);
  if (!id) return null;
  return guild.members.fetch(id).catch(() => null);
}

function hasPermission(member, permission) {
  return Boolean(member?.permissions?.has(permission));
}

function deny(text = 'You do not have permission to use this command.') {
  return componentsPayload(`## Runcandels
${text}`, { ephemeral: true });
}

module.exports = { memberIdFromArg, getMember, hasPermission, deny };
