<script>
  import Sidebar from './components/Sidebar.svelte';
  import Chat from './components/Chat.svelte';
  import ModelSelector from './components/ModelSelector.svelte';
  import VisionPanel from './components/VisionPanel.svelte';

  let selectedConversation = null;
  let selectedModel = 'llama3.2:3b';
  let profile = 'balanced';
  let activeTab = 'chat';

  function onConversationSelect(event) {
    selectedConversation = event.detail;
    activeTab = 'chat';
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

    <div class="tabs">
      <button class:active={activeTab === 'chat'} on:click={() => (activeTab = 'chat')}>Chat</button>
      <button class:active={activeTab === 'vision'} on:click={() => (activeTab = 'vision')}>Vision / Images</button>
    </div>

    {#if activeTab === 'chat'}
      <Chat {selectedConversation} {selectedModel} {profile} />
    {:else}
      <VisionPanel />
    {/if}
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
  .tabs { display:flex; gap:8px; }
  .tabs button { background:#334155; border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer; }
  .tabs button.active { background:#0ea5e9; color:#062235; }
  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 1fr;
    }
  }
</style>
