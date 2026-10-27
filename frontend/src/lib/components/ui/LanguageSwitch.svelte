<script lang="ts">
  /** English | ខ្មែរ: switches the interface language everywhere, immediately. */
  import { LOCALES, i18n, setLocale, t } from '$lib/i18n/index.svelte';

  let { class: extra = '' }: { class?: string } = $props();
</script>

<div
  class="inline-flex rounded-[0.7rem] border border-slate-700 bg-slate-900 p-0.5 {extra}"
  role="radiogroup"
  aria-label={t('lang.switch')}
>
  {#each LOCALES as l (l.value)}
    <button
      type="button"
      role="radio"
      aria-checked={i18n.locale === l.value}
      title={l.name}
      class="rounded-[0.55rem] px-3 py-1 text-sm font-medium whitespace-nowrap transition {i18n.locale ===
      l.value
        ? 'bg-slate-700 text-slate-50 shadow-sm'
        : 'text-slate-400 hover:text-slate-200'}"
      onclick={() => setLocale(l.value)}
    >
      {l.label}
    </button>
  {/each}
</div>
