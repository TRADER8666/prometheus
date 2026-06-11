<script>
  export let card;
</script>

<div class="card">
  <div class="title">{card.title}</div>
  {#if card.description}<div class="muted">{card.description}</div>{/if}
  <div class="meta">
    {#if card.assignee}<span>👤 {card.assignee}</span>{/if}
    {#if card.due_date}<span>📅 {card.due_date}</span>{/if}
  </div>
</div>

<style>
  .card { background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; padding:8px; margin-bottom:8px; }
  .title { font-weight:600; margin-bottom:4px; }
  .meta { display:flex; gap:8px; color:var(--text-secondary); font-size:0.82rem; }
</style>
