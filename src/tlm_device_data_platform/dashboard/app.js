'use strict';
const $ = id => document.getElementById(id);
const csrf = () => document.cookie.split('; ').find(x => x.startsWith('tlm_csrf='))?.split('=')[1] || '';
let profile, options, editing = null, historyPath, offset = 0, nextOffset, refreshing;
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const showError = error => { $('notice').textContent = error.message; $('notice').className = 'error'; };
const handle = fn => async (...args) => { $('notice').textContent = ''; try { await fn(...args); } catch (e) { showError(e); } };
async function api(path, method = 'GET', body, retry = true) {
  const response = await fetch(path, { method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (response.status === 401 && retry && !path.startsWith('/v1/auth/')) {
    if (!refreshing) refreshing = api('/v1/auth/refresh', 'POST', undefined, false).finally(() => { refreshing = null; });
    await refreshing; return api(path, method, body, false);
  }
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
const button = (text, fn) => { const n = node('button', text, 'secondary'); n.type = 'button'; n.addEventListener('click', handle(fn)); return n; };
const cell = (row, value, cls) => { const c = node('td', value, cls); row.append(c); return c; };
function select(label, entries, selected, empty = false) {
  const s = node('select'); s.setAttribute('aria-label', label);
  if (empty) s.append(new Option('Unassigned', ''));
  entries.forEach(([id, name]) => s.append(new Option(name, id)));
  s.value = selected || ''; return s;
}
function signedOut() {
  profile = null; $('authentication').hidden = false; $('workspace').hidden = true; $('identity').textContent = '';
  ['users', 'sessions', 'readings', 'contexts', 'bindings'].forEach(id => $(id).replaceChildren());
  $('password').value = '';
}
async function load() {
  try { profile = await api('/v1/auth/me'); }
  catch (e) { try { await api('/v1/auth/refresh', 'POST'); profile = await api('/v1/auth/me'); } catch (_) { signedOut(); return; } }
  $('authentication').hidden = true; $('workspace').hidden = false;
  $('identity').textContent = profile.email;
  $('account-status').textContent = `${profile.role || 'New account'} · ${profile.status}`;
  $('pending').hidden = profile.status !== 'pending'; $('disabled').hidden = profile.status !== 'disabled';
  $('approved').hidden = profile.status !== 'approved';
  if (profile.status !== 'approved') return;
  const canManage = ['teacher', 'admin'].includes(profile.role);
  $('session-editor').hidden = !canManage; $('device-context').hidden = !canManage;
  $('administration').hidden = profile.role !== 'admin';
  $('global-history').hidden = !['manager', 'admin'].includes(profile.role);
  const sessions = await api('/v1/sessions');
  $('sessions').replaceChildren();
  sessions.forEach(s => {
    const row = node('tr'); cell(row, s.name); cell(row, s.status); cell(row, s.student_ids.length); cell(row, s.device_ids.length);
    const actions = cell(row); actions.append(button('Open', async () => { historyPath = `/v1/sessions/${s.session_id}/telemetry`; offset = 0; $('history-title').textContent = `${s.name} · Telemetry history`; await history(); }));
    if (canManage && s.status === 'draft') {
      actions.append(button('Edit roster', () => edit(s)), button('Start', async () => { await api(`/v1/sessions/${s.session_id}/start`, 'POST'); await load(); }));
    }
    if (canManage && s.status === 'active') actions.append(button('End', async () => { await api(`/v1/sessions/${s.session_id}/finish`, 'POST'); await load(); }));
    $('sessions').append(row);
  });
  if (!sessions.length) { const row = node('tr'); const c = cell(row, 'No sessions available'); c.colSpan = 5; $('sessions').append(row); }
  if (canManage) {
    options = await api('/v1/sessions/options');
    $('session-school').replaceChildren(...options.schools.map(s => new Option(s.name, s.school_id)));
    pickRoster();
    $('contexts').replaceChildren();
    const sessionName = id => id ? sessions.find(s => s.session_id === id)?.name || id : 'No session';
    options.devices.forEach(d => { const row = node('tr'); cell(row, `${d.system_type} · ${d.device_id}`, 'mono'); cell(row, sessionName(d.desired_session_id)); cell(row, d.desired_session_id ? (d.desired_session_confirmed ? 'Packet confirmed' : 'Awaiting packet') : 'No group requested'); cell(row, d.confirmed_session_id ? sessionName(d.confirmed_session_id) : 'No group confirmed'); cell(row, d.last_v2_received_at ? `${sessionName(d.last_received_session_id)} · ${d.last_v2_received_at}` : 'No v2 packet received'); $('contexts').append(row); });
  }
  if (profile.role === 'admin') await administration();
}
function pickRoster(students = [], devices = []) {
  const school = $('session-school').value;
  $('session-students').replaceChildren(...options.students.filter(s => s.school_id === school).map(s => new Option(s.email, s.user_id, false, students.includes(s.user_id))));
  $('session-devices').replaceChildren(...options.devices.filter(d => d.school_id === school && d.is_active).map(d => new Option(`${d.system_type} · ${d.device_id}`, d.device_id, false, devices.includes(d.device_id))));
}
function edit(s) {
  editing = s.session_id; $('session-name').value = s.name; $('session-name').disabled = true;
  $('session-school').value = s.school_id; $('session-school').disabled = true; pickRoster(s.student_ids, s.device_ids);
  $('editor-title').textContent = 'Edit draft roster'; $('save-session').textContent = 'Save roster'; $('cancel-edit').hidden = false; $('session-editor').scrollIntoView({ behavior: 'smooth' });
}
function cancelEdit() { editing = null; $('session-name').disabled = false; $('session-school').disabled = false; $('session-form').reset(); $('editor-title').textContent = 'Create session'; $('save-session').textContent = 'Create draft'; $('cancel-edit').hidden = true; if (options) pickRoster(); }
async function history() {
  const data = await api(`${historyPath}?limit=50&offset=${offset}`);
  $('history').hidden = false; $('readings').replaceChildren(); nextOffset = data.next_offset;
  data.items.forEach(m => { const row = node('tr'); cell(row, m.device_id, 'mono'); cell(row, m.captured_at || 'Unsynchronized'); cell(row, m.received_at); cell(row, Object.entries(m.payload).map(([key, value]) => `${key}: ${value}`).join(', ')); $('readings').append(row); });
  if (!data.items.length) { const row = node('tr'); const c = cell(row, 'No telemetry available'); c.colSpan = 4; $('readings').append(row); }
  $('history-back').disabled = offset === 0; $('history-next').disabled = nextOffset === null;
}
async function administration() {
  const schools = await api('/v1/admin/schools');
  const entries = schools.map(s => [s.school_id, s.name]);
  $('schools').replaceChildren(...schools.map(s => node('li', s.name)));
  $('users').replaceChildren();
  (await api('/v1/admin/users')).forEach(u => {
    const row = node('tr'); cell(row, u.email);
    const role = select('Role', ['student', 'teacher', 'manager', 'admin'].map(x => [x, x]), u.role, true);
    const school = select('School', entries, u.school_id, true);
    const status = select('Status', ['pending', 'approved', 'disabled'].map(x => [x, x]), u.status);
    cell(row).append(role); cell(row).append(school); cell(row).append(status);
    const action = cell(row), saved = node('span');
    action.append(button('Save', async () => { await api(`/v1/admin/users/${u.user_id}`, 'PATCH', { role: role.value || null, school_id: school.value || null, status: status.value }); saved.textContent = 'Saved'; }), saved); $('users').append(row);
  });
  $('bindings').replaceChildren();
  (await api('/v1/admin/devices')).forEach(d => {
    const row = node('tr'); cell(row, `${d.system_type} · ${d.device_id}`, 'mono');
    const school = select('Device school', entries, d.school_id, true); cell(row).append(school);
    cell(row).append(button('Save binding', async () => { await api(`/v1/admin/devices/${d.device_id}`, 'PATCH', { school_id: school.value || null }); await load(); })); $('bindings').append(row);
  });
}
$('auth-form').addEventListener('submit', handle(async event => {
  event.preventDefault(); const action = event.submitter.value;
  const data = { email: $('email').value, password: $('password').value }; $('password').value = '';
  await api(`/v1/auth/${action}`, 'POST', data); await load();
}));
$('session-school').addEventListener('change', () => pickRoster());
$('cancel-edit').addEventListener('click', cancelEdit);
$('session-form').addEventListener('submit', handle(async event => {
  event.preventDefault(); const data = { student_ids: Array.from($('session-students').selectedOptions, x => x.value), device_ids: Array.from($('session-devices').selectedOptions, x => x.value) };
  if (editing) await api(`/v1/sessions/${editing}/roster`, 'PUT', data);
  else await api('/v1/sessions', 'POST', { ...data, name: $('session-name').value, school_id: $('session-school').value });
  cancelEdit(); await load();
}));
$('school-form').addEventListener('submit', handle(async event => { event.preventDefault(); await api('/v1/admin/schools', 'POST', { name: $('school-name').value }); $('school-form').reset(); await load(); }));
$('reload').addEventListener('click', handle(load));
$('logout').addEventListener('click', handle(async () => { try { await api('/v1/auth/logout', 'POST'); } finally { signedOut(); await api('/v1/auth/csrf'); } }));
$('global-history').addEventListener('click', handle(async () => { historyPath = '/v1/telemetry'; offset = 0; $('history-title').textContent = 'All telemetry'; await history(); }));
$('history-next').addEventListener('click', handle(async () => { offset = nextOffset; await history(); }));
$('history-back').addEventListener('click', handle(async () => { offset = Math.max(0, offset - 50); await history(); }));
handle(async () => { await api('/v1/auth/csrf'); await load(); })();
