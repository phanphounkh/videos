<script lang="ts">
  /** The two ways an uploaded photo can talk: two selectable cards. */
  import { t } from '$lib/i18n/index.svelte';
  import type { AvatarMode } from '$lib/types/api';

  let { value = $bindable() }: { value: AvatarMode } = $props();
  const options: AvatarMode[] = ['mouth', 'subtle'];
</script>

<div class="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label={t('avatars.mode')}>
  {#each options as mode (mode)}
    <button
      type="button"
      role="radio"
      aria-checked={value === mode}
      onclick={() => (value = mode)}
      class="rounded-xl border p-3 text-left transition {value === mode
        ? 'border-sun-400/70 bg-sun-500/10'
        : 'border-slate-700 bg-slate-950 hover:border-slate-600'}"
    >
      <span class="block text-sm font-semibold text-slate-50">{t(`avatars.mode.${mode}`)}</span>
      <span class="mt-0.5 block text-xs leading-relaxed text-slate-400">{t(`avatars.mode.${mode}.hint`)}</span>
    </button>
  {/each}
</div>
