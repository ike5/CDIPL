#!/usr/bin/env node
'use strict';

// Convert a CSV file to JSON or a JSON file to CSV. The direction is chosen
// from the input file's extension. The result is printed, or written to the
// output file if one is named.
// Usage: node j09_csv_json.js <input.csv|input.json> [output-file]

const fs = require('node:fs');
const path = require('node:path');

/** Parse CSV text into rows of strings (handles quotes, "" escapes, CRLF). */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  const endRow = () => {
    row.push(field);
    rows.push(row);
    row = [];
    field = '';
  };

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (inQuotes) {
      if (char !== '"') field += char;
      else if (text[i + 1] === '"') { field += '"'; i++; }
      else inQuotes = false;
    } else if (char === '"' && field === '') {
      inQuotes = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[i + 1] === '\n') i++;
      endRow();
    } else {
      field += char;
    }
  }
  if (inQuotes) throw new Error('CSV has an unterminated quoted field');
  if (field !== '' || row.length > 0) endRow(); // last line without a newline

  // Ignore completely blank lines.
  return rows.filter((r) => r.length > 1 || r[0] !== '');
}

/** CSV text -> JSON text: the first row gives the property names. */
function csvToJson(text) {
  const [header, ...rows] = parseCsv(text.replace(/^﻿/, ''));
  if (!header) throw new Error('CSV file is empty');

  const records = rows.map((row, index) => {
    if (row.length > header.length) {
      throw new Error(`CSV row ${index + 2} has more fields than the header`);
    }
    return Object.fromEntries(header.map((name, col) => [name, row[col] ?? '']));
  });
  return `${JSON.stringify(records, null, 2)}\n`;
}

function formatCsvField(value) {
  if (value === null || value === undefined) return '';
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/** JSON text -> CSV text: columns are the union of all record keys. */
function jsonToCsv(text) {
  let records;
  try {
    records = JSON.parse(text);
  } catch (err) {
    throw new Error(`Invalid JSON: ${err.message}`);
  }
  const isRecord = (r) => r !== null && typeof r === 'object' && !Array.isArray(r);
  if (!Array.isArray(records) || !records.every(isRecord)) {
    throw new Error('JSON input must be an array of objects');
  }

  const header = [...new Set(records.flatMap(Object.keys))];
  const lines = [header, ...records.map((record) => header.map((key) => record[key]))];
  return lines.map((line) => line.map(formatCsvField).join(',')).join('\n') + '\n';
}

const CONVERTERS = { '.csv': csvToJson, '.json': jsonToCsv };

function main() {
  const [inputPath, outputPath] = process.argv.slice(2);
  if (!inputPath) {
    console.error(`Usage: node ${path.basename(__filename)} <input.csv|input.json> [output-file]`);
    process.exit(2);
  }

  try {
    const convert = CONVERTERS[path.extname(inputPath).toLowerCase()];
    if (!convert) throw new Error(`Input file must end in .csv or .json: ${inputPath}`);

    let text;
    try {
      text = fs.readFileSync(inputPath, 'utf8');
    } catch (err) {
      if (err.code === 'ENOENT') throw new Error(`File not found: ${inputPath}`);
      throw new Error(`Cannot read ${inputPath}: ${err.message}`);
    }

    const result = convert(text);
    if (outputPath) {
      fs.writeFileSync(outputPath, result);
      console.error(`Wrote ${outputPath}`);
    } else {
      process.stdout.write(result);
    }
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
