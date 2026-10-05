const { AttachmentBuilder } = require('discord.js');

async function generateTranscript(channel){
  const messages = await channel.messages.fetch({ limit: 100 });
  const sorted = messages.sort((a,b)=>a.createdTimestamp - b.createdTimestamp);

  let html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Grey Transcript - ${channel.name}</title><style>
  body{background:#0f0f0f;color:#fff;font-family:Arial;padding:20px}
 .msg{background:#1a1a1a;margin:10px 0;padding:12px;border-radius:8px;border-left:4px solid #2b2b2b}
 .author{font-weight:bold;color:#fff}
 .time{color:#888;font-size:12px}
 .content{margin-top:5px}
  h1{color:#fff;border-bottom:2px solid #2b2b2b;padding-bottom:10px}
  </style></head><body><h1>🖤 Grey Transcript - #${channel.name}</h1><p>Generated at ${new Date().toLocaleString()}</p>`;

  sorted.forEach(m=>{
    html+=`<div class="msg"><div class="author">${m.author.tag} <span class="time">${m.createdAt.toLocaleString()}</span></div><div class="content">${m.content || '<i>Embed/Attachment</i>'}</div></div>`;
  });
  html+=`</body></html>`;

  const buffer = Buffer.from(html, 'utf-8');
  return new AttachmentBuilder(buffer, { name: `transcript-${channel.name}.html` });
}

module.exports = { generateTranscript };