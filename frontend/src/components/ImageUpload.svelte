<script>
  import { createEventDispatcher } from 'svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  const dispatch = createEventDispatcher();

  let dragging = false;
  let preview = null;
  let uploading = false;
  let error = '';

  async function uploadFile(file) {
    if (!file) return;
    error = '';
    uploading = true;

    const reader = new FileReader();
    reader.onload = () => {
      preview = reader.result;
    };
    reader.readAsDataURL(file);

    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API}/upload_image`, { method: 'POST', body: fd });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'Upload failed');
      }
      const data = await res.json();
      dispatch('uploaded', data);
    } catch (e) {
      error = e.message || 'Upload failed';
    } finally {
      uploading = false;
    }
  }

  function onDrop(event) {
    event.preventDefault();
    dragging = false;
    const file = event.dataTransfer?.files?.[0];
    uploadFile(file);
  }

  function onInput(event) {
    const file = event.target.files?.[0];
    uploadFile(file);
  }
</script>

<div
  class:dragging
  class="upload"
  role="region"
  aria-label="Image upload dropzone"
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={onDrop}
>
  <label for="image-upload-input">Drag image here or click to upload</label>
  <input id="image-upload-input" type="file" accept="image/*" on:change={onInput} />

  {#if uploading}
    <div class="meta">Uploading image...</div>
  {/if}
  {#if error}
    <div class="err">{error}</div>
  {/if}
  {#if preview}
    <img src={preview} alt="preview" />
  {/if}
</div>

<style>
  .upload {
    border: 1px dashed #475569;
    border-radius: 10px;
    padding: 10px;
    background: #0b1220;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .upload.dragging { border-color: #38bdf8; background: #0f1c35; }
  label { cursor: pointer; font-size: 0.9rem; }
  input { display: block; }
  img { max-height: 140px; object-fit: contain; border-radius: 8px; border: 1px solid #334155; }
  .meta { color: #cbd5e1; font-size: 0.85rem; }
  .err { color: #fca5a5; font-size: 0.85rem; }
</style>
