<script lang="ts">
  /** Every account: who, plan, what they have used this month, and how to open them. */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import StatTile from '$lib/components/telemetry/StatTile.svelte';
  import { ago, compact } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import { users, type AdminUser, type Stats } from '$lib/api/users';
  import { auth } from '$lib/stores/auth.svelte';

  const PAGE = 50;
  const STATUS = [
    ['all', 'Everyone'],
    ['active', 'Active'],
    ['disabled', 'Disabled'],
    ['admin', 'Admins']
  ] as const;

  const q = $derived(page.url.searchParams.get('q') ?? '');
  const status = $derived(page.url.searchParams.get('status') ?? 'all');
  const offset = $derived(Number(page.url.searchParams.get('offset') ?? 0));

  let rows = $state<AdminUser[]>([]);
  let total = $state(0);
  let stats = $state<Stats | null>(null);
  let search = $state('');
  let loading = $state(false);
  let error = $state<unknown>(null);

  // Bulk selection. Your own account is never selectable.
  let selected = $state(new Set<string>());
  let confirming = $state(false);
  let typed = $state('');
  let busy = $state(false);
  let notice = $state('');
  const selectable = $derived(rows.filter((u) => u.id !== auth.user?.id));
  const allSelected = $derived(selectable.length > 0 && selectable.every((u) => selected.has(u.id)));
  function toggleAll() {
    selected = allSelected ? new Set() : new Set(selectable.map((u) => u.id));
  }
  function toggleOne(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selected = next;
  }
  async function deleteSelected() {
    busy = true;
    notice = '';
    try {
      const result = await users.bulkRemove([...selected]);
      notice =
        `Deleted ${result.deleted} ${result.deleted === 1 ? 'account' : 'accounts'}.` +
        (result.skipped.length ? ` Skipped ${result.skipped.length}: ${result.skipped[0].reason}` : '');
      selected = new Set();
      confirming = false;
      typed = '';
      error = null;
      void reload();
    } catch (e) {
      error = e;
    } finally {
      busy = false;
    }
  }

  function go(next: { q?: string; status?: string; offset?: number }) {
    const p = new URLSearchParams();
    const merged = { q, status, offset: 0, ...next };
    if (merged.q) p.set('q', merged.q);
    if (merged.status !== 'all') p.set('status', merged.status);
    if (merged.offset) p.set('offset', String(merged.offset));
    void goto(`/users${p.size ? `?${p}` : ''}`, { replaceState: true, keepFocus: true, noScroll: true });
  }

  let generation = 0;
  function reload() {
    const mine = ++generation;
    loading = true;
    return users
      .list({ q, status, limit: PAGE, offset })
      .then((r) => {
        if (mine !== generation) return;
        rows = r.items;
        total = r.total;
        error = null;
        users.stats().then((st) => (stats = st)).catch(() => {});
      })
      .catch((e) => mine === generation && (error = e))
      .finally(() => mine === generation && (loading = false));
  }
  $effect(() => {
    void page.url.search;
    selected = new Set();
    confirming = false;
    void reload();
  });
  $effect(() => {
    search = q;
  });
  $effect(() => {
    users.stats().then((s) => (stats = s)).catch(() => {});
  });

  const limit = (used: number | undefined, cap: number | null) =>
    `${compact(used ?? 0)}${cap === null ? '' : ` / ${compact(cap)}`}`;
</script>

<svelte:head><title>Users · Sorya Admin</title></svelte:head>

<header>
  <h1 class="text-2xl font-bold tracking-tight text-slate-50">Users</h1>
  <p class="text-sm text-slate-400">Accounts, plans and this month's usage.</p>
</header>

