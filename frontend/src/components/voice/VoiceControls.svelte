<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  export let ttsEnabled = false;
  export let voiceModel = '';
</script>

<div class="panel controls">
  <label><input type="checkbox" bind:checked={ttsEnabled} on:change={() => dispatch('change', { ttsEnabled, voiceModel })} /> Speak responses</label>
  <input bind:value={voiceModel} placeholder="Piper voice model path (optional)" on:change={() => dispatch('change', { ttsEnabled, voiceModel })} />
</div>

<style>
  .controls { display:flex; gap:8px; align-items:center; }
</style>
