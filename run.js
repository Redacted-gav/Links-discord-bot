import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

import { iboss } from './iboss.js';

const blockedColor = '\x1b[38;2;147;11;181m';
const green = '\x1b[32m';
const mainColor = '\x1b[38;2;191;69;204m';
const offMainColor = '\x1b[38;2;126;23;138m';
const linkTextColor = '\x1b[38;2;27;83;224m';
const reset = '\x1b[0m';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function drawProgress(done, total) {
  const width = 30;
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  const filled = Math.round((width * done) / total) || 0;
  const empty = width - filled;

  const bar = `[${'█'.repeat(filled)}${'-'.repeat(empty)}]`;

  readline.clearLine(process.stdout, 0);
  process.stdout.write(`${mainColor}${bar} ${percent}% (${done}/${total})${reset}`);
}

async function main() {
  const inputFile = path.join(__dirname, 'urls.txt');
  const blocklistFile = path.join(__dirname, 'blocklist.txt');
  const outputFile = path.join(__dirname, 'unchecked.txt');

  try {
    const blocklist = new Set();
    try {
      const blockData = await fs.readFile(blocklistFile, 'utf8');
      blockData
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean)
        .forEach(url => blocklist.add(url));
      console.log(`Loaded ${blocklist.size} rules from global blocklist.`);
    } catch (err) {
      console.log(`No global blocklist found at ${blocklistFile} (skipping)...`);
    }

    const rawData = await fs.readFile(inputFile, 'utf8');
    const urls = rawData.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const total = urls.length;
    let done = 0;

    if (total === 0) {
      console.log(`${mainColor}No URLs found to process.${reset}`);
      return;
    }

    await fs.writeFile(outputFile, '');
    console.log(`Checking ${total} URLs...\n`);
    drawProgress(done, total);

    for (const url of urls) {
      let logLine = '';

      try {
        if (blocklist.has(url)) {
          logLine = `${linkTextColor}${url}${reset} ${blockedColor}[BLOCKED] (Global Blocklist)${reset}`;
        } else {
          const [reason, blocked] = await iboss(url);

          if (!blocked) {
            await fs.appendFile(outputFile, `${url}\n`);
            logLine = `${linkTextColor}${url}${reset} ${offMainColor}[UNBLOCKED]${reset}`;
          } else {
            logLine = `${linkTextColor}${url}${reset} ${blockedColor}[BLOCKED] (${reason || 'No reason'})${reset}`;
          }
        }
      } catch (err) {
        logLine = `${linkTextColor}${url}${reset} ${blockedColor}[ERROR]: ${err.message}${reset}`;
      }

      readline.cursorTo(process.stdout, 0);
      readline.clearLine(process.stdout, 0);

      console.log(logLine);

      done++;
      drawProgress(done, total);
    }

    console.log(`\n\n${mainColor}Done! Saved unblocked URLs to: ${path.resolve(outputFile)}${reset}`);

  } catch (err) {
    console.error(`${blockedColor}Error: ${err.message}${reset}`);
  }
}

main();
