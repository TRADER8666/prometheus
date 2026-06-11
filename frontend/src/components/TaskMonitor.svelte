<script>
  export let events = [];

  function latestByTask(events) {
    const map = new Map();
    for (const e of events) {
      if (e.task_id) map.set(e.task_id, e);
    }
    return Array.from(map.values()).reverse();
  }

  $: latest = latestByTask(events);
</script>

<section class="panel">
  <h3>Task Monitor</h3>
  <div class="list">
    {#if !latest.length}
      <div class="empty">No DAG updates yet.</div>
    {/if}
    {#each latest as item}
      <article>
        <div><b>Task:</b> {item.task_id}</div>
        <div><b>Type:</b> {item.type}</div>
        <details>
          <summary>Details</summary>
          <pre>{JSON.stringify(item.state || item, null, 2)}</pre>
        </details>
      </article>
    {/each}
  </div>
</section>

<style>
  .panel { background:#020617; border:1px solid #1f2937; border-radius:10px; padding:10px; }
  .list { display:flex; flex-direction:column; gap:8px; max-height:380px; overflow:auto; }
  article { background:#0f172a; border:1px solid #334155; border-radius:8px; padding:8px; }
  .empty { color:#94a3b8; }
  pre { background:#020617; padding:8px; border-radius:8px; overflow:auto; }
</style>
