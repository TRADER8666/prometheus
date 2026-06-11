<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  const API = import.meta.env.VITE_API_URL || '/api';
  let recording = false;
  let mediaRecorder;
  let chunks = [];

  async function toggle() {
    if (!recording) {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      chunks = [];
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('file', blob, 'voice.webm');
        const res = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) dispatch('transcribed', data.text || '');
      };
      mediaRecorder.start();
      recording = true;
    } else {
      mediaRecorder.stop();
      recording = false;
    }
  }
</script>

<button class:rec={recording} on:click={toggle}>{recording ? '⏹ Stop' : '🎤 Speak'}</button>

<style>
  .rec { background:var(--error); }
</style>
