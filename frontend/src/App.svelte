<script>
  import Sidebar from './components/Sidebar.svelte';
  import Chat from './components/Chat.svelte';
  import ModelSelector from './components/ModelSelector.svelte';

  let selectedConversation = null;
  let selectedModel = 'llama3.2:3b';
  let profile = 'balanced';

  function onConversationSelect(event) {
    selectedConversation = event.detail;
  }

  function onModelChange(event) {
    selectedModel = event.detail.model;
    profile = event.detail.profile;
  }
</script>

<div class="layout">
  <Sidebar bind:selectedConversation on:select={onConversationSelect} />
  <main>
    <ModelSelector bind:selectedModel bind:profile on:change={onModelChange} />
    <Chat {selectedConversation} {selectedModel} {profile} />
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    font-family: Inter, system-ui, -apple-system, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
  }
  .layout {
    display: grid;
    grid-template-columns: 290px 1fr;
    min-height: 100vh;
  }
  main {
    display: flex;
    flex-direction: column;
    padding: 16px;
    gap: 12px;
  }
  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 1fr;
    }
  }
</style>
