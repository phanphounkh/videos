<script lang="ts">
  /**
   * One person, in full: manage the account (status, admin rights, plan, monthly limits,
   * deletion) and see everything telemetry knows about them (AI usage, sessions, what they
   * do most, their latest errors).
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import BarList from '$lib/components/telemetry/BarList.svelte';
  import EventList from '$lib/components/telemetry/EventList.svelte';
  import StatTile from '$lib/components/telemetry/StatTile.svelte';
  import { ago, compact, duration, usd } from '$lib/components/telemetry/format';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { users, type UserDetail, type UserPatch } from '$lib/api/users';
  import {
    RANGES,
    admin,
    emptyFilters,
    shortId,
    type LlmUsage,
    type Range,
    type UserDetail as TelemetryDetail
  } from '$lib/telemetry/admin';
  import { auth } from '$lib/stores/auth.svelte';

  const id = $derived(page.params.id ?? '');
  const isSelf = $derived(auth.user?.id === id);

  let detail = $state<UserDetail | null>(null);
  let seen = $state<TelemetryDetail | null>(null);
  let llm = $state<LlmUsage | null>(null);
  let range = $state<Range>('30d');
  let error = $state<unknown>(null);
  let notice = $state('');
  let busy = $state(false);

  // Editable copies of the plan and limits. Empty text means unlimited.
  let plan = $state('free');
  let limits = $state({ ai_calls: '', tokens: '', exports: '', storage: '' });
  let confirmEmail = $state('');
  let deleting = $state(false);

  const user = $derived(detail?.user ?? null);

  function fill(u: NonNullable<typeof user>) {
    plan = u.plan;
    limits = {
      ai_calls: u.limit_ai_calls?.toString() ?? '',
      tokens: u.limit_tokens?.toString() ?? '',
      exports: u.limit_exports?.toString() ?? '',
      storage: u.limit_storage_mb?.toString() ?? ''
    };
  }

  async function load() {
    try {
      detail = await users.get(id);
      fill(detail.user);
      error = null;
    } catch (e) {
      error = e;
    }
  }

  async function loadTelemetry() {
    const f = { ...emptyFilters(), range, user: id };
    // A person with no events yet is normal (404): the panels just stay empty.
    seen = await admin.user(id, f).catch(() => null);
    llm = await admin.llm(f).catch(() => null);
  }

  $effect(() => {
    if (id) void load();
  });
  $effect(() => {
    void range;
    if (id) void loadTelemetry();
  });

  async function save(patch: UserPatch, message: string) {
    busy = true;
    notice = '';
    try {
      const updated = await users.update(id, patch);
      if (detail) detail = { ...detail, user: updated };
      fill(updated);
      error = null;
      notice = message;
    } catch (e) {
      error = e;
      if (detail) fill(detail.user);
    } finally {
      busy = false;
    }
  }

  const parse = (text: string): number | null => (text.trim() === '' ? null : Math.max(0, Math.floor(Number(text))));
  const limitsInvalid = $derived(
    Object.values(limits).some((v) => v.trim() !== '' && !Number.isFinite(Number(v)))
  );

  async function resetUsage() {
    busy = true;
    try {
      await users.resetUsage(id);
      await load();
      notice = 'This month’s usage was reset.';
    } catch (e) {
      error = e;
    } finally {
      busy = false;
    }
  }

  async function remove() {
    busy = true;
    try {
      await users.remove(id);
      await goto('/users');
    } catch (e) {
      error = e;
      busy = false;
    }
  }

  const used = (key: 'ai_calls' | 'tokens' | 'exports') => user?.used[key] ?? 0;
  const cap = (key: 'ai_calls' | 'tokens' | 'exports') =>
    ({ ai_calls: user?.limit_ai_calls, tokens: user?.limit_tokens, exports: user?.limit_exports })[key] ?? null;
  const quotaState = (key: 'ai_calls' | 'tokens' | 'exports') => {
    const c = cap(key);
    if (c === null) return { tone: 'good' as const, label: 'No limit' };
    return used(key) >= c
      ? { tone: 'critical' as const, label: 'Limit reached' }
      : used(key) >= c * 0.8
        ? { tone: 'warning' as const, label: 'Nearly there' }
        : { tone: 'good' as const, label: 'Within limit' };
  };
</script>

<svelte:head><title>{user?.email ?? 'User'} · Sorya Admin</title></svelte:head>

<div class="flex flex-wrap items-center gap-2 text-sm">
  <a href="/users" class="text-sun-300 hover:text-sun-200">← Users</a>
  <span class="text-slate-500">/</span>
  <span class="font-semibold text-slate-100">{user?.email ?? shortId(id)}</span>
  {#if isSelf}<span class="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">you</span>{/if}
</div>

<ErrorBanner {error} />
{#if notice}
  <p class="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-200" role="status">{notice}</p>
{/if}

{#if user}
  <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <StatTile label="Status" value={user.is_active ? 'Active' : 'Disabled'} sub={`${user.is_admin ? 'Administrator · ' : ''}${user.plan} plan`} state={user.is_active ? { tone: 'good', label: 'Can sign in' } : { tone: 'critical', label: 'Blocked' }} />
    <StatTile label="Projects" value={compact(user.project_count)} sub={`Joined ${new Date(user.created_at).toLocaleDateString()}`} />
    <StatTile label="Last login" value={user.last_login_at ? ago(user.last_login_at) : 'Never'} sub={user.full_name ?? undefined} />
    <StatTile label="Telemetry events" value={seen ? compact(seen.user.events) : '–'} sub={seen ? `${seen.user.sessions} sessions in ${range}` : 'None recorded'} />
  </section>

  <div class="grid gap-4 xl:grid-cols-2">
    <!-- usage against limits -->
    <section class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
      <h2 class="text-sm font-semibold text-[var(--viz-ink)]">This month’s usage</h2>
      <div class="mt-3 grid gap-3 sm:grid-cols-3">
        <StatTile label="AI generations" value={compact(used('ai_calls'))} sub={cap('ai_calls') === null ? 'Unlimited' : `of ${compact(cap('ai_calls'))}`} state={quotaState('ai_calls')} />
        <StatTile label="AI tokens" value={compact(used('tokens'))} sub={cap('tokens') === null ? 'Unlimited' : `of ${compact(cap('tokens'))}`} state={quotaState('tokens')} />
        <StatTile label="Exports" value={compact(used('exports'))} sub={cap('exports') === null ? 'Unlimited' : `of ${compact(cap('exports'))}`} state={quotaState('exports')} />
      </div>
      <div class="mt-3"><Button variant="secondary" size="sm" disabled={busy} onclick={resetUsage}>Reset this month’s usage</Button></div>
    </section>

    <!-- plan and limits -->
    <form
      class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4"
      onsubmit={(e) => {
        e.preventDefault();
        void save(
          {
            plan: plan.trim().toLowerCase(),
            limit_ai_calls: parse(limits.ai_calls),
            limit_tokens: parse(limits.tokens),
            limit_exports: parse(limits.exports),
            limit_storage_mb: parse(limits.storage)
          },
          'Plan and limits saved.'
        );
      }}
    >
      <h2 class="text-sm font-semibold text-[var(--viz-ink)]">Plan and monthly limits</h2>
      <p class="mt-0.5 text-xs text-[var(--viz-ink-3)]">Leave a limit empty for unlimited. Limits are enforced as soon as you save.</p>
      <div class="mt-3 grid gap-3 sm:grid-cols-5">
        <label class="flex flex-col gap-1 text-xs text-slate-300">Plan
          <input list="plans" bind:value={plan} pattern="[a-z0-9_-]+" required class="h-9 rounded-lg border border-slate-700 bg-slate-950 px-2.5 text-sm text-slate-100 focus:border-sun-400 focus:outline-none" />
          <datalist id="plans"><option value="free"></option><option value="pro"></option><option value="team"></option></datalist>
        </label>
        {#each [['ai_calls', 'AI generations'], ['tokens', 'AI tokens'], ['exports', 'Exports']] as [key, label] (key)}
          <label class="flex flex-col gap-1 text-xs text-slate-300">{label}
            <input inputmode="numeric" placeholder={key === 'storage' ? 'Plan default' : 'Unlimited'} bind:value={limits[key as keyof typeof limits]} class="h-9 rounded-lg border border-slate-700 bg-slate-950 px-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sun-400 focus:outline-none" />
          </label>
        {/each}
      </div>
      <div class="mt-3"><Button type="submit" size="sm" disabled={busy || limitsInvalid}>Save plan and limits</Button></div>
    </form>
  </div>

  <!-- account controls -->
  <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
    <h2 class="text-sm font-semibold text-[var(--viz-ink)]">Account</h2>
    <div class="mt-3 flex flex-wrap items-center gap-2">
      {#if user.is_active}
        <Button variant="secondary" size="sm" disabled={busy || isSelf} title={isSelf ? 'You cannot disable yourself' : 'Blocks sign-in and API access; keeps all data'} onclick={() => save({ is_active: false }, 'Account disabled. They are signed out of everything.')}>Disable account</Button>
      {:else}
        <Button size="sm" disabled={busy} onclick={() => save({ is_active: true }, 'Account enabled.')}>Enable account</Button>
      {/if}
      {#if user.is_admin}
        <Button variant="secondary" size="sm" disabled={busy || isSelf} title={isSelf ? 'You cannot demote yourself' : ''} onclick={() => save({ is_admin: false }, 'Administrator rights removed.')}>Remove admin rights</Button>
      {:else}
        <Button variant="secondary" size="sm" disabled={busy} onclick={() => save({ is_admin: true }, 'They are now an administrator.')}>Make administrator</Button>
      {/if}
      <a href="/events?user={id}&range=30d" class="text-xs text-sun-300 hover:text-sun-200">All events →</a>
      <a href="/sessions?user={id}" class="text-xs text-sun-300 hover:text-sun-200">Sessions →</a>
    </div>

    <div class="mt-4 border-t border-[var(--viz-grid)] pt-3">
      {#if !deleting}
        <Button variant="danger" size="sm" disabled={busy || isSelf} title={isSelf ? 'You cannot delete yourself here' : ''} onclick={() => (deleting = true)}>Delete account…</Button>
      {:else}
        <p class="text-xs text-red-200">This permanently deletes the account and all {user.project_count} of their projects. Type <strong>{user.email}</strong> to confirm.</p>
        <div class="mt-2 flex flex-wrap items-center gap-2">
          <input bind:value={confirmEmail} aria-label="Type the email to confirm" class="h-9 w-72 rounded-lg border border-red-500/40 bg-slate-950 px-2.5 text-sm text-slate-100 focus:outline-none" />
          <Button variant="danger" size="sm" disabled={busy || confirmEmail !== user.email} onclick={remove}>Delete permanently</Button>
          <Button variant="ghost" size="sm" onclick={() => ((deleting = false), (confirmEmail = ''))}>Cancel</Button>
        </div>
      {/if}
    </div>
  </section>

  <!-- what telemetry knows -->
  <div class="flex flex-wrap items-center gap-3">
    <h2 class="text-lg font-semibold text-slate-50">Activity</h2>
    <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Time range">
      {#each RANGES as r (r.value)}
        <button type="button" role="radio" aria-checked={range === r.value} title={r.hint} class="rounded-md px-2.5 py-1 text-xs font-medium transition {range === r.value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => (range = r.value)}>{r.label}</button>
      {/each}
    </div>
  </div>

  {#if llm}
    <section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatTile label="AI calls" value={compact(llm.totals.calls)} sub={llm.totals.failures ? `${llm.totals.failures} failed` : 'None failed'} />
      <StatTile label="Tokens" value={compact(llm.totals.tokens)} sub={`${compact(llm.totals.prompt_tokens)} in · ${compact(llm.totals.completion_tokens)} out`} />
      <StatTile label="Estimated cost" value={usd(llm.totals.cost_usd)} sub={llm.totals.cost_usd === null ? 'No prices set' : undefined} />
      <StatTile label="Average call" value={duration(llm.totals.avg_ms)} sub={`p95 ${duration(llm.totals.p95_ms)}`} />
    </section>
  {/if}

  {#if seen}
    <div class="grid gap-3 lg:grid-cols-2">
      <BarList title="What they do most" rows={seen.top_events.map((t) => ({ label: t.name, value: t.count }))} />
      <section class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
        <h3 class="mb-3 text-sm font-semibold text-[var(--viz-ink)]">Recent sessions</h3>
        <ul class="divide-y divide-[var(--viz-grid)] text-xs">
          {#each seen.sessions.slice(0, 8) as s (s.session_id)}
            <li>
              <a href="/sessions/{s.session_id}" class="flex items-center gap-3 rounded px-1.5 py-1.5 hover:bg-slate-800/40">
                <span class="w-20 shrink-0 text-[var(--viz-ink-2)]">{ago(s.last_seen)}</span>
                <span class="flex-1 text-[var(--viz-ink)]">{s.pages} pages · {compact(s.events)} events</span>
                {#if s.errors}<span style="color:var(--status-critical)">{s.errors} errors</span>{/if}
                <span class="text-[var(--viz-ink-3)]">{shortId(s.session_id)}</span>
              </a>
            </li>
          {/each}
        </ul>
      </section>
    </div>
    <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)]">
      <header class="border-b border-[var(--viz-grid)] px-4 py-2.5"><h3 class="text-sm font-semibold text-[var(--viz-ink)]">Recent errors</h3></header>
      <EventList events={seen.errors} emptyText="No errors for this person in this range." />
    </section>
  {:else}
    <p class="rounded-xl border border-slate-800 bg-[var(--viz-surface)] px-4 py-8 text-center text-sm text-[var(--viz-ink-3)]">No telemetry events for this person in the last {range}.</p>
  {/if}

  {#if detail && detail.recent_projects.length}
    <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
      <h3 class="mb-2 text-sm font-semibold text-[var(--viz-ink)]">Recent projects</h3>
      <ul class="divide-y divide-[var(--viz-grid)] text-xs">
        {#each detail.recent_projects as p (p.id)}
          <li class="flex items-center gap-3 py-1.5">
            <span class="flex-1 truncate text-[var(--viz-ink)]">{p.title}</span>
            <span class="text-[var(--viz-ink-2)]">{p.status}</span>
            <span class="w-20 text-right text-[var(--viz-ink-3)]">{ago(p.created_at)}</span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}
{:else if !error}
  <p class="py-16 text-center text-sm text-slate-400">Loading…</p>
{/if}
