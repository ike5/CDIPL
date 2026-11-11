#!/usr/bin/env node
'use strict';

// Tic-tac-toe for two players sharing a terminal.
// Players take turns typing a square number (1-9); type "q" to quit.
// Usage: node j10_tic_tac_toe.js

const readline = require('node:readline');

const WINNING_LINES = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8], // rows
  [0, 3, 6], [1, 4, 7], [2, 5, 8], // columns
  [0, 4, 8], [2, 4, 6],            // diagonals
];

/** Draw the board; empty squares show their number so players know what to type. */
function renderBoard(board) {
  const rows = [0, 3, 6].map((start) =>
    ` ${board
      .slice(start, start + 3)
      .map((mark, offset) => mark ?? start + offset + 1)
      .join(' | ')}`
  );
  return rows.join('\n---+---+---\n');
}

/** Return 'X' or 'O' if that player has three in a row, otherwise null. */
function findWinner(board) {
  for (const [a, b, c] of WINNING_LINES) {
    if (board[a] && board[a] === board[b] && board[a] === board[c]) return board[a];
  }
  return null;
}

const isFull = (board) => board.every((square) => square !== null);

/**
 * Turn the player's input into a board index.
 * Returns { index } on success or { error } describing what was wrong.
 */
function parseMove(input, board) {
  if (!/^[1-9]$/.test(input)) return { error: 'Please enter a number from 1 to 9.' };
  const index = Number(input) - 1;
  if (board[index] !== null) return { error: `Square ${input} is already taken.` };
  return { index };
}

async function play() {
  const rl = readline.createInterface({ input: process.stdin });
  const lines = rl[Symbol.asyncIterator](); // works for a terminal and for piped input

  const board = Array(9).fill(null);
  let player = 'X';

  console.log('Tic-tac-toe: X goes first. Enter a square number, or q to quit.\n');
  console.log(`${renderBoard(board)}\n`);

  try {
    while (true) {
      process.stdout.write(`Player ${player}, choose a square (1-9): `);
      const { value, done } = await lines.next();
      if (done) {
        console.log('\nInput ended before the game finished.');
        return;
      }

      const input = value.trim();
      if (input.toLowerCase() === 'q') {
        console.log('Game abandoned.');
        return;
      }

      const move = parseMove(input, board);
      if (move.error) {
        console.log(move.error);
        continue;
      }

      board[move.index] = player;
      console.log(`\n${renderBoard(board)}\n`);

      if (findWinner(board)) {
        console.log(`Player ${player} wins!`);
        return;
      }
      if (isFull(board)) {
        console.log("It's a draw.");
        return;
      }
      player = player === 'X' ? 'O' : 'X';
    }
  } finally {
    rl.close();
  }
}

play().catch((err) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
