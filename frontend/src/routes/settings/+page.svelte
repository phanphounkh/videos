<script lang="ts">
  /**
   * Account settings, laid out like ChatGPT's or Canva's: a short menu on the left, one
   * section at a time on the right, each setting a row with its explanation beside it.
   */
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import { setToken } from '$lib/api/client';
  import AvatarSettings from '$lib/components/avatars/AvatarSettings.svelte';
  import Avatar from '$lib/components/ui/Avatar.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import LanguageSwitch from '$lib/components/ui/LanguageSwitch.svelte';
  import Segmented from '$lib/components/ui/Segmented.svelte';
  import { page } from '$app/state';
  import { bytes } from '$lib/format';
  import { i18n, t } from '$lib/i18n/index.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { loadPreferences, savePreferences, type Preferences } from '$lib/stores/preferences';
  import type { AccountUsage, PurposeTemplate, Storage } from '$lib/types/api';

  const TABS: { id: string; label: string; icon: IconName }[] = $derived([
    { id: 'profile', label: t('settings.tab.profile'), icon: 'user' },
    { id: 'preferences', label: t('settings.tab.preferences'), icon: 'sparkles' },
    { id: 'avatar', label: t('avatars.tab'), icon: 'smile' },
    { id: 'security', label: t('settings.tab.security'), icon: 'lock' },
    { id: 'usage', label: t('settings.tab.usage'), icon: 'clock' },
    { id: 'account', label: t('settings.tab.account'), icon: 'trash' }
  ]);
  /** A word from the dictionary, or the server's own text when there is no entry for it. */
  const word = (key: string, fallback: string) => {
    const s = t(key);
    return s === key ? fallback : s;
  };
  // `/settings?tab=usage` opens straight on a tab (the sidebar's storage meter links there).
  const startTab = page.url.searchParams.get('tab');
  let tab = $state(['profile', 'preferences', 'avatar', 'security', 'usage', 'account'].includes(startTab ?? '') ? startTab! : 'profile');

  // A link to another tab while already on Settings (the profile menu's Usage) switches it.
  $effect(() => {
    const wanted = page.url.searchParams.get('tab');
    if (wanted && ['profile', 'preferences', 'avatar', 'security', 'usage', 'account'].includes(wanted)) tab = wanted;
  });

  // ---- usage: loaded when the tab is first opened
  let usage = $state<AccountUsage | null>(null);
  let storage = $state<Storage | null>(null);
  let usageError = $state<unknown>(null);
  $effect(() => {
    if (tab !== 'usage' || usage) return;
    api.myUsage().then((u) => (usage = u)).catch((e) => (usageError = e));
    api.storage().then((x) => (storage = x)).catch(() => {});
  });
  const METERS = $derived([
    { key: 'ai_calls', label: t('usage.aiCalls'), hint: t('usage.aiCallsHint') },
    { key: 'tokens', label: t('usage.tokens'), hint: t('usage.tokensHint') },
    { key: 'exports', label: t('usage.exports'), hint: t('usage.exportsHint') }
  ] as const);
  // Some browsers ship without Khmer date data and quietly answer in English, so the
  // twelve month names are spelled out for Khmer.
  const KM_MONTHS = ['មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា', 'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ'];
  const month = $derived.by(() => {
    if (!usage) return '';
    const d = new Date(`${usage.period}-01T00:00:00`);
    if (i18n.locale === 'km') return `${KM_MONTHS[d.getMonth()]} ${d.getFullYear()}`;
    return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  });
  const share = (used: number, cap: number | null) => (cap === null || cap === 0 ? 0 : Math.min(100, (used / cap) * 100));
  const fmt = (n: number) => n.toLocaleString();

  $effect(() => {
    if (auth.ready && !auth.user) void goto('/login', { replaceState: true });
  });

  const name = $derived(auth.user?.full_name?.trim() || auth.user?.email.split('@')[0] || '');

  // ---- profile picture
  let photoInput = $state<HTMLInputElement>();
  let photoBusy = $state(false);
  let photoError = $state<unknown>(null);
  async function pickPhoto(file: File) {
    photoError = null;
    if (!file.type.startsWith('image/')) {
      photoError = new Error(t('profile.notImage'));
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      photoError = new Error(t('profile.tooBig'));
      return;
    }
    photoBusy = true;
    try {
      auth.user = await api.uploadAvatar(file);
    } catch (err) {
      photoError = err;
    } finally {
      photoBusy = false;
    }
  }
  async function removePhoto() {
    photoBusy = true;
    photoError = null;
    try {
      auth.user = await api.removeAvatar();
    } catch (err) {
      photoError = err;
    } finally {
      photoBusy = false;
    }
  }

  // ---- profile
  let fullName = $state('');
  let profileError = $state<unknown>(null);
  let profileNote = $state('');
  $effect(() => {
    fullName = auth.user?.full_name ?? '';
  });
  const nameChanged = $derived(fullName.trim() !== (auth.user?.full_name ?? ''));
  async function saveProfile(e: SubmitEvent) {
    e.preventDefault();
    profileNote = '';
    try {
      auth.user = await api.updateProfile({ full_name: fullName.trim() || null });
      profileError = null;
      profileNote = 'saved';
    } catch (err) {
      profileError = err;
    }
  }

  // ---- preferences: saved the moment they change, like a toggle should be
  let prefs = $state<Preferences>({ language: 'en', purpose: 'story' });
  let purposes = $state<PurposeTemplate[]>([]);
  let prefsNote = $state('');
  $effect(() => {
    prefs = loadPreferences();
    api
      .purposes()
      .then((p) => (purposes = p))
      .catch(() => {});
  });
  function savePrefs() {
    savePreferences($state.snapshot(prefs));
    prefsNote = 'saved';
    setTimeout(() => (prefsNote = ''), 1800);
  }

  // ---- password
  let current = $state('');
  let next = $state('');
  let again = $state('');
  let passwordError = $state<unknown>(null);
  let passwordNote = $state('');
  const mismatch = $derived(again.length > 0 && next !== again);
  async function changePassword(e: SubmitEvent) {
    e.preventDefault();
    passwordNote = '';
    try {
      await api.changePassword({ current_password: current, new_password: next });
      current = next = again = '';
      passwordError = null;
      passwordNote = 'changed';
    } catch (err) {
      passwordError = err;
    }
  }

  // ---- delete
  let deleting = $state(false);
  let deletePassword = $state('');
  let deleteError = $state<unknown>(null);
  async function deleteAccount() {
    try {
      await api.deleteAccount({ password: deletePassword });
      setToken(null);
      auth.user = null;
      await goto('/login');
    } catch (err) {
      deleteError = err;
    }
  }

  const input =
    'h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sun-400 focus:outline-none';
