<script lang="ts">
  /**
   * Settings > Avatar: your favourite host on the left (alive, big), with the
   * style-matching switch, and the full picker on the right for choosing, uploading and
   * managing hosts.
   */
  import { api } from '$lib/api';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import AnimatedAvatar from './AnimatedAvatar.svelte';
  import AvatarImage from './AvatarImage.svelte';
  import AvatarPicker from './AvatarPicker.svelte';
  import { builtinHosts, hostInfo, hostPrefs, loadHosts, setHostPrefs } from './hosts.svelte';

  let note = $state(false);
  let error = $state<unknown>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const prefs = $derived(hostPrefs());
  const favourite = $derived(hostInfo(prefs.default));
  const detail = $derived(builtinHosts().find((a) => a.id === prefs.default));

  $effect(() => {
    void loadHosts();
    return () => clearTimeout(timer);
  });

  async function save(next: { default: string | null; auto: boolean }) {
    const before = hostPrefs();
    setHostPrefs(next); // shown at once; put back if the server says no
    error = null;
    try {
      setHostPrefs(await api.saveAvatarPreferences(next));
      note = true;
      clearTimeout(timer);
      timer = setTimeout(() => (note = false), 1800);
    } catch (e) {
      setHostPrefs(before);
      error = e;
    }
  }
</script>

<div class="mb-4 flex items-center justify-between">
  <div>
    <h2 class="text-lg font-semibold text-slate-50">{t('avatars.tab')}</h2>
    <p class="mt-0.5 text-sm text-slate-400">{t('avatars.settings.favouriteHint')}</p>
  </div>
  {#if note}<span class="inline-flex items-center gap-1 text-xs text-emerald-300" role="status"><Icon name="check" size={13} /> {t('common.saved')}</span>{/if}
</div>
<ErrorBanner {error} />

<div class="grid gap-8 xl:grid-cols-[19rem_minmax(0,1fr)] xl:items-start">
  <!-- your favourite, large and alive -->
  <aside class="flex flex-col gap-4 xl:sticky xl:top-4">
    <div class="overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-b from-sun-500/20 via-slate-900 to-slate-950">
      <div class="relative aspect-[4/5] w-full">
        {#if favourite}
          <AvatarImage src={favourite.image} name={favourite.name} fit={favourite.custom ? 'cover' : 'contain'} class="absolute inset-0 h-full w-full bg-transparent" />
          {#key favourite.id}<AnimatedAvatar id={favourite.id} active />{/key}
        {:else}
          <div class="absolute inset-0 grid place-items-center text-sun-300"><Icon name="sparkles" size={44} /></div>
        {/if}
      </div>
      <div class="border-t border-slate-800 bg-slate-950/60 px-4 py-3.5">
        <p class="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide text-sun-300 uppercase">★ {t('avatars.favourite')}</p>
        <p class="mt-0.5 text-lg font-semibold text-slate-50" data-private>{favourite?.name ?? t('avatars.noFavourite')}</p>
        <p class="mt-0.5 text-xs text-slate-400">
          {#if detail}{t(`avatars.style.${detail.style}`)} · {t(`avatars.gender.${detail.gender}`)} · {t(`avatars.age.${detail.age}`)}{:else if favourite}{t('avatars.yours')}{:else}{t('avatars.noFavouriteHint')}{/if}
        </p>
      </div>
    </div>

    <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <input class="mt-1" type="checkbox" role="switch" aria-label={t('avatars.settings.auto')} checked={prefs.auto} onchange={(e) => save({ default: prefs.default, auto: e.currentTarget.checked })} />
      <span>
        <span class="block text-sm font-medium text-slate-100">{t('avatars.settings.auto')}</span>
        <span class="mt-1 block text-xs leading-relaxed text-slate-500">{t('avatars.settings.autoHint')}</span>
      </span>
    </label>
  </aside>

  <!-- everything to choose from -->
  <div class="min-w-0">
    <AvatarPicker
      size="lg"
      allowAuto
      autoLabel={t('avatars.noFavourite')}
      autoHint={t('avatars.noFavouriteHint')}
      value={prefs.default}
      onselect={(id) => save({ default: id, auto: prefs.auto })}
    />
  </div>
</div>
