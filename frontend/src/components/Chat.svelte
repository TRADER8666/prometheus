<script>
  import { marked } from 'marked';
  import ImageUpload from './ImageUpload.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  export let selectedConversation = null;
  export let selectedModel = 'llama3.2:3b';
  export let profile = 'balanced';

  let messages = [];
  let input = '';
  let uploading = false;
  let attachedImages = [];

  $: if (selectedConversation) loadMessages();

  async function loadMessages() {
    const r = await fetch(`${API}/conversations/${selectedConversation}/messages`);
    messages = await r.json();
  }

  function onImageUploaded(event) {
    const data = event.detail;
    attachedImages = [...attachedImages, data];
  }

  function removeAttachment(idx) {
    attachedImages = attachedImages.filter((_, i) => i !== idx);
  }

  async function send() {
    const text = input.trim();
    if (!text && attachedImages.length === 0) return;

    const attachmentText = attachedImages.length
      ? `\n\nAttached images:\n${attachedImages.map(a => `![${a.filename}](${a.image_url})`).join('\n')}`
      : '';
    const finalText = `${text}${attachmentText}`.trim();

    messages = [...messages, { role: 'user', content: finalText }, { role: 'assistant', content: '' }];
    input = '';

    const payload = {
      conversation_id: selectedConversation,
      message: finalText,
      model: selectedModel,
      profile,
      use_tools: true,
      use_rag: true,
      image_paths: attachedImages.map(a => a.image_path),
      vision_model: 'llava'
    };

    const resp = await fetch(`${API}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let acc = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
      for (const line of lines) {
        const data = line.slice(6);
        if (data === '[DONE]') continue;
        try {
          const obj = JSON.parse(data);
          acc += obj.delta || '';
          messages[messages.length - 1].content = acc;
          messages = messages;
          if (!selectedConversation && obj.conversation_id) selectedConversation = obj.conversation_id;
        } catch {
          // no-op
        }
      }
    }

    attachedImages = [];
    if (selectedConversation) await loadMessages();
  }

  async function onUpload(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    uploading = true;
    const fd = new FormData();
    fd.append('file', f);
    await fetch(`${API}/documents/upload`, { method: 'POST', body: fd });
    uploading = false;
  }

  function render(md) {
    return marked.parse(md || '');
  }
</script>

<section class="chat">
  <div class="toolbar">
    <label class="upload">
      Upload doc for RAG
      <input type="file" on:change={onUpload} />
    </label>
    {#if uploading}<span>Uploading...</span>{/if}
  </div>

  <ImageUpload on:uploaded={onImageUploaded} />
  {#if attachedImages.length}
    <div class="attachments">
      {#each attachedImages as item, idx}
        <div class="chip">
          <img src={item.image_url} alt={item.filename} />
          <span>{item.filename}</span>
          <button on:click={() => removeAttachment(idx)}>x</button>
        </div>
      {/each}
    </div>
  {/if}

  <div class="messages">
    {#each messages as m}
      <article class={m.role}>
        <div class="bubble">
          {@html render(m.content)}
        </div>
      </article>
    {/each}
  </div>

  <div class="composer">
    <textarea bind:value={input} rows="3" placeholder="Ask anything. You can attach images above."></textarea>
    <button on:click={send}>Send</button>
  </div>
</section>

<style>
  .chat { display:flex; flex-direction:column; gap:12px; height:calc(100vh - 130px); }
  .toolbar { display:flex; align-items:center; gap:10px; }
  .upload { background:#1e293b; padding:8px 12px; border-radius:8px; cursor:pointer; }
  .upload input { display:none; }
  .attachments { display:flex; gap:8px; flex-wrap:wrap; }
  .chip { display:flex; align-items:center; gap:6px; background:#111827; border:1px solid #334155; border-radius:8px; padding:4px 6px; }
  .chip img { width:28px; height:28px; object-fit:cover; border-radius:4px; }
  .chip button { background:#7f1d1d; color:#fff; border:none; border-radius:6px; cursor:pointer; }
  .messages { flex:1; overflow:auto; background:#020617; border:1px solid #1f2937; border-radius:10px; padding:12px; }
  article { display:flex; margin-bottom:10px; }
  article.user { justify-content:flex-end; }
  :global(.bubble img) { max-width:240px; border-radius:8px; border:1px solid #334155; }
  .bubble { max-width:80%; padding:10px; border-radius:12px; background:#1e293b; }
  article.user .bubble { background:#0ea5e9; color:#001018; }
  .composer { display:flex; gap:10px; }
  textarea { flex:1; background:#111827; color:#e5e7eb; border:1px solid #334155; border-radius:8px; padding:10px; }
  button { background:#22c55e; color:#052e16; border:none; border-radius:8px; padding:0 16px; font-weight:600; }
</style>