{#if stats}
  <section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <StatTile label="Accounts" value={compact(stats.users)} sub={`${stats.active} active`} />
    <StatTile label="New this week" value={compact(stats.new_7d)} />
    <StatTile label="Admins" value={compact(stats.admins)} />
    <StatTile label="Projects" value={compact(stats.projects)} />
  </section>
{/if}

<div class="flex flex-wrap items-center gap-2">
  <form
    class="min-w-52 flex-1 sm:max-w-sm"
    onsubmit={(e) => {
      e.preventDefault();
      go({ q: search.trim() });
    }}
  >
    <input
      type="search"
      bind:value={search}
      placeholder="Search by email or name…"
      aria-label="Search users"
      class="h-8 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 text-xs text-slate-100 placeholder:text-slate-500 focus:border-sun-400 focus:outline-none"
    />
  </form>
  <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Status">
    {#each STATUS as [value, label] (value)}
      <button
        type="button"
        role="radio"
        aria-checked={status === value}
        class="rounded-md px-2.5 py-1 text-xs font-medium transition {status === value
          ? 'bg-slate-700 text-slate-50'
          : 'text-slate-400 hover:text-slate-200'}"
        onclick={() => go({ status: value })}>{label}</button
      >
    {/each}
  </div>
  <span class="text-xs text-slate-400">{total} {total === 1 ? 'person' : 'people'}</span>
</div>

<ErrorBanner {error} />
{#if notice}
  <p class="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-200" role="status">{notice}</p>
{/if}

{#if selected.size}
  <div class="flex flex-wrap items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm">
    <span class="font-medium text-slate-100">{selected.size} selected</span>
    {#if !confirming}
      <Button variant="danger" size="sm" onclick={() => (confirming = true)}>Delete selected…</Button>
      <Button variant="ghost" size="sm" onclick={() => (selected = new Set())}>Clear</Button>
    {:else}
      <span class="text-xs text-red-200">Permanently deletes these accounts and all their projects. Type <strong>DELETE</strong> to confirm.</span>
      <input bind:value={typed} aria-label="Type DELETE to confirm" class="h-8 w-32 rounded-lg border border-red-500/40 bg-slate-950 px-2.5 text-sm text-slate-100 focus:outline-none" />
      <Button variant="danger" size="sm" disabled={busy || typed !== 'DELETE'} onclick={deleteSelected}>Delete {selected.size}</Button>
      <Button variant="ghost" size="sm" onclick={() => ((confirming = false), (typed = ''))}>Cancel</Button>
    {/if}
  </div>
{/if}

<section class="overflow-x-auto rounded-xl border border-slate-800 bg-[var(--viz-surface)]">
  <table class="w-full min-w-[860px] border-collapse text-left text-xs transition-opacity {loading && rows.length ? 'opacity-60' : ''}">
    <thead class="text-[var(--viz-ink-3)]">
      <tr class="border-b border-[var(--viz-grid)]">
        <th class="w-10 px-4 py-2"><input type="checkbox" aria-label="Select everyone on this page" checked={allSelected} disabled={!selectable.length} onchange={toggleAll} /></th>
        <th class="px-3 py-2 font-medium">Person</th>
        <th class="px-3 py-2 font-medium">Status</th>
        <th class="px-3 py-2 font-medium">Plan</th>
        <th class="px-3 py-2 text-right font-medium">Projects</th>
        <th class="px-3 py-2 text-right font-medium">AI calls</th>
        <th class="px-3 py-2 text-right font-medium">Exports</th>
        <th class="px-3 py-2 font-medium">Last login</th>
        <th class="px-3 py-2 font-medium">Joined</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as u (u.id)}
        <tr class="border-b border-[var(--viz-grid)] transition hover:bg-slate-800/40">
          <td class="px-4 py-2">
            <input type="checkbox" aria-label="Select {u.email}" checked={selected.has(u.id)} disabled={u.id === auth.user?.id} title={u.id === auth.user?.id ? 'This is you' : ''} onchange={() => toggleOne(u.id)} />
          </td>
          <td class="px-3 py-2">
            <a href="/users/{u.id}" class="font-medium text-[var(--viz-ink)] hover:text-sun-300">{u.email}</a>
            {#if u.full_name}<p class="text-[var(--viz-ink-3)]">{u.full_name}</p>{/if}
          </td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center gap-1.5 text-[var(--viz-ink-2)]">
              <span class="h-2 w-2 rounded-full" style="background:{u.is_active ? 'var(--status-good)' : 'var(--status-critical)'}"></span>
              {u.is_active ? 'Active' : 'Disabled'}{u.is_admin ? ' · admin' : ''}
            </span>
          </td>
          <td class="px-3 py-2 text-[var(--viz-ink-2)]">{u.plan}</td>
          <td class="px-3 py-2 text-right text-[var(--viz-ink-2)] tabular-nums">{u.project_count}</td>
          <td class="px-3 py-2 text-right text-[var(--viz-ink-2)] tabular-nums">{limit(u.used.ai_calls, u.limit_ai_calls)}</td>
          <td class="px-3 py-2 text-right text-[var(--viz-ink-2)] tabular-nums">{limit(u.used.exports, u.limit_exports)}</td>
          <td class="px-3 py-2 text-[var(--viz-ink-2)]">{u.last_login_at ? ago(u.last_login_at) : 'never'}</td>
          <td class="px-3 py-2 text-[var(--viz-ink-2)]">{new Date(u.created_at).toLocaleDateString()}</td>
        </tr>
      {:else}
        <tr><td colspan="9" class="py-12 text-center text-sm text-[var(--viz-ink-3)]">{loading ? 'Loading…' : 'No one matches.'}</td></tr>
      {/each}
    </tbody>
  </table>
  {#if total > PAGE}
    <div class="flex items-center justify-between border-t border-[var(--viz-grid)] px-4 py-2 text-xs text-slate-400">
      <span>{offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
      <span class="flex gap-2">
        <button type="button" class="rounded border border-slate-700 px-2 py-1 disabled:opacity-40" disabled={offset === 0} onclick={() => go({ offset: Math.max(0, offset - PAGE) })}>Previous</button>
        <button type="button" class="rounded border border-slate-700 px-2 py-1 disabled:opacity-40" disabled={offset + PAGE >= total} onclick={() => go({ offset: offset + PAGE })}>Next</button>
      </span>
    </div>
  {/if}
</section>
