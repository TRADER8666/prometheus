<script>
  import { onMount } from 'svelte';
  import cytoscape from 'cytoscape';

  export let dagState = null;
  let container;
  let cy;

  function colorFor(state) {
    if (state === 'COMPLETED') return '#22c55e';
    if (state === 'IN_PROGRESS') return '#3b82f6';
    if (state === 'FAILED') return '#ef4444';
    if (state === 'SKIPPED') return '#a855f7';
    return '#6b7280';
  }

  function buildElements() {
    if (!dagState?.nodes) return [];
    const elements = [];
    for (const [id, n] of Object.entries(dagState.nodes)) {
      elements.push({
        data: {
          id,
          label: `${id}\n${n.task?.action || ''}\n${n.state}`,
          color: colorFor(n.state)
        }
      });
      for (const dep of n.dependencies || []) {
        elements.push({ data: { id: `${dep}->${id}`, source: dep, target: id } });
      }
    }
    return elements;
  }

  function renderGraph() {
    const elements = buildElements();
    if (!container) return;

    if (cy) {
      cy.destroy();
      cy = null;
    }

    cy = cytoscape({
      container,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#e5e7eb',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': 120,
            'font-size': 9,
            'shape': 'round-rectangle',
            'padding': 8
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#64748b',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: { name: 'breadthfirst', directed: true, padding: 20 }
    });
  }

  $: dagState, renderGraph();
  onMount(renderGraph);
</script>

<div class="panel">
  <h3>DAG Visualizer</h3>
  <div bind:this={container} class="graph"></div>
  {#if dagState}
    <pre>{JSON.stringify(dagState, null, 2)}</pre>
  {/if}
</div>

<style>
  .panel { background:#020617; border:1px solid #1f2937; border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:10px; }
  .graph { height:360px; border:1px solid #334155; border-radius:8px; background:#0f172a; }
  pre { max-height:200px; overflow:auto; background:#0f172a; padding:8px; border-radius:8px; }
</style>
