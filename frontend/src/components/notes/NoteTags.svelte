<script>
  import { createEventDispatcher } from 'svelte';
  export let tags = [];
  let input = '';
  const dispatch = createEventDispatcher();

  function addTag() {
    const t = input.trim();
    if (!t) return;
    if (!tags.includes(t)) tags = [...tags, t];
    input = '';
    dispatch('change', tags);
  }

  function removeTag(tag) {
    tags = tags.filter((x) => x !== tag);
    dispatch('change', tags);
  }
</script>

<div class="wrap">
  <div class="chips">
    {#each tags as tag}
      <span class="chip">{tag} <button on:click={() => removeTag(tag)}>x</button></span>
    {/each}
  </div>
  <div class="row">
    <input bind:value={input} placeholder="Add tag" on:keydown={(e)=>e.key==='Enter' && (e.preventDefault(), addTag())} />
    <button on:click={addTag}>Add</button>
  </div>
</div>

<style>
  .chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px; }
  .chip { background:#0b1220; border:1px solid var(--border); border-radius:999px; padding:4px 8px; }
  .chip button { margin-left:6px; background:var(--error); padding:2px 6px; }
  .row { display:flex; gap:8px; }
</style>
