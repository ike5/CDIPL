// Sign-up form validation.
// Checks the fields when the form is submitted, shows a message beside each
// invalid one, and only lets the form through when everything is valid.

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

const form = document.querySelector('#signup-form');
const fields = [...form.querySelectorAll('input[name]')];

/** Returns the error message for a field, or an empty string if it is valid. */
function getError(field) {
  // Spaces can be a legitimate part of a password, so only trim other fields.
  const value = field.type === 'password' ? field.value : field.value.trim();

  if (value === '') {
    const label = field.labels[0]?.textContent.trim() ?? 'This field';
    return field.required ? `${label} is required.` : '';
  }
  if (field.type === 'email' && !EMAIL_PATTERN.test(value)) {
    return 'Enter a valid email address, such as name@example.com.';
  }
  if (field.type === 'password' && value.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  return '';
}

/** Shows (or clears) the message in the element beside the field. */
function showError(field, message) {
  const output = document.getElementById(`${field.id}-error`);
  output.textContent = message;
  field.setAttribute('aria-invalid', String(message !== ''));
}

/** Validates one field, updates its message, and reports whether it passed. */
function validateField(field) {
  const message = getError(field);
  showError(field, message);
  return message === '';
}

function handleSubmit(event) {
  // Validate every field, not just the first failure, so all messages show.
  const invalidFields = fields.filter((field) => !validateField(field));

  if (invalidFields.length > 0) {
    event.preventDefault();
    invalidFields[0].focus();
  }
}

function handleInput(event) {
  // Once a field has been flagged, re-check it as the user corrects it.
  const field = event.target;
  if (field.getAttribute('aria-invalid') === 'true') {
    validateField(field);
  }
}

// Use our own messages instead of the browser's built-in validation bubbles.
form.noValidate = true;
form.addEventListener('submit', handleSubmit);
form.addEventListener('input', handleInput);
