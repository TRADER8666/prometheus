<script>
  import { marked } from 'marked';
  import NoteTags from './NoteTags.svelte';
  export let note = null;
  export let onSave = async () => {};
  export let onDelete = async () => {};

  let title = '';
  let content = '';
  let tags = [];

  $: if (note) {
    title = note.title || '';
    content = note.content || '';
    tags = note.tags || [];
  }

  async function save() {
    await onSave({ title, content, tags });
  }
</script>

<div class="editor panel">
  <input bind:value={title} placeholder="Note title" />
  <NoteTags bind:tags on:change={(e)=>tags=e.detail} />
  <div class="grid">
    <textarea rows="12" bind:value={content} placeholder="Write markdown..."></textarea>
    <div class="preview">{@html marked.parse(content || '')}</div>
  </div>
  <div class="row">
    <button on:click={save}>Save</button>
    {#if note?.id}<button class="danger" on:click={() => onDelete(note.id)}>Delete</button>{/if}
  </div>
</div>

<style>
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .preview { background:#0b1220; border:1px solid var(--border); border-radius:8px; padding:8px; overflow:auto; }
  .row { display:flex; gap:8px; margin-top:8px; }
  .danger { background:var(--error); }
  @media (max-width: 900px) { .grid { grid-template-columns:1fr; } }
</style>
