<script>
  export let folders = [];
  export let selected = '';
  export let onSelect = () => {};
</script>

<div class="panel folders">
  <button class:active={!selected} on:click={() => onSelect('')}>All</button>
  {#each folders as f}
    <button class:active={selected === f} on:click={() => onSelect(f)}>{f}</button>
  {/each}
</div>

<style>
  .folders { display:flex; gap:8px; flex-wrap:wrap; }
  button { background:var(--bg-tertiary); border:1px solid var(--border); }
  button.active { outline:1px solid var(--primary); }
</style>
