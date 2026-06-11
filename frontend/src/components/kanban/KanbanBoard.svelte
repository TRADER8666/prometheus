<script>
  import KanbanColumn from './KanbanColumn.svelte';

  const API = import.meta.env.VITE_API_URL || '/api';
  let boards = [];
  let selectedBoard = null;
  let columns = [];
  let cards = [];

  async function loadBoards() {
    boards = await fetch(`${API}/kanban/boards`).then(r => r.json()).then(d => d.boards || []);
    if (!selectedBoard && boards.length) selectedBoard = boards[0].id;
    if (selectedBoard) await loadBoardData(selectedBoard);
  }

  async function loadBoardData(boardId) {
    columns = await fetch(`${API}/kanban/columns?board_id=${boardId}`).then(r => r.json()).then(d => d.columns || []);
    cards = await fetch(`${API}/kanban/cards`).then(r => r.json()).then(d => d.cards || []);
  }

  async function createBoard() {
    const name = prompt('Board name', 'New Board');
    if (!name) return;
    await fetch(`${API}/kanban/boards`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name }) });
    await loadBoards();
  }

  async function createColumn() {
    if (!selectedBoard) return;
    const name = prompt('Column name', 'To Do');
    if (!name) return;
    await fetch(`${API}/kanban/columns`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ board_id:selectedBoard, name }) });
    await loadBoardData(selectedBoard);
  }

  async function createCard(columnId) {
    const title = prompt('Card title', 'New task');
    if (!title) return;
    await fetch(`${API}/kanban/cards`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ column_id: columnId, title }) });
    await loadBoardData(selectedBoard);
  }

  async function moveCard(cardId, targetColumnId, position) {
    await fetch(`${API}/kanban/cards/${cardId}/move`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ target_column_id: targetColumnId, position }) });
    await loadBoardData(selectedBoard);
  }

  function cardsFor(columnId) {
    return cards.filter(c => c.column_id === columnId).sort((a,b) => a.position - b.position);
  }

  loadBoards();
</script>

<section class="panel">
  <div class="top">
    <h3>Kanban</h3>
    <div class="row">
      <select bind:value={selectedBoard} on:change={() => loadBoardData(selectedBoard)}>
        {#each boards as b}
          <option value={b.id}>{b.name}</option>
        {/each}
      </select>
      <button on:click={createBoard}>+ Board</button>
      <button on:click={createColumn}>+ Column</button>
    </div>
  </div>
  <div class="columns">
    {#each columns as col}
      <KanbanColumn column={col} cards={cardsFor(col.id)} onMove={moveCard} onCreateCard={createCard} />
    {/each}
  </div>
</section>

<style>
  .top { display:flex; justify-content:space-between; gap:10px; align-items:center; }
  .row { display:flex; gap:8px; }
  .columns { display:flex; gap:10px; overflow:auto; padding-bottom:6px; }
  select { min-width:180px; }
</style>
