// ---------- toast (uses Bootstrap's Toast component) ----------
function showToast(message, kind) {
  const wrap = document.getElementById('toast-wrap');
  if (!wrap || !message) return;
  const bg = kind === 'error' ? 'text-bg-danger' : 'text-bg-success';
  const el = document.createElement('div');
  el.className = 'toast align-items-center border-0 ' + bg;
  el.setAttribute('role', 'alert');
  el.innerHTML = '<div class="d-flex">' +
    '<div class="toast-body">' + message + '</div>' +
    '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
    '</div>';
  wrap.appendChild(el);
  const toast = new bootstrap.Toast(el, { delay: 3200 });
  el.addEventListener('hidden.bs.toast', () => el.remove());
  toast.show();
}

// ---------- shared modal (uses Bootstrap's Modal component) ----------
const appModalEl = document.getElementById('appModal');
const appModal = appModalEl ? new bootstrap.Modal(appModalEl) : null;

function openModal(html, opts) {
  opts = opts || {};
  document.getElementById('appModalBody').innerHTML = html;
  const content = document.getElementById('appModalContent');
  content.className = 'modal-content ' + (opts.white ? 'el-modal-white' : 'el-modal');
  appModal.show();
}
function closeModal() {
  if (appModal) appModal.hide();
}

function loadFragment(url, opts) {
  fetch(url)
    .then((r) => r.text())
    .then((html) => openModal(html, opts))
    .catch(() => showToast('Something went wrong. Please try again.', 'error'));
}

// ---------- opportunity / applicant detail popups ----------
function viewOpportunity(id) { loadFragment('/fragments/opportunity/' + id); }
function viewApplicant(id) { loadFragment('/fragments/application/' + id); }

// ---------- favorite / apply (AJAX) ----------
function toggleFavorite(id, btnEl) {
  fetch('/volunteer/favorite/' + id, { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      showToast(d.message, d.ok ? 'success' : 'error');
      if (btnEl) btnEl.textContent = d.saved ? 'Saved' : 'Save';
    });
}

function applyToOpportunity(id) {
  fetch('/volunteer/apply/' + id, { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      showToast(d.message, d.ok ? 'success' : 'error');
      if (d.ok) closeModal();
    });
}

// ---------- matching ----------
function runMatch(page) {
  page = page || 1;
  const fd = new FormData();
  fd.append('page', page);
  fetch('/api/match', { method: 'POST', body: fd })
    .then((r) => r.json())
    .then((d) => {
      if (!d.ok) { showToast(d.message, 'error'); return; }
      openModal(d.html);
    });
}

// ---------- org: close/reopen an opportunity ----------
function toggleOppStatus(id, badgeEl) {
  fetch('/organisation/opportunity/' + id + '/close', { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      showToast(d.message, d.ok ? 'success' : 'error');
      if (d.ok && badgeEl) {
        badgeEl.textContent = d.status;
        badgeEl.className = 'badge ' + (d.status === 'Active' ? 'text-bg-success' : 'text-bg-danger');
      }
    });
}

// ---------- org: accept/reject application ----------
function decideApplication(id, decision) {
  fetch('/organisation/application/' + id + '/' + decision, { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      showToast(d.message, d.ok ? 'success' : 'error');
      if (d.ok) { closeModal(); setTimeout(() => location.reload(), 500); }
    });
}

// ---------- dropdown checklist filters (category / time / skills / offer) ----------
// Keeps the button label in sync with the checked boxes. Checking "All"
// clears the other boxes in that group (and vice versa), matching how the
// backend treats "All" as a wildcard.
function initChecklists() {
  document.querySelectorAll('.checklist').forEach((box) => {
    const btn = box.querySelector('.checklist-toggle');
    const boxes = [...box.querySelectorAll('input[type=checkbox]')];
    const placeholder = btn.dataset.placeholder || 'Select...';

    function refreshLabel() {
      const checked = boxes.filter((c) => c.checked).map((c) => c.value);
      btn.textContent = checked.length ? checked.join(', ') : placeholder;
    }
    boxes.forEach((cb) => {
      cb.addEventListener('change', () => {
        if (cb.value === 'All' && cb.checked) {
          boxes.forEach((other) => { if (other !== cb) other.checked = false; });
        } else if (cb.checked) {
          boxes.forEach((other) => { if (other.value === 'All') other.checked = false; });
        }
        refreshLabel();
      });
    });
    refreshLabel();
  });
}
document.addEventListener('DOMContentLoaded', initChecklists);
