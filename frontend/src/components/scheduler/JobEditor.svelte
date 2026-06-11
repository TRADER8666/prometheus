<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let job = null;
  let name = '';
  let schedule = '0 8 * * *';
  let action = 'daily_briefing';
  let enabled = true;
  let actionPayload = '{}';

  $: if (job) {
    name = job.name || '';
    schedule = job.schedule || '0 8 * * *';
    action = job.action || 'daily_briefing';
    enabled = !!job.enabled;
    actionPayload = JSON.stringify(job.action_payload || {}, null, 2);
  }

  function submit() {
    let payload = {};
    try { payload = JSON.parse(actionPayload || '{}'); } catch { payload = {}; }
    dispatch('save', { name, schedule, action, enabled, action_payload: payload });
  }
</script>

<div class="panel">
  <h4>{job ? 'Edit Job' : 'Create Job'}</h4>
  <input bind:value={name} placeholder="Job name" />
  <input bind:value={schedule} placeholder="Cron pattern or natural language" />
  <select bind:value={action}>
    <option value="daily_briefing">daily_briefing</option>
    <option value="system_health">system_health</option>
    <option value="backup_data">backup_data</option>
    <option value="email_summary">email_summary</option>
    <option value="custom_agent_task">custom_agent_task</option>
  </select>
  <textarea rows="4" bind:value={actionPayload} placeholder="Action payload JSON"></textarea>
  <label><input type="checkbox" bind:checked={enabled} /> Enabled</label>
  <button on:click={submit}>Save Job</button>
</div>
