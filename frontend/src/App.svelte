<script>
  import { onMount } from 'svelte';
  import Sidebar from './components/Sidebar.svelte';
  import Chat from './components/Chat.svelte';
  import ModelSelector from './components/ModelSelector.svelte';
  import VisionPanel from './components/VisionPanel.svelte';
  import PlanPanel from './components/PlanPanel.svelte';
  import DAGVisualizer from './components/DAGVisualizer.svelte';
  import TaskMonitor from './components/TaskMonitor.svelte';
  import NotesPanel from './components/notes/NotesPanel.svelte';
  import KanbanBoard from './components/kanban/KanbanBoard.svelte';
  import BookmarksPanel from './components/bookmarks/BookmarksPanel.svelte';
  import SchedulerPanel from './components/scheduler/SchedulerPanel.svelte';

  let selectedConversation = null;
  let selectedModel = 'llama3.2:3b';
  let profile = 'balanced';

  let section = 'chat';
  const sections = [
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'orchestration', label: 'Orchestration', icon: '🕸️' },
    { id: 'vision', label: 'Vision', icon: '🖼️' },
    { id: 'notes', label: 'Notes', icon: '📝' },
    { id: 'kanban', label: 'Kanban', icon: '📋' },
    { id: 'bookmarks', label: 'Bookmarks', icon: '🔖' },
    { id: 'scheduler', label: 'Scheduler', icon: '⏱️' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  let dagEvents = [];
  let dagState = null;
  let wsStatus = 'disconnected';

  function onConversationSelect(event) {
    selectedConversation = event.detail;
    section = 'chat';
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
        dagEvents = [...dagEvents, data].slice(-300);
        if (data.state?.nodes) dagState = data.state;
      } catch {
        // ignore invalid message
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

  $: breadcrumb = `Home / ${sections.find(s => s.id === section)?.label || 'Chat'}`;

  onMount(connectWs);
</script>

<div class="shell">
  <aside class="main-nav panel">
    <h2>Prometheus</h2>
    <nav>
      {#each sections as s}
        <button class:active={section === s.id} on:click={() => section = s.id}>
          <span>{s.icon}</span> {s.label}
        </button>
      {/each}
    </nav>
    <div class="muted">WS: {wsStatus}</div>
  </aside>

  <main>
    <div class="crumb muted">{breadcrumb}</div>
    <ModelSelector bind:selectedModel bind:profile on:change={onModelChange} />

    {#if section === 'chat'}
      <div class="chat-layout">
        <Sidebar bind:selectedConversation on:select={onConversationSelect} />
        <Chat {selectedConversation} {selectedModel} {profile} />
      </div>
    {:else if section === 'orchestration'}
      <div class="orchestration-grid">
        <PlanPanel on:executed={onPlanExecuted} />
        <DAGVisualizer {dagState} />
        <TaskMonitor events={dagEvents} />
      </div>
    {:else if section === 'vision'}
      <VisionPanel />
    {:else if section === 'notes'}
      <NotesPanel />
    {:else if section === 'kanban'}
      <KanbanBoard />
    {:else if section === 'bookmarks'}
      <BookmarksPanel />
    {:else if section === 'scheduler'}
      <SchedulerPanel />
    {:else}
      <section class="panel">
        <h3>Settings</h3>
        <p class="muted">General app settings and keyboard shortcuts will appear here.</p>
        <ul>
          <li><b>Ctrl/Cmd + Enter</b> send chat (planned)</li>
          <li><b>/</b> focus search (planned)</li>
        </ul>
      </section>
    {/if}
  </main>
</div>

<style>
  .shell { display:grid; grid-template-columns: 230px 1fr; min-height:100vh; gap:12px; padding:12px; }
  .main-nav { display:flex; flex-direction:column; gap:10px; }
  nav { display:flex; flex-direction:column; gap:8px; }
  nav button { text-align:left; background:var(--bg-tertiary); border:1px solid var(--border); }
  nav button.active { outline:1px solid var(--primary); background:rgba(99,102,241,0.2); }
  main { display:flex; flex-direction:column; gap:12px; }
  .crumb { font-size:0.86rem; }
  .chat-layout { display:grid; grid-template-columns: 290px 1fr; gap:10px; min-height: 700px; }
  .orchestration-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .orchestration-grid :global(section.panel):last-child,
  .orchestration-grid :global(div.panel):last-child { grid-column: 1 / -1; }

  @media (max-width: 1100px) {
    .orchestration-grid { grid-template-columns:1fr; }
    .chat-layout { grid-template-columns:1fr; }
  }
  @media (max-width: 900px) {
    .shell { grid-template-columns:1fr; }
  }
</style>
