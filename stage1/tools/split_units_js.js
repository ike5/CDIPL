// Split JavaScript programs into units for the Stage 1 inventory.
//
// A unit is a top-level function declaration, a top-level variable initialised
// with a function, a method of a top-level class, or "<module>": the remaining
// top-level statements other than directives, `require` declarations,
// declarations of literal constants, and a bare call such as `main()`.
// If the whole file is wrapped in one function call (an IIFE, or a
// DOMContentLoaded listener), the wrapper's body is treated as the top level.
//
// Lines counted are non-blank lines that are not comment-only.
// Needs the `acorn` parser on NODE_PATH (it is not part of the repository).
// Usage: node split_units_js.js FILE... (prints CSV rows: program,unit,start,end,lines)
const acorn = require('acorn');
const fs = require('fs');
const path = require('path');

const isFn = (n) => n && (n.type === 'FunctionExpression' || n.type === 'ArrowFunctionExpression');
const isLiteral = (n) => !n || n.type === 'Literal' || n.type === 'TemplateLiteral' && n.expressions.length === 0 ||
  n.type === 'UnaryExpression' && isLiteral(n.argument) ||
  n.type === 'BinaryExpression' && isLiteral(n.left) && isLiteral(n.right) ||
  n.type === 'ArrayExpression' && n.elements.every(isLiteral) ||
  n.type === 'ObjectExpression' && n.properties.every((p) => p.type === 'Property' && isLiteral(p.value)) ||
  n.type === 'NewExpression' && n.arguments.every(isLiteral);
const isRequire = (n) => n && (n.type === 'CallExpression' && n.callee.name === 'require' ||
  n.type === 'MemberExpression' && isRequire(n.object));

function unwrap(body) {
  const real = body.filter((s) => !s.directive);
  if (real.length !== 1 || real[0].type !== 'ExpressionStatement') return body;
  const call = real[0].expression;
  if (call.type !== 'CallExpression') return body;
  const fn = isFn(call.callee) ? call.callee : call.arguments.find(isFn);
  return fn && fn.body.type === 'BlockStatement' ? fn.body.body : body;
}

function units(file) {
  const source = fs.readFileSync(file, 'utf8');
  const comments = [];
  const tokens = [];
  const ast = acorn.parse(source, { ecmaVersion: 'latest', sourceType: 'script', locations: true,
    allowHashBang: true, onComment: comments, onToken: tokens });
  const codeLines = new Set();
  for (const t of tokens) for (let l = t.loc.start.line; l <= t.loc.end.line; l++) codeLines.add(l);
  const count = (node) => {
    let n = 0;
    for (let l = node.loc.start.line; l <= node.loc.end.line; l++) if (codeLines.has(l)) n++;
    return n;
  };
  const rows = [];
  let moduleLines = 0;
  const add = (name, node) => rows.push([name, node.loc.start.line, node.loc.end.line, count(node)]);
  for (const s of unwrap(ast.body)) {
    if (s.directive) continue;
    if (s.type === 'FunctionDeclaration') add(s.id.name, s);
    else if (s.type === 'ClassDeclaration') {
      for (const m of s.body.body) if (m.type === 'MethodDefinition') add(`${s.id.name}.${m.key.name}`, m);
    } else if (s.type === 'VariableDeclaration' && s.declarations.every((d) => isFn(d.init))) {
      for (const d of s.declarations) add(d.id.name, s);
    } else if (s.type === 'VariableDeclaration' && s.declarations.every((d) => isRequire(d.init) || isLiteral(d.init))) {
      continue;
    } else if (s.type === 'ExpressionStatement' && s.expression.type === 'CallExpression' &&
      s.expression.callee.type === 'Identifier' && s.expression.arguments.length === 0) {
      continue;
    } else moduleLines += count(s);
  }
  if (moduleLines) rows.push(['<module>', 0, 0, moduleLines]);
  return rows;
}

for (const file of process.argv.slice(2)) {
  const program = path.basename(file).split('_')[0].toUpperCase();
  for (const [name, start, end, lines] of units(file)) console.log(`${program},${name},${start},${end},${lines}`);
}
