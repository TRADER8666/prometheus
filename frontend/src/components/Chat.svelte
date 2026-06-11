<script>
  import { marked } from 'marked';
  import ImageUpload from './ImageUpload.svelte';
  import VoiceInput from './voice/VoiceInput.svelte';
  import VoiceControls from './voice/VoiceControls.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  export let selectedConversation = null;
  export let selectedModel = 'llama3.2:3b';
  export let profile = 'balanced';

  let messages = [];
  let input = '';
  let uploading = false;
  let attachedImages = [];
  let ttsEnabled = false;
  let voiceModel = '';
  let latestAudioUrl = '';

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

  async function speak(text) {
    if (!ttsEnabled || !text?.trim()) return;
    const res = await fetch(`${API}/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_model: voiceModel || null })
    });
    if (res.ok) {
      const blob = await res.blob();
      latestAudioUrl = URL.createObjectURL(blob);
    }
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
          // ignore parse errors
        }
      }
    }

    attachedImages = [];
    if (selectedConversation) await loadMessages();
    await speak(acc);
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

  function onTranscribed(event) {
    const text = event.detail || '';
    input = input ? `${input} ${text}` : text;
  }

  function render(md) {
    return marked.parse(md || '');
  }
</script>

<section class="chat panel">
  <div class="toolbar">
    <label class="upload">
      Upload doc for RAG
      <input type="file" on:change={onUpload} />
    </label>
    <VoiceInput on:transcribed={onTranscribed} />
    {#if uploading}<span>Uploading...</span>{/if}
  </div>

  <VoiceControls bind:ttsEnabled bind:voiceModel />

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

  {#if latestAudioUrl}
    <audio controls src={latestAudioUrl}></audio>
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
    <textarea bind:value={input} rows="3" placeholder="Ask anything. You can attach images or use voice."></textarea>
    <button on:click={send}>Send</button>
  </div>
</section>

<style>
  .chat { display:flex; flex-direction:column; gap:12px; height:calc(100vh - 130px); }
  .toolbar { display:flex; align-items:center; gap:10px; }
  .upload { background:var(--bg-tertiary); padding:8px 12px; border-radius:8px; cursor:pointer; border:1px solid var(--border); }
  .upload input { display:none; }
  .attachments { display:flex; gap:8px; flex-wrap:wrap; }
  .chip { display:flex; align-items:center; gap:6px; background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; padding:4px 6px; }
  .chip img { width:28px; height:28px; object-fit:cover; border-radius:4px; }
  .chip button { background:var(--error); color:#fff; border:none; border-radius:6px; cursor:pointer; }
  .messages { flex:1; overflow:auto; background:#020617; border:1px solid var(--border); border-radius:10px; padding:12px; }
  article { display:flex; margin-bottom:10px; }
  article.user { justify-content:flex-end; }
  :global(.bubble img) { max-width:240px; border-radius:8px; border:1px solid var(--border); }
  .bubble { max-width:80%; padding:10px; border-radius:12px; background:var(--bg-tertiary); }
  article.user .bubble { background:var(--secondary); color:white; }
  .composer { display:flex; gap:10px; }
  textarea { flex:1; }
</style>
