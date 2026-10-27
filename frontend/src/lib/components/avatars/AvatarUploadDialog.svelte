<script lang="ts">
  import { api } from '$lib/api';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import type { AvatarMode, CustomAvatar } from '$lib/types/api';
  import ModeChoice from './ModeChoice.svelte';

  let { onclose, ondone }: { onclose: () => void; ondone: (created: CustomAvatar) => void } = $props();

  const MAX = 8 * 1024 * 1024;
  let file = $state<File | null>(null);
  let preview = $state('');
  let name = $state(t('avatars.defaultName'));
  let mode = $state<AvatarMode>('mouth');
  let busy = $state(false);
  let error = $state<unknown>(null);
  let over = $state(false);
  let input = $state<HTMLInputElement>();

  $effect(() => () => preview && URL.revokeObjectURL(preview));

  function choose(f: File | undefined | null) {
    if (!f) return;
    error = null;
    if (!f.type.startsWith('image/')) {
      error = new Error(t('avatars.notImage'));
      return;
    }
    if (f.size > MAX) {
      error = new Error(t('avatars.tooBig'));
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    file = f;
    preview = URL.createObjectURL(f);
  }

  async function upload(e: SubmitEvent) {
    e.preventDefault();
    if (!file || busy) return;
    busy = true;
    error = null;
    try {
      ondone(await api.uploadHostAvatar(file, { name: name.trim() || t('avatars.defaultName'), mode }));
    } catch (err) {
      error = err;
      busy = false;
    }
  }
</script>

<Modal title={t('avatars.uploadTitle')} onclose={() => !busy && onclose()}>
  <form class="flex max-h-[75vh] flex-col gap-4 overflow-y-auto" onsubmit={upload}>
    <ErrorBanner {error} />
    <div class="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="shrink-0"
        ondragover={(e) => {
          e.preventDefault();
          over = true;
        }}
        ondragleave={() => (over = false)}
        ondrop={(e) => {
          e.preventDefault();
          over = false;
          choose(e.dataTransfer?.files?.[0]);
        }}
      >
        <button
          type="button"
          class="group relative grid h-40 w-32 place-items-center overflow-hidden rounded-[3.5rem] border-2 border-dashed bg-slate-950 text-slate-400 transition hover:border-sun-400/70 {over
            ? 'border-sun-400 bg-sun-500/10'
            : 'border-slate-600'}"
          aria-label={t('avatars.choosePhoto')}
          onclick={() => input?.click()}
        >
          {#if preview}
            <img src={preview} alt="" class="h-full w-full object-cover" />
            <span class="absolute inset-0 grid place-items-center bg-black/55 text-xs font-semibold text-white opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">{t('profile.change')}</span>
          {:else}
            <span class="flex flex-col items-center gap-1.5 px-3 text-center text-xs">
              <Icon name="upload" size={20} />
              {t('avatars.dropHere')}
            </span>
          {/if}
        </button>
        <input bind:this={input} type="file" accept="image/*" class="hidden" aria-label={t('avatars.choosePhoto')} onchange={(e) => { const f = e.currentTarget.files?.[0]; e.currentTarget.value = ''; choose(f); }} />
      </div>
      <div class="w-full min-w-0 flex-1">
        <label class="text-xs font-medium text-slate-400" for="avatar-name">{t('avatars.name')}</label>
        <input id="avatar-name" class="mt-1 h-10 w-full px-3 text-sm" bind:value={name} maxlength="60" />
        <p class="mt-2 text-xs leading-relaxed text-slate-500">{t('avatars.photoHint')}</p>
      </div>
    </div>
    <div>
      <p class="mb-2 text-xs font-medium text-slate-400">{t('avatars.mode')}</p>
      <ModeChoice bind:value={mode} />
    </div>
    <div class="flex justify-end gap-2 pt-1">
      <Button variant="ghost" disabled={busy} onclick={onclose}>{t('common.cancel')}</Button>
      <Button type="submit" disabled={!file} loading={busy}>{busy ? t('avatars.uploading') : t('avatars.upload')}</Button>
    </div>
  </form>
</Modal>
