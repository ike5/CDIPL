#!/usr/bin/env node
'use strict';

// Print the most frequent words in a text file, ignoring case and punctuation.
// Usage: node j02_word_count.js <file.txt> [count]

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_TOP = 20;

// A word is a run of letters/digits, optionally joined by inner apostrophes
// (so "don't" stays one word while surrounding quotes are dropped).
const WORD_PATTERN = /[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*/gu;

function readText(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`File not found: ${filePath}`);
    throw new Error(`Cannot read ${filePath}: ${err.message}`);
  }
}

/** Return a Map of word -> number of occurrences. */
function countWords(text) {
  const counts = new Map();
  for (const word of text.toLowerCase().match(WORD_PATTERN) ?? []) {
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }
  return counts;
}

/** Most frequent first; ties are broken alphabetically so output is stable. */
function topWords(counts, limit) {
  return [...counts.entries()]
    .sort(([wordA, a], [wordB, b]) => b - a || wordA.localeCompare(wordB))
    .slice(0, limit);
}

function printTable(entries) {
  if (entries.length === 0) {
    console.log('No words found.');
    return;
  }
  const wordWidth = Math.max(...entries.map(([word]) => word.length));
  const countWidth = String(entries[0][1]).length;
  for (const [word, count] of entries) {
    console.log(`${word.padEnd(wordWidth)}  ${String(count).padStart(countWidth)}`);
  }
}

function parseLimit(value) {
  if (value === undefined) return DEFAULT_TOP;
  const limit = Number(value);
  if (!Number.isInteger(limit) || limit < 1) {
    throw new Error(`Count must be a positive whole number, got "${value}"`);
  }
  return limit;
}

function main() {
  const [filePath, limitArg] = process.argv.slice(2);
  if (!filePath) {
    console.error(`Usage: node ${path.basename(__filename)} <file.txt> [count]`);
    process.exit(2);
  }

  try {
    const limit = parseLimit(limitArg);
    printTable(topWords(countWords(readText(filePath)), limit));
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
