<script>
  import JobEditor from './JobEditor.svelte';
  import JobHistory from './JobHistory.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  let jobs = [];
  let history = [];
  let editing = null;

  async function load() {
    jobs = await fetch(`${API}/scheduler/jobs`).then(r=>r.json()).then(d=>d.jobs||[]);
    history = await fetch(`${API}/scheduler/history`).then(r=>r.json()).then(d=>d.history||[]);
  }

  async function saveJob(e) {
    const payload = e.detail;
    if (editing?.id) {
      await fetch(`${API}/scheduler/jobs/${editing.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    } else {
      await fetch(`${API}/scheduler/jobs`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    }
    editing = null;
    await load();
  }

  async function del(id) {
    await fetch(`${API}/scheduler/jobs/${id}`, { method:'DELETE' });
    await load();
  }

  load();
</script>

<section class="panel wrap">
  <h3>Scheduler</h3>
  <div class="grid">
    <div>
      <JobEditor job={editing} on:save={saveJob} />
      <div class="panel">
        <h4>Jobs</h4>
        {#if !jobs.length}<div class="muted">No jobs</div>{/if}
        {#each jobs as j}
          <div class="job">
            <div><b>{j.name}</b> ({j.schedule})</div>
            <div class="actions">
              <button on:click={() => editing = j}>Edit</button>
              <button class="danger" on:click={() => del(j.id)}>Delete</button>
            </div>
          </div>
        {/each}
      </div>
    </div>
    <JobHistory {history} />
  </div>
</section>

<style>
  .wrap { display:flex; flex-direction:column; gap:10px; }
  .grid { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
  .job { display:flex; justify-content:space-between; gap:8px; background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; padding:8px; margin-bottom:6px; }
  .actions { display:flex; gap:6px; }
  .danger { background:var(--error); }
  @media (max-width: 1000px) { .grid { grid-template-columns:1fr; } }
</style>