</script>

<svelte:head><title>{t('settings.title')} · Sorya</title></svelte:head>

{#snippet row(label: string, hint: string | undefined, control: import('svelte').Snippet)}
  <div class="grid gap-3 border-b border-slate-800 px-5 py-4 last:border-0 sm:grid-cols-[1fr_minmax(0,22rem)] sm:items-center sm:gap-8 sm:px-6">
    <div>
      <p class="text-sm font-medium text-slate-100">{label}</p>
      {#if hint}<p class="mt-0.5 text-xs text-slate-500">{hint}</p>{/if}
    </div>
    <div>{@render control()}</div>
  </div>
{/snippet}

{#snippet card(title: string, subtitle: string | undefined, icon: IconName, body: import('svelte').Snippet, tone: 'default' | 'danger' = 'default')}
  <section class="overflow-hidden rounded-2xl border bg-slate-900 {tone === 'danger' ? 'border-red-500/30' : 'border-slate-800'}">
    <header class="flex items-center gap-3 border-b border-slate-800 px-5 py-4 sm:px-6">
      <span class="grid size-9 shrink-0 place-items-center rounded-xl {tone === 'danger' ? 'bg-red-500/15 text-red-300' : 'bg-[image:var(--sun-gradient)] text-slate-950'}"><Icon name={icon} size={16} /></span>
      <div class="min-w-0">
        <h2 class="text-base font-semibold text-slate-50">{title}</h2>
        {#if subtitle}<p class="truncate text-xs text-slate-400">{subtitle}</p>{/if}
      </div>
    </header>
    {@render body()}
  </section>
{/snippet}

{#snippet stat(label: string, hint: string | undefined, value: string, pct: number | null, warnAt: number)}
  <div class="rounded-2xl border border-slate-800 bg-slate-900 p-5 transition hover:border-slate-700">
    <p class="text-xs font-medium tracking-wide text-slate-400 uppercase">{label}</p>
    <p class="mt-2 text-2xl font-bold text-slate-50 tabular-nums">{value}</p>
    {#if pct !== null}
      <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-800" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin="0" aria-valuemax="100" aria-label={label}>
        <div class="h-full rounded-full transition-[width] duration-700 {pct >= 100 ? 'bg-red-400' : pct >= warnAt ? 'bg-amber-400' : 'bg-[image:var(--sun-gradient)]'}" style="width:{Math.max(pct, 1)}%"></div>
      </div>
      {#if pct >= 100}<p class="mt-1.5 text-xs text-red-300">{t('usage.limitReached')}</p>{/if}
    {:else}
      <p class="mt-3 text-xs text-slate-500">{t('usage.noLimit')}</p>
    {/if}
    {#if hint}<p class="mt-2 text-xs text-slate-500">{hint}</p>{/if}
  </div>
{/snippet}

{#if auth.user}
  <main class="mx-auto max-w-[120rem] px-4 py-6 sm:px-6 lg:px-10">
    <h1 class="text-[30px] leading-tight font-bold tracking-tight text-slate-50">{t('settings.title')}</h1>

    <div class="mt-6 grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:items-start xl:grid-cols-[17rem_minmax(0,1fr)]">
      <nav class="flex gap-1 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900 p-2 lg:sticky lg:top-6 lg:flex-col" aria-label={t('settings.sections')}>
        {#each TABS as tb (tb.id)}
          <button
            type="button"
            aria-current={tab === tb.id ? 'page' : undefined}
            class="flex h-10 shrink-0 items-center gap-3 rounded-xl px-3 text-sm font-medium transition {tab === tb.id
              ? 'bg-slate-800 text-slate-50 shadow-pop'
              : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'}"
            onclick={() => (tab = tb.id)}
          >
            <span class="grid size-6 place-items-center rounded-lg {tab === tb.id ? 'bg-[image:var(--sun-gradient)] text-slate-950' : 'bg-slate-800 text-slate-400'}"><Icon name={tb.icon} size={13} /></span>
            {tb.label}
          </button>
        {/each}
      </nav>

      <div class="min-w-0">
        {#if tab === 'profile'}
          <div class="flex flex-col gap-6">
            <section class="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
              <div class="h-24 bg-[image:var(--sun-gradient)] opacity-80 sm:h-28"></div>
              <div class="flex flex-wrap items-end gap-5 px-5 pb-6 sm:px-6">
                <button
                  type="button"
                  class="group relative -mt-12 shrink-0 rounded-full ring-4 ring-slate-900"
                  aria-label={t('profile.change')}
                  disabled={photoBusy}
                  onclick={() => photoInput?.click()}
                >
                  <Avatar user={auth.user} size={96} />
                  <span class="absolute inset-0 grid place-items-center rounded-full bg-black/55 text-xs font-semibold text-white opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">
                    {photoBusy ? t('profile.uploading') : t('profile.change')}
                  </span>
                </button>
                <div class="min-w-0 flex-1 pt-3">
                  <p class="truncate text-xl font-semibold text-slate-50" data-private>{name}</p>
                  <p class="truncate text-sm text-slate-400" data-private>{auth.user.email}</p>
                  <p class="mt-2 text-xs text-slate-500">{t('profile.hint')}</p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                  <Button size="sm" variant="secondary" disabled={photoBusy} onclick={() => photoInput?.click()}>{photoBusy ? t('profile.uploading') : t('profile.upload')}</Button>
                  {#if auth.user.avatar_url}<Button size="sm" variant="ghost" disabled={photoBusy} onclick={removePhoto}>{t('profile.remove')}</Button>{/if}
                  <button type="button" class="rounded-full bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700" onclick={() => (tab = 'usage')}>{t('settings.planBadge', { plan: word(`settings.plan.${auth.user.plan}`, auth.user.plan.charAt(0).toUpperCase() + auth.user.plan.slice(1)) })}</button>
                </div>
                <input bind:this={photoInput} type="file" accept="image/png,image/jpeg,image/webp" class="hidden" aria-label={t('profile.photo')} onchange={(e) => { const f = e.currentTarget.files?.[0]; e.currentTarget.value = ''; if (f) void pickPhoto(f); }} />
              </div>
              {#if photoError}<div class="px-5 pb-5 sm:px-6"><ErrorBanner error={photoError} /></div>{/if}
            </section>

            {#snippet profileBody()}
              <form onsubmit={saveProfile}>
                {#if profileError}<div class="px-5 pt-4 sm:px-6"><ErrorBanner error={profileError} /></div>{/if}
                {#snippet nameControl()}
                  <input class={input} bind:value={fullName} maxlength="255" placeholder={t('settings.namePlaceholder')} data-private />
                {/snippet}
                {#snippet emailControl()}
                  <input class="{input} opacity-60" value={auth.user?.email} readonly data-private />
                {/snippet}
                {@render row(t('common.name'), t('settings.nameHint'), nameControl)}
                {@render row(t('common.email'), t('settings.emailHint'), emailControl)}
                <div class="flex items-center gap-3 border-t border-slate-800 px-5 py-4 sm:px-6">
                  <Button type="submit" size="sm" disabled={!nameChanged}>{t('settings.saveChanges')}</Button>
                  {#if profileNote}<span class="inline-flex items-center gap-1 text-xs text-emerald-300" role="status"><Icon name="check" size={13} /> {t('common.saved')}</span>{/if}
                </div>
              </form>
            {/snippet}
            {@render card(t('settings.tab.profile'), undefined, 'user', profileBody)}
          </div>
        {:else if tab === 'preferences'}
          <div class="grid gap-6 xl:grid-cols-2 xl:items-start">
            {#snippet interfaceControl()}<LanguageSwitch />{/snippet}
            {#snippet interfaceBody()}
              {@render row(t('lang.interface'), t('lang.interfaceHint'), interfaceControl)}
            {/snippet}
            {@render card(t('lang.interface'), undefined, 'monitor', interfaceBody)}

            {#snippet languageControl()}
              <Segmented
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'km', label: 'ខ្មែរ' }
                ]}
                bind:value={prefs.language}
                label={t('settings.videoLanguageLabel')}
                onchange={savePrefs}
              />
            {/snippet}
            {#snippet purposeControl()}
              <select class={input} bind:value={prefs.purpose} onchange={savePrefs}>
                {#each purposes as p (p.key)}<option value={p.key}>{word(`purpose.${p.key}.label`, p.label)}</option>{/each}
              </select>
            {/snippet}
            {#snippet videoBody()}
              {@render row(t('settings.videoLanguage'), t('settings.videoLanguageHint'), languageControl)}
              {@render row(t('settings.videoPurpose'), t('settings.videoPurposeHint'), purposeControl)}
              <div class="flex items-center justify-between gap-3 border-t border-slate-800 px-5 py-3 sm:px-6">
                <p class="text-xs text-slate-500">{t('settings.prefsFootnote')}</p>
                {#if prefsNote}<span class="inline-flex shrink-0 items-center gap-1 text-xs text-emerald-300" role="status"><Icon name="check" size={13} /> {t('common.saved')}</span>{/if}
              </div>
            {/snippet}
            {@render card(t('settings.tab.preferences'), undefined, 'sparkles', videoBody)}
          </div>
        {:else if tab === 'avatar'}
          <AvatarSettings />
        {:else if tab === 'security'}
          {#snippet securityBody()}
            <form onsubmit={changePassword}>
              {#if passwordError}<div class="px-5 pt-4 sm:px-6"><ErrorBanner error={passwordError} /></div>{/if}
              {#snippet currentControl()}
                <input class={input} type="password" autocomplete="current-password" required bind:value={current} data-private />
              {/snippet}
              {#snippet newControl()}
                <input class={input} type="password" autocomplete="new-password" required minlength="8" maxlength="72" bind:value={next} data-private />
              {/snippet}
              {#snippet againControl()}
                <input class={input} type="password" autocomplete="new-password" required bind:value={again} data-private />
                {#if mismatch}<p class="mt-1 text-xs text-red-300">{t('settings.mismatch')}</p>{/if}
              {/snippet}
              {@render row(t('settings.currentPassword'), undefined, currentControl)}
              {@render row(t('settings.newPassword'), t('settings.newPasswordHint'), newControl)}
              {@render row(t('settings.repeatPassword'), undefined, againControl)}
              <div class="flex items-center gap-3 border-t border-slate-800 px-5 py-4 sm:px-6">
                <Button type="submit" size="sm" disabled={mismatch || next.length < 8 || !current}>{t('settings.changePassword')}</Button>
                {#if passwordNote}<span class="inline-flex items-center gap-1 text-xs text-emerald-300" role="status"><Icon name="check" size={13} /> {t('settings.passwordChanged')}</span>{/if}
              </div>
            </form>
          {/snippet}
          {@render card(t('settings.password'), undefined, 'lock', securityBody)}
        {:else if tab === 'usage'}
          <div class="flex flex-col gap-4">
            <div class="flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 class="text-xl font-semibold text-slate-50">{t('usage.title')}</h2>
                <p class="mt-0.5 text-sm text-slate-400">{usage ? t('usage.monthPlan', { month, plan: word(`settings.plan.${usage.plan}`, usage.plan.charAt(0).toUpperCase() + usage.plan.slice(1)) }) : t('usage.subtitle')}</p>
              </div>
            </div>
            <ErrorBanner error={usageError} />
            {#if usage}
              <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {#each METERS as m (m.key)}
                  {@const used = usage.used[m.key]}
                  {@const cap = usage.limits[m.key]}
                  {@render stat(m.label, m.hint, cap === null ? fmt(used) : t('usage.of', { used: fmt(used), cap: fmt(cap) }), cap === null ? null : share(used, cap), 80)}
                {/each}
                {#if storage}
                  {@render stat(t('shell.storage'), undefined, t('usage.of', { used: bytes(storage.used_bytes), cap: bytes(storage.limit_bytes) }), share(storage.used_bytes, storage.limit_bytes), 90)}
                {:else}
                  {@render stat(t('shell.storage'), undefined, t('common.loading'), null, 90)}
                {/if}
                <div class="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <p class="text-xs font-medium tracking-wide text-slate-400 uppercase">{t('usage.projects')}</p>
                  <p class="mt-2 text-2xl font-bold text-slate-50 tabular-nums">{usage.projects}</p>
                </div>
                <div class="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <p class="text-xs font-medium tracking-wide text-slate-400 uppercase">{t('usage.videosReady')}</p>
                  <p class="mt-2 text-2xl font-bold text-slate-50 tabular-nums">{usage.exports_ready}</p>
                </div>
              </div>
            {:else if !usageError}
              <p class="py-10 text-center text-sm text-slate-400">{t('common.loading')}</p>
            {/if}
          </div>
        {:else}
          {#snippet deleteControl()}
            {#if !deleting}
              <Button variant="danger" size="sm" onclick={() => (deleting = true)}>{t('settings.deleteStart')}</Button>
            {:else}
              <div class="flex flex-col gap-2">
                <ErrorBanner error={deleteError} />
                <input class={input} type="password" placeholder={t('settings.enterPassword')} bind:value={deletePassword} data-private />
                <div class="flex gap-2">
                  <Button variant="danger" size="sm" disabled={!deletePassword} onclick={deleteAccount}>{t('settings.deleteConfirm')}</Button>
                  <Button variant="ghost" size="sm" onclick={() => ((deleting = false), (deletePassword = ''), (deleteError = null))}>{t('common.cancel')}</Button>
                </div>
              </div>
            {/if}
          {/snippet}
          {#snippet accountBody()}
            {@render row(t('settings.deleteAccount'), t('settings.deleteAccountHint'), deleteControl)}
          {/snippet}
          {@render card(t('settings.account'), undefined, 'trash', accountBody, 'danger')}
        {/if}
      </div>
    </div>
  </main>
{/if}
