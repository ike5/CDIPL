#!/usr/bin/env node
'use strict';

// Combine every JSON file in a folder (each holding a list of records) into
// one list, keeping only the first record seen for each `id`.
// Usage: node j07_combine_json.js <input-folder> <output.json>

const fs = require('node:fs');
const path = require('node:path');

/** List the .json files in a folder, in name order so results are repeatable. */
function listJsonFiles(folder, excludePath) {
  let entries;
  try {
    entries = fs.readdirSync(folder, { withFileTypes: true });
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`Folder not found: ${folder}`);
    if (err.code === 'ENOTDIR') throw new Error(`Not a folder: ${folder}`);
    throw new Error(`Cannot read folder ${folder}: ${err.message}`);
  }

  return entries
    .filter((entry) => entry.isFile() && path.extname(entry.name).toLowerCase() === '.json')
    .map((entry) => path.join(folder, entry.name))
    // Don't read our own output back in if it lives in the input folder.
    .filter((filePath) => path.resolve(filePath) !== excludePath)
    .sort();
}

function readRecords(filePath) {
  let data;
  try {
    data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    throw new Error(`Cannot load ${filePath}: ${err.message}`);
  }
  if (!Array.isArray(data)) {
    throw new Error(`${filePath} must contain a JSON array of records`);
  }
  return data;
}

/**
 * Keep the first record for each id. Records without an id cannot be
 * duplicates of anything, so they are always kept.
 */
function dedupeById(records) {
  const seen = new Set();
  const unique = [];
  for (const record of records) {
    const id = record?.id;
    if (id === undefined || id === null) {
      unique.push(record);
    } else if (!seen.has(id)) {
      seen.add(id);
      unique.push(record);
    }
  }
  return unique;
}

function main() {
  const [folder, outputPath] = process.argv.slice(2);
  if (!folder || !outputPath) {
    console.error(`Usage: node ${path.basename(__filename)} <input-folder> <output.json>`);
    process.exit(2);
  }

  try {
    const files = listJsonFiles(folder, path.resolve(outputPath));
    if (files.length === 0) throw new Error(`No .json files found in ${folder}`);

    const all = files.flatMap(readRecords);
    const unique = dedupeById(all);

    fs.writeFileSync(outputPath, `${JSON.stringify(unique, null, 2)}\n`);

    console.log(
      `Read ${all.length} records from ${files.length} files; ` +
        `dropped ${all.length - unique.length} duplicates; ` +
        `wrote ${unique.length} records to ${outputPath}`
    );
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
