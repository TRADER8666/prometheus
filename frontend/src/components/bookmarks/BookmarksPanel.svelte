<script>
  import BookmarkCard from './BookmarkCard.svelte';
  import BookmarkFolders from './BookmarkFolders.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  let bookmarks = [];
  let folder = '';
  let search = '';

  $: folders = Array.from(new Set(bookmarks.map(b => b.folder).filter(Boolean)));

  async function load() {
    const q = encodeURIComponent(search || '');
    const f = encodeURIComponent(folder || '');
    bookmarks = await fetch(`${API}/bookmarks?q=${q}&folder=${f}`).then(r => r.json()).then(d => d.bookmarks || []);
  }

  async function createBookmark() {
    const url = prompt('URL');
    if (!url) return;
    const title = prompt('Title', '');
    await fetch(`${API}/bookmarks`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ url, title, folder }) });
    await load();
  }

  async function deleteBookmark(id) {
    await fetch(`${API}/bookmarks/${id}`, { method:'DELETE' });
    await load();
  }

  load();
</script>

<section class="panel">
  <div class="top">
    <h3>Bookmarks</h3>
    <div class="row">
      <input bind:value={search} placeholder="Search bookmarks" on:input={load} />
      <button on:click={createBookmark}>+ Bookmark</button>
    </div>
  </div>

  <BookmarkFolders {folders} selected={folder} onSelect={(f)=>{folder=f; load();}} />

  <div class="list">
    {#if !bookmarks.length}<div class="muted">No bookmarks</div>{/if}
    {#each bookmarks as b}
      <BookmarkCard bookmark={b} onDelete={deleteBookmark} />
    {/each}
  </div>
</section>

<style>
  .top { display:flex; justify-content:space-between; gap:10px; align-items:center; }
  .row { display:flex; gap:8px; }
  .list { display:flex; flex-direction:column; gap:8px; margin-top:8px; }
</style>
