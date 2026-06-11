<script>
  import { createEventDispatcher } from 'svelte';
  export let notes = [];
  export let selectedId = null;
  const dispatch = createEventDispatcher();
</script>

<div class="list">
  {#if !notes.length}
    <div class="muted">No notes yet.</div>
  {/if}
  {#each notes as note}
    <button class:selected={note.id === selectedId} on:click={() => dispatch('select', note.id)}>
      <div class="title">{note.title}</div>
      <div class="muted">{(note.tags || []).join(', ')}</div>
    </button>
  {/each}
</div>

<style>
  .list { display:flex; flex-direction:column; gap:8px; max-height:420px; overflow:auto; }
  button { text-align:left; background:var(--bg-tertiary); border:1px solid var(--border); }
  button.selected { outline:1px solid var(--primary); }
  .title { font-weight:600; }
</style>
