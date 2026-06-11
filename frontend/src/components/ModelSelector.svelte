<script>
  import { createEventDispatcher, onMount } from 'svelte';
  const API = import.meta.env.VITE_API_URL || '/api';
  const dispatch = createEventDispatcher();

  export let selectedModel = 'llama3.2:3b';
  export let profile = 'balanced';

  let models = [];
  let rec = null;

  async function load() {
    try {
      const m = await fetch(`${API}/models`).then(r => r.json());
      models = (m.models || []).map(x => x.name);
    } catch {
      models = ['llama3.2:3b', 'qwen2.5-coder:1.5b'];
    }
    try {
      rec = await fetch(`${API}/cookbook/recommendations`).then(r => r.json());
    } catch {
      rec = null;
    }
  }

  function applyProfile(p) {
    profile = p;
    const preferred = rec?.recommendations?.[p]?.[0];
    if (preferred) selectedModel = preferred;
    dispatch('change', { model: selectedModel, profile });
  }

  function modelChanged() {
    dispatch('change', { model: selectedModel, profile });
  }

  onMount(load);
</script>

<div class="selector">
  <div>
    <label for="model-select">Model</label>
    <select id="model-select" bind:value={selectedModel} on:change={modelChanged}>
      {#each models as m}
        <option value={m}>{m}</option>
      {/each}
    </select>
  </div>
  <div class="profiles">
    <button on:click={() => applyProfile('quality')}>Quality</button>
    <button on:click={() => applyProfile('balanced')}>Balanced</button>
    <button on:click={() => applyProfile('speed')}>Speed</button>
  </div>
</div>

<style>
  .selector { display:flex; justify-content:space-between; align-items:center; gap:12px; background:#111827; padding:10px; border-radius:10px; }
  select { background:#1f2937; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:8px; }
  .profiles { display:flex; gap:8px; }
  button { background:#334155; color:white; border:none; padding:8px 10px; border-radius:8px; cursor:pointer; }
</style>
