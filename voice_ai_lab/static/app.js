'use strict';
const $ = id => document.getElementById(id);
let labKey = '';
let pending = null;
function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
async function api(path, options = {}) {
  if (!labKey) throw new Error('Connect with your local lab key first.');
  const response = await fetch('/api/v1/' + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Lab-Key': labKey },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${body.error?.message || 'Request failed'}`);
  return body;
}
async function refresh() {
  const [leads, metrics] = await Promise.all([api('leads'), api('metrics')]);
  $('counts').textContent = `${metrics.data.persisted_test_leads} persisted test leads · ${metrics.data.retrieval_requests} retrieval requests · showing latest 20 leads`;
  $('leads').replaceChildren();
  if (!leads.data.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 4; cell.textContent = 'No persisted test leads yet.';
    row.append(cell); $('leads').append(row);
  }
  for (const lead of leads.data) {
    const row = document.createElement('tr');
    for (const value of [lead.id, `${lead.name} (${lead.email})`, lead.course_id, new Date(lead.created_at).toLocaleString()]) {
      const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
    }
    $('leads').append(row);
  }
}
$('connect-form').addEventListener('submit', async event => {
  event.preventDefault(); labKey = $('key').value.trim();
  try {
    const catalog = await api('catalog');
    $('course').replaceChildren();
    for (const course of catalog.data) {
      const option = document.createElement('option');
      option.value = course.id; option.textContent = course.name; $('course').append(option);
    }
    await refresh(); status('Connected to the local simulation. All course information is fictional.');
  } catch (error) { labKey = ''; status(error.message, true); }
});
$('question-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const {data} = await api('questions', {method: 'POST', body: JSON.stringify({text: $('question').value})});
    $('answer').classList.remove('error');
    $('answer').textContent = `${data.reply}\n\nSources: ${data.sources.join(', ') || 'No match'}\nLocal retrieval: ${data.retrieval_ms} ms (not voice latency)`;
    await refresh();
  } catch (error) { $('answer').textContent = error.message; $('answer').classList.add('error'); }
});
$('lead-form').addEventListener('submit', async event => {
  event.preventDefault();
  const payload = {name: $('name').value, email: $('email').value, course_id: $('course').value, consent: $('consent').checked};
  const signature = JSON.stringify(payload);
  if (!pending || pending.signature !== signature) pending = {signature, id: crypto.randomUUID()};
  const button = event.submitter; button.disabled = true;
  try {
    const result = await api('leads', {method: 'POST', body: JSON.stringify({...payload, request_id: pending.id})});
    $('receipt').classList.remove('error');
    $('receipt').textContent = `Confirmed database commit: lead #${result.data.id}.\n${result.replayed ? 'Retry recognized; no duplicate created.' : 'New fictional lead saved.'}\nRequest: ${pending.id}`;
    await refresh();
  } catch (error) {
    $('receipt').classList.add('error');
    $('receipt').textContent = `${error.message}\nNo new save is confirmed. Retry unchanged details to reuse the request ID.`;
  } finally { button.disabled = false; }
});
$('refresh').addEventListener('click', () => refresh().catch(error => status(error.message, true)));
for (const button of document.querySelectorAll('[data-question]')) {
  button.addEventListener('click', () => { $('question').value = button.dataset.question; $('question').focus(); });
}
