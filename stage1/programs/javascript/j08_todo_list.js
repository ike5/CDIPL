// To-do list.
// Items can be added, marked as done and deleted. The list is kept in
// localStorage so it is still there after the page is reloaded.

const STORAGE_KEY = 'todo-list-items';

const form = document.querySelector('#todo-form');
const input = document.querySelector('#todo-input');
const list = document.querySelector('#todo-list');

// Each item is { id: number, text: string, done: boolean }.
let todos = loadTodos();

function loadTodos() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    // Storage is unavailable or holds something unreadable: start empty.
    return [];
  }
}

function saveTodos() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  } catch (error) {
    console.warn('The to-do list could not be saved.', error);
  }
}

function createTodoElement(todo) {
  const item = document.createElement('li');
  item.dataset.id = todo.id;
  item.classList.toggle('done', todo.done);

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = todo.done;

  const text = document.createElement('span');
  text.textContent = todo.text;

  const label = document.createElement('label');
  label.append(checkbox, ' ', text);

  const deleteButton = document.createElement('button');
  deleteButton.type = 'button';
  deleteButton.className = 'delete';
  deleteButton.textContent = 'Delete';
  deleteButton.setAttribute('aria-label', `Delete "${todo.text}"`);

  item.append(label, ' ', deleteButton);
  return item;
}

function render() {
  list.replaceChildren(...todos.map(createTodoElement));
}

/** Replaces the list, then saves and redraws it. */
function setTodos(nextTodos) {
  todos = nextTodos;
  saveTodos();
  render();
}

function addTodo(text) {
  const id = Math.max(0, ...todos.map((todo) => todo.id)) + 1;
  setTodos([...todos, { id, text, done: false }]);
}

function toggleTodo(id) {
  setTodos(todos.map((todo) => (todo.id === id ? { ...todo, done: !todo.done } : todo)));
}

function deleteTodo(id) {
  setTodos(todos.filter((todo) => todo.id !== id));
}

/** Finds the id of the to-do item that contains the given element. */
function getTodoId(element) {
  return Number(element.closest('li').dataset.id);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (text === '') return;

  addTodo(text);
  form.reset();
  input.focus();
});

// One listener on the list handles every item, including ones added later.
list.addEventListener('change', (event) => {
  if (!event.target.matches('input[type="checkbox"]')) return;

  const id = getTodoId(event.target);
  toggleTodo(id);
  // The list was redrawn, so put keyboard focus back on the same checkbox.
  list.querySelector(`li[data-id="${id}"] input`).focus();
});

list.addEventListener('click', (event) => {
  if (event.target.matches('button.delete')) {
    deleteTodo(getTodoId(event.target));
  }
});

render();
