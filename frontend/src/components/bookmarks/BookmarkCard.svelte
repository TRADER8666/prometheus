<script>
  export let bookmark;
  export let onDelete = async () => {};
</script>

<div class="card">
  <div class="line">
    <a href={bookmark.url} target="_blank" rel="noreferrer">{bookmark.title || bookmark.url}</a>
    <button on:click={() => onDelete(bookmark.id)}>Delete</button>
  </div>
  <div class="muted">{bookmark.description}</div>
  <div class="muted">Folder: {bookmark.folder || 'default'} | Tags: {(bookmark.tags || []).join(', ')}</div>
</div>

<style>
  .card { background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; padding:8px; }
  .line { display:flex; justify-content:space-between; gap:8px; }
  a { color:#93c5fd; }
</style>
