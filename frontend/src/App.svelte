<script>
  import { onMount } from 'svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Chat from './components/Chat.svelte';
  import ModelSelector from './components/ModelSelector.svelte';
  import VisionPanel from './components/VisionPanel.svelte';
  import PlanPanel from './components/PlanPanel.svelte';
  import DAGVisualizer from './components/DAGVisualizer.svelte';
  import TaskMonitor from './components/TaskMonitor.svelte';

  let selectedConversation = null;
  let selectedModel = 'llama3.2:3b';
  let profile = 'balanced';
  let activeTab = 'chat';

  let dagEvents = [];
  let dagState = null;
  let wsStatus = 'disconnected';

  function onConversationSelect(event) {
    selectedConversation = event.detail;
    activeTab = 'chat';
  }

  function onModelChange(event) {
    selectedModel = event.detail.model;
    profile = event.detail.profile;
  }

  function onPlanExecuted(event) {
    const result = event.detail?.result;
    if (result?.dag) dagState = result.dag;
  }

  function connectWs() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/dag`);

    ws.onopen = () => {
      wsStatus = 'connected';
      ws.send('subscribe');
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        dagEvents = [...dagEvents, data].slice(-200);
        if (data.state?.nodes) dagState = data.state;
      } catch {
        // ignore non-json
      }
    };

    ws.onclose = () => {
      wsStatus = 'disconnected';
      setTimeout(connectWs, 1500);
    };

    ws.onerror = () => {
      wsStatus = 'error';
      ws.close();
    };
  }

  onMount(connectWs);
</script>

<div class="layout">
  <Sidebar bind:selectedConversation on:select={onConversationSelect} />
  <main>
    <ModelSelector bind:selectedModel bind:profile on:change={onModelChange} />

    <div class="tabs">
      <button class:active={activeTab === 'chat'} on:click={() => (activeTab = 'chat')}>Chat</button>
      <button class:active={activeTab === 'vision'} on:click={() => (activeTab = 'vision')}>Vision / Images</button>
      <button class:active={activeTab === 'orchestration'} on:click={() => (activeTab = 'orchestration')}>Orchestration</button>
      <span class="ws">WS: {wsStatus}</span>
    </div>

    {#if activeTab === 'chat'}
      <Chat {selectedConversation} {selectedModel} {profile} />
    {:else if activeTab === 'vision'}
      <VisionPanel />
    {:else}
      <div class="orchestration-grid">
        <PlanPanel on:executed={onPlanExecuted} />
        <DAGVisualizer {dagState} />
        <TaskMonitor events={dagEvents} />
      </div>
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
  .layout { display: grid; grid-template-columns: 290px 1fr; min-height: 100vh; }
  main { display: flex; flex-direction: column; padding: 16px; gap: 12px; }
  .tabs { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .tabs button { background:#334155; border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer; }
  .tabs button.active { background:#0ea5e9; color:#062235; }
  .ws { margin-left:auto; font-size:0.85rem; color:#93c5fd; }
  .orchestration-grid {
    display:grid;
    grid-template-columns: 1fr 1fr;
    gap:12px;
  }
  .orchestration-grid :global(section.panel):last-child,
  .orchestration-grid :global(div.panel):last-child {
    grid-column: 1 / -1;
  }
  @media (max-width: 1100px) {
    .orchestration-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 900px) {
    .layout { grid-template-columns: 1fr; }
  }
</style>
