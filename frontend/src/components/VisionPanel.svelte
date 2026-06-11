<script>
  const API = import.meta.env.VITE_API_URL || '/api';

  const tabs = ['detect', 'generate', 'edit', 'ocr', 'analyze'];
  let tab = 'detect';

  let imagePath = '';
  let maskPath = '';
  let prompt = '';
  let negativePrompt = '';
  let steps = 25;
  let guidanceScale = 7.5;
  let model = 'llava';

  let result = null;
  let loading = false;
  let error = '';

  async function callApi(path, body) {
    loading = true;
    error = '';
    result = null;
    try {
      const res = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Request failed');
      result = data;
    } catch (e) {
      error = e.message || 'Request failed';
    } finally {
      loading = false;
    }
  }

  function run() {
    if (tab === 'detect') {
      callApi('/detect_objects', { image_path: imagePath });
    } else if (tab === 'generate') {
      callApi('/generate_image', {
        prompt,
        negative_prompt: negativePrompt,
        steps,
        guidance_scale: guidanceScale
      });
    } else if (tab === 'edit') {
      callApi('/edit_image', {
        image_path: imagePath,
        mask_path: maskPath,
        prompt,
        negative_prompt: negativePrompt,
        steps,
        guidance_scale: guidanceScale
      });
    } else if (tab === 'ocr') {
      callApi('/extract_text', { image_path: imagePath, langs: ['en'] });
    } else if (tab === 'analyze') {
      callApi('/analyze_image', { image_path: imagePath, prompt, model });
    }
  }
</script>

<section class="panel">
  <div class="tabs">
    {#each tabs as t}
      <button class:active={tab === t} on:click={() => (tab = t)}>{t}</button>
    {/each}
  </div>

  <div class="form">
    {#if tab !== 'generate'}
      <input bind:value={imagePath} placeholder="Image path (/tmp/prometheus-images/...)" />
    {/if}

    {#if tab === 'edit'}
      <input bind:value={maskPath} placeholder="Mask path" />
    {/if}

    {#if tab === 'generate' || tab === 'edit' || tab === 'analyze'}
      <textarea bind:value={prompt} rows="3" placeholder="Prompt"></textarea>
    {/if}

    {#if tab === 'generate' || tab === 'edit'}
      <input bind:value={negativePrompt} placeholder="Negative prompt" />
      <div class="inline">
        <label for="steps">Steps</label>
        <input id="steps" type="number" bind:value={steps} min="1" max="100" />
        <label for="guidance">Guidance</label>
        <input id="guidance" type="number" step="0.1" bind:value={guidanceScale} min="1" max="20" />
      </div>
    {/if}

    {#if tab === 'analyze'}
      <input bind:value={model} placeholder="Vision model (llava/bakllava)" />
    {/if}

    <button class="run" on:click={run} disabled={loading}>{loading ? 'Running...' : 'Run'}</button>
  </div>

  {#if error}
    <pre class="error">{error}</pre>
  {/if}

  {#if result}
    <div class="result">
      {#if result.image_url}
        <img src={result.image_url} alt="result" />
      {/if}
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>
  {/if}
</section>

<style>
  .panel { background:#020617; border:1px solid #1f2937; border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:10px; }
  .tabs { display:flex; gap:8px; flex-wrap:wrap; }
  button { background:#334155; color:#fff; border:none; border-radius:8px; padding:7px 10px; cursor:pointer; }
  button.active { background:#0ea5e9; color:#062235; }
  .form { display:flex; flex-direction:column; gap:8px; }
  input, textarea { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:8px; }
  .inline { display:flex; align-items:center; gap:8px; }
  .run { background:#22c55e; color:#052e16; font-weight:600; }
  .result img { max-width:300px; border-radius:8px; border:1px solid #334155; margin-bottom:8px; }
  pre { white-space:pre-wrap; word-break:break-word; background:#0f172a; padding:8px; border-radius:8px; }
  .error { color:#fecaca; }
</style>
