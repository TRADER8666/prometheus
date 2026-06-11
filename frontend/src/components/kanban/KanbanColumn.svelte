<script>
  import { dndzone } from 'svelte-dnd-action';
  import KanbanCard from './KanbanCard.svelte';

  export let column;
  export let cards = [];
  export let onMove = async () => {};
  export let onCreateCard = async () => {};

  function handleFinalize(e) {
    const items = e.detail.items;
    items.forEach((item, index) => onMove(item.id, column.id, index + 1));
  }
</script>

<div class="column panel">
  <h4>{column.name}</h4>
  <div class="cards" use:dndzone={{ items: cards, flipDurationMs: 150 }} on:finalize={handleFinalize}>
    {#each cards as card (card.id)}
      <div data-id={card.id}>
        <KanbanCard {card} />
      </div>
    {/each}
  </div>
  <button on:click={() => onCreateCard(column.id)}>+ Card</button>
</div>

<style>
  .column { min-width: 280px; max-width: 320px; }
  .cards { min-height: 120px; }
</style>
