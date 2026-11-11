// Searchable table.
// Fetches a JSON list of items from the address in the table's data-src
// attribute, renders it as table rows, and hides the rows that do not contain
// the text typed into the search box.

const COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'category', label: 'Category' },
  { key: 'price', label: 'Price' },
];

const table = document.querySelector('#items-table');
const searchBox = document.querySelector('#search');
const status = document.querySelector('#status');

async function fetchItems(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request for ${url} failed with status ${response.status}`);
  }
  return response.json();
}

/** Builds a <tr> with one cell (<th> or <td>) per value. */
function createRow(values, cellTag) {
  const row = document.createElement('tr');
  for (const value of values) {
    const cell = document.createElement(cellTag);
    cell.textContent = value ?? '';
    row.append(cell);
  }
  return row;
}

function renderTable(items) {
  const headerRow = createRow(COLUMNS.map((column) => column.label), 'th');
  const bodyRows = items.map((item) =>
    createRow(COLUMNS.map((column) => item[column.key]), 'td'),
  );

  table.createTHead().replaceChildren(headerRow);
  table.tBodies[0].replaceChildren(...bodyRows);
}

/** Hides every row that has no cell containing the query (case-insensitive). */
function filterRows(query) {
  const needle = query.trim().toLowerCase();
  let visibleCount = 0;

  for (const row of table.tBodies[0].rows) {
    const matches = [...row.cells].some((cell) =>
      cell.textContent.toLowerCase().includes(needle),
    );
    row.hidden = !matches;
    if (matches) visibleCount += 1;
  }

  status.textContent = visibleCount === 0 ? 'No matching items.' : '';
}

async function init() {
  status.textContent = 'Loading…';
  try {
    const items = await fetchItems(table.dataset.src);
    renderTable(items);
    // The browser may have restored text typed before a reload.
    filterRows(searchBox.value);
  } catch (error) {
    console.error(error);
    status.textContent = 'Sorry, the items could not be loaded.';
  }
}

searchBox.addEventListener('input', () => filterRows(searchBox.value));
init();
