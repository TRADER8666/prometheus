<script>
  import { createEventDispatcher, onMount } from 'svelte';
  const API = import.meta.env.VITE_API_URL || '/api';
  const dispatch = createEventDispatcher();

  export let selectedConversation = null;
  let conversations = [];

  async function load() {
    const r = await fetch(`${API}/conversations`);
    conversations = await r.json();
  }

  async function newConversation() {
    await fetch(`${API}/conversations?title=New%20conversation`, { method: 'POST' });
    await load();
  }

  async function remove(id) {
    await fetch(`${API}/conversations/${id}`, { method: 'DELETE' });
    if (selectedConversation === id) selectedConversation = null;
    await load();
  }

  function select(id) {
    selectedConversation = id;
    dispatch('select', id);
  }

  onMount(load);
</script>

<aside>
  <div class="top">
    <h2>Prometheus</h2>
    <button on:click={newConversation}>+ New</button>
  </div>

  <div class="list">
    {#each conversations as c}
      <div class:selected={c.id === selectedConversation} class="item">
        <button class="title" on:click={() => select(c.id)}>{c.title}</button>
        <button class="del" on:click={() => remove(c.id)}>×</button>
      </div>
    {/each}
  </div>
</aside>

<style>
  aside { background: #111827; border-right: 1px solid #1f2937; padding: 12px; }
  .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
  h2 { margin:0; font-size:1.1rem; }
  button { background:#334155; border:none; color:white; padding:6px 10px; border-radius:8px; cursor:pointer; }
  .list { display:flex; flex-direction:column; gap:8px; }
  .item { display:flex; gap:8px; align-items:center; background:#1f2937; padding:6px; border-radius:8px; }
  .item.selected { outline:1px solid #38bdf8; }
  .title { flex:1; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .del { background:#7f1d1d; }
</style>
