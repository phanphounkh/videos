<script lang="ts">
  /** The rename/mode dialog and the delete confirmation for uploaded hosts. */
  import { api } from '$lib/api';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import type { AvatarMode, CustomAvatar } from '$lib/types/api';
  import { loadHosts } from './hosts.svelte';
  import ModeChoice from './ModeChoice.svelte';

  let {
    editing = $bindable(null),
    deleting = $bindable(null),
    ondeleted = undefined
  }: {
    editing: CustomAvatar | null;
    deleting: CustomAvatar | null;
    ondeleted?: (id: string) => void;
  } = $props();

  let name = $state('');
  let mode = $state<AvatarMode>('mouth');
  let busy = $state(false);
  let error = $state<unknown>(null);

  $effect(() => {
    if (editing) {
      name = editing.name;
      mode = editing.mode;
      error = null;
    }
  });
  $effect(() => {
    if (deleting) error = null;
  });

  const uuid = (a: CustomAvatar) => a.id.replace(/^custom:/, '');

  async function save(e: SubmitEvent) {
    e.preventDefault();
    if (!editing) return;
    busy = true;
    error = null;
    try {
      await api.updateHostAvatar(uuid(editing), { name: name.trim() || editing.name, mode });
      await loadHosts(true);
      editing = null;
    } catch (err) {
      error = err;
    } finally {
      busy = false;
    }
  }

  async function remove() {
    if (!deleting) return;
    busy = true;
    error = null;
    try {
      const id = deleting.id;
      await api.deleteHostAvatar(uuid(deleting));
      await loadHosts(true);
      deleting = null;
      ondeleted?.(id);
    } catch (err) {
      error = err;
    } finally {
      busy = false;
    }
  }
</script>

{#if editing}
  <Modal title={t('avatars.editTitle')} onclose={() => (editing = null)}>
    <form class="flex flex-col gap-4" onsubmit={save}>
      <ErrorBanner {error} />
      <div>
        <label class="text-xs font-medium text-slate-400" for="avatar-edit-name">{t('avatars.name')}</label>
        <input id="avatar-edit-name" class="mt-1 h-10 w-full px-3 text-sm" bind:value={name} maxlength="60" />
      </div>
      <ModeChoice bind:value={mode} />
      <div class="flex justify-end gap-2">
        <Button variant="ghost" onclick={() => (editing = null)}>{t('common.cancel')}</Button>
        <Button type="submit" loading={busy}>{t('settings.saveChanges')}</Button>
      </div>
    </form>
  </Modal>
{/if}

{#if deleting}
  <Modal title={t('avatars.deleteTitle')} onclose={() => (deleting = null)}>
    <ErrorBanner {error} />
    <p>{t('avatars.deleteBody', { name: deleting.name })}</p>
    {#snippet actions()}
      <Button variant="ghost" onclick={() => (deleting = null)}>{t('common.cancel')}</Button>
      <Button variant="danger" loading={busy} onclick={remove}>{t('avatars.delete')}</Button>
    {/snippet}
  </Modal>
{/if}
