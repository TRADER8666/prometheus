<script>
  export let history = [];
</script>

<div class="panel">
  <h4>Job History</h4>
  <div class="list">
    {#if !history.length}<div class="muted">No history yet.</div>{/if}
    {#each history as h}
      <article>
        <div><b>{h.job_name || h.job_id}</b> · {h.status} · {h.run_at}</div>
        {#if h.error}<div class="error">{h.error}</div>{/if}
        {#if h.output}<pre>{JSON.stringify(h.output, null, 2)}</pre>{/if}
      </article>
    {/each}
  </div>
</div>

<style>
  .list { display:flex; flex-direction:column; gap:8px; max-height:320px; overflow:auto; }
  article { background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; padding:8px; }
</style>
