<script lang="ts">
  import { ApiError } from '$lib/api/client';
  import Icon from '$lib/components/ui/Icon.svelte';

  let { error }: { error: unknown } = $props();

  const text = $derived(
    error instanceof ApiError
      ? `${error.message} (${error.code})`
      : error
        ? String(error)
        : ''
  );
</script>

{#if text}
  <p
    class="flex items-start gap-2.5 rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-200"
    role="alert"
  >
    <Icon name="alert" size={16} class="mt-0.5 text-red-300" />
    <span>{text}</span>
  </p>
{/if}
