<script lang="ts" generics="Row">
  /**
   * A sortable table for the many-columns questions (endpoints, AI calls, errors).
   * A table is the honest form when more than a few numbers per row matter.
   * Rows can expand to show detail (an error's stack).
   */
  import Icon from '$lib/components/ui/Icon.svelte';

  type Column = {
    key: string;
    label: string;
    value: (row: Row) => string | number | null;
    /** Display text; defaults to the value. */
    text?: (row: Row) => string;
    numeric?: boolean;
    /** Narrow, truncated, with a tooltip: for long names. */
    wide?: boolean;
  };

  let {
    title,
    subtitle = undefined,
    rows,
    columns,
    id,
    detail = undefined,
    initialSort = undefined,
    emptyText = 'Nothing recorded in this range.',
    stale = false
  }: {
    title: string;
    subtitle?: string;
    rows: Row[];
    columns: Column[];
    id: (row: Row) => string;
    detail?: import('svelte').Snippet<[Row]>;
    initialSort?: { key: string; dir: 'asc' | 'desc' };
    emptyText?: string;
    stale?: boolean;
  } = $props();

  let sort = $state<{ key: string; dir: 'asc' | 'desc' } | undefined>(undefined);
  let open = $state<string | null>(null);
  const active = $derived(sort ?? initialSort);

  const sorted = $derived.by(() => {
    if (!active) return rows;
    const column = columns.find((c) => c.key === active.key);
    if (!column) return rows;
    const direction = active.dir === 'asc' ? 1 : -1;
    // Missing values sink to the bottom whichever way it is sorted.
    return [...rows].sort((a, b) => {
      const va = column.value(a);
      const vb = column.value(b);
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      return (va < vb ? -1 : va > vb ? 1 : 0) * direction;
    });
  });

  function toggle(key: string) {
    sort =
      active?.key === key
        ? { key, dir: active.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: columns.find((c) => c.key === key)?.numeric ? 'desc' : 'asc' };
  }
</script>

<section class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
  <header class="mb-3">
    <h3 class="text-sm font-semibold text-[var(--viz-ink)]">{title}</h3>
    {#if subtitle}<p class="mt-0.5 text-xs text-[var(--viz-ink-3)]">{subtitle}</p>{/if}
  </header>

  {#if !rows.length}
    <p class="py-6 text-center text-xs text-[var(--viz-ink-3)]">{emptyText}</p>
  {:else}
    <div
      class="max-h-96 overflow-auto rounded-lg border border-slate-800 transition-opacity {stale
        ? 'opacity-50'
        : ''}"
    >
      <table class="w-full text-left text-xs">
        <thead class="sticky top-0 z-10 bg-slate-900 text-[var(--viz-ink-3)]">
          <tr>
            {#each columns as column (column.key)}
              <th
                class="px-3 py-2 font-medium {column.numeric ? 'text-right' : ''}"
                aria-sort={active?.key === column.key
                  ? active.dir === 'asc'
                    ? 'ascending'
                    : 'descending'
                  : 'none'}
              >
                <button
                  type="button"
                  class="inline-flex items-center gap-1 hover:text-slate-100 {column.numeric
                    ? 'flex-row-reverse'
                    : ''}"
                  onclick={() => toggle(column.key)}
                >
                  {column.label}
                  {#if active?.key === column.key}
                    <Icon name={active.dir === 'asc' ? 'chevronUp' : 'chevronDown'} size={12} />
                  {/if}
                </button>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="text-[var(--viz-ink)]">
          {#each sorted as row (id(row))}
            {@const expanded = open === id(row)}
            <tr
              class="border-t border-slate-800/70 {detail ? 'cursor-pointer hover:bg-slate-800/30' : ''}"
              onclick={() => detail && (open = expanded ? null : id(row))}
            >
              {#each columns as column (column.key)}
                {@const text = column.text ? column.text(row) : String(column.value(row) ?? '–')}
                <td
                  class="px-3 py-1.5 {column.numeric ? 'text-right tabular-nums' : 'text-[var(--viz-ink-2)]'} {column.wide
                    ? 'max-w-64 truncate'
                    : 'whitespace-nowrap'}"
                  title={column.wide ? text : undefined}
                >
                  {text}
                </td>
              {/each}
            </tr>
            {#if detail && expanded}
              <tr class="border-t border-slate-800/70 bg-slate-950/60">
                <td colspan={columns.length} class="px-3 py-2">{@render detail(row)}</td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
