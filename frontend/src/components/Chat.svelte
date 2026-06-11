<script>
  import { marked } from 'marked';
  import { onMount } from 'svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  export let selectedConversation = null;
  export let selectedModel = 'llama3.2:3b';
  export let profile = 'balanced';

  let messages = [];
  let input = '';
  let uploading = false;

  $: if (selectedConversation) loadMessages();

  async function loadMessages() {
    const r = await fetch(`${API}/conversations/${selectedConversation}/messages`);
    messages = await r.json();
  }

  async function send() {
    const text = input.trim();
    if (!text) return;

    messages = [...messages, { role: 'user', content: text }, { role: 'assistant', content: '' }];
    input = '';

    const payload = {
      conversation_id: selectedConversation,
      message: text,
      model: selectedModel,
      profile,
      use_tools: true,
      use_rag: true
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
        } catch {}
      }
    }

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
    <textarea bind:value={input} rows="3" placeholder="Ask anything... use tool syntax like [[tool:search query]]"></textarea>
    <button on:click={send}>Send</button>
  </div>
</section>

<style>
  .chat { display:flex; flex-direction:column; gap:12px; height:calc(100vh - 100px); }
  .toolbar { display:flex; align-items:center; gap:10px; }
  .upload { background:#1e293b; padding:8px 12px; border-radius:8px; cursor:pointer; }
  .upload input { display:none; }
  .messages { flex:1; overflow:auto; background:#020617; border:1px solid #1f2937; border-radius:10px; padding:12px; }
  article { display:flex; margin-bottom:10px; }
  article.user { justify-content:flex-end; }
  .bubble { max-width:80%; padding:10px; border-radius:12px; background:#1e293b; }
  article.user .bubble { background:#0ea5e9; color:#001018; }
  .composer { display:flex; gap:10px; }
  textarea { flex:1; background:#111827; color:#e5e7eb; border:1px solid #334155; border-radius:8px; padding:10px; }
  button { background:#22c55e; color:#052e16; border:none; border-radius:8px; padding:0 16px; font-weight:600; }
</style>
