<script>
  import NotesList from './NotesList.svelte';
  import NoteEditor from './NoteEditor.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  let notes = [];
  let selectedId = null;
  let search = '';

  $: selected = notes.find((n) => n.id === selectedId) || null;

  async function load() {
    const q = encodeURIComponent(search || '');
    notes = await fetch(`${API}/notes?q=${q}`).then((r) => r.json()).then((d) => d.notes || []);
    if (!selectedId && notes.length) selectedId = notes[0].id;
  }

  async function createNew() {
    const res = await fetch(`${API}/notes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'Untitled note', content: '', tags: [] })
    }).then((r) => r.json());
    await load();
    selectedId = res.note?.id;
  }

  async function saveNote(payload) {
    if (selectedId) {
      await fetch(`${API}/notes/${selectedId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    } else {
      await fetch(`${API}/notes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    }
    await load();
  }

  async function deleteNote(id) {
    await fetch(`${API}/notes/${id}`, { method: 'DELETE' });
    selectedId = null;
    await load();
  }

  load();
</script>

<section class="panel notes-wrap">
  <div class="top">
    <h3>Notes</h3>
    <div class="actions">
      <input bind:value={search} placeholder="Search notes" on:input={load} />
      <button on:click={createNew}>New</button>
    </div>
  </div>

  <div class="layout">
    <NotesList {notes} {selectedId} on:select={(e)=>selectedId=e.detail} />
    <NoteEditor note={selected} onSave={saveNote} onDelete={deleteNote} />
  </div>
</section>

<style>
  .notes-wrap { display:flex; flex-direction:column; gap:10px; }
  .top { display:flex; justify-content:space-between; gap:10px; }
  .actions { display:flex; gap:8px; }
  .layout { display:grid; grid-template-columns:320px 1fr; gap:10px; }
  @media (max-width: 1000px) { .layout { grid-template-columns:1fr; } }
</style>
