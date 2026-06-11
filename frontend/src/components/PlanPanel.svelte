<script>
  import { createEventDispatcher } from 'svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  const dispatch = createEventDispatcher();

  let requestText = '';
  let plan = [];
  let planText = '[]';
  let loading = false;
  let executing = false;
  let error = '';

  async function generatePlan() {
    loading = true;
    error = '';
    try {
      const res = await fetch(`${API}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: requestText })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Plan generation failed');
      plan = data.plan || [];
      planText = JSON.stringify(plan, null, 2);
    } catch (e) {
      error = e.message || 'Plan generation failed';
    } finally {
      loading = false;
    }
  }

  async function executePlan() {
    executing = true;
    error = '';
    try {
      try {
        plan = JSON.parse(planText || '[]');
      } catch {
        throw new Error('Invalid plan JSON');
      }

      const res = await fetch(`${API}/execute_dag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: requestText, plan, max_parallel: 4 })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'Execution failed');
      dispatch('executed', data);
    } catch (e) {
      error = e.message || 'Execution failed';
    } finally {
      executing = false;
    }
  }
</script>

<section class="panel">
  <h3>Plan Panel</h3>
  <textarea rows="4" bind:value={requestText} placeholder="Describe a complex multi-step task..."></textarea>
  <div class="row">
    <button on:click={generatePlan} disabled={loading}>{loading ? 'Planning...' : 'Generate Plan'}</button>
    <button on:click={executePlan} disabled={executing}>{executing ? 'Executing...' : 'Execute DAG'}</button>
  </div>

  {#if error}<div class="error">{error}</div>{/if}

  <div class="plan">
    <h4>Editable Plan JSON</h4>
    <textarea rows="10" bind:value={planText}></textarea>
  </div>
</section>

<style>
  .panel { background:#020617; border:1px solid #1f2937; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:8px; }
  textarea { width:100%; background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:8px; }
  .row { display:flex; gap:8px; }
  button { background:#334155; border:none; color:#fff; padding:8px 10px; border-radius:8px; cursor:pointer; }
  .error { color:#fca5a5; }
</style>
