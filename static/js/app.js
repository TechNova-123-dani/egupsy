// Simple toast helper
function showToast(msg, cls='bg-dark') {
  const area = document.getElementById('toast-area');
  if(!area) return;
  const id = 't' + Date.now();
  const div = document.createElement('div');
  div.className = `toast align-items-center text-white ${cls} border-0 show mb-2`;
  div.setAttribute('role', 'alert');
  div.setAttribute('aria-live', 'assertive');
  div.setAttribute('aria-atomic', 'true');
  div.id = id;
  div.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${msg}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  area.appendChild(div);
  setTimeout(() => div.remove(), 5000);
}
