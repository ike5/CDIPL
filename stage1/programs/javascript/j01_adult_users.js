#!/usr/bin/env node
'use strict';

// Print the first ten adult users (age >= 18) from a JSON file, sorted by name.
// Usage: node j01_adult_users.js <users.json>

const fs = require('node:fs');
const path = require('node:path');

const ADULT_AGE = 18;
const LIMIT = 10;

/** Read and parse the file, making sure it holds a JSON array. */
function loadUsers(filePath) {
  let text;
  try {
    text = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`File not found: ${filePath}`);
    throw new Error(`Cannot read ${filePath}: ${err.message}`);
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch (err) {
    throw new Error(`${filePath} is not valid JSON: ${err.message}`);
  }

  if (!Array.isArray(data)) {
    throw new Error(`${filePath} must contain a JSON array of users`);
  }
  return data;
}

/** A usable user has a name and a numeric age; anything else is skipped. */
function isAdult(user) {
  return (
    user !== null &&
    typeof user === 'object' &&
    typeof user.name === 'string' &&
    Number.isFinite(user.age) &&
    user.age >= ADULT_AGE
  );
}

function selectAdults(users, limit = LIMIT) {
  return users
    .filter(isAdult)
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
    .slice(0, limit);
}

function printUsers(users) {
  if (users.length === 0) {
    console.log('No adult users found.');
    return;
  }
  const width = Math.max(...users.map((u) => u.name.length));
  for (const user of users) {
    console.log(`${user.name.padEnd(width)}  ${user.age}`);
  }
}

function main() {
  const [filePath] = process.argv.slice(2);
  if (!filePath) {
    console.error(`Usage: node ${path.basename(__filename)} <users.json>`);
    process.exit(2);
  }

  try {
    printUsers(selectAdults(loadUsers(filePath)));
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
