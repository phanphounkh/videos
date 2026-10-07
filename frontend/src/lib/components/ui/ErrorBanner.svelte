<script lang="ts">
  import { ApiError } from '$lib/api/client';

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
  <p class="rounded-lg border border-red-900/60 bg-red-950/50 px-4 py-3 text-sm text-red-200">
    {text}
  </p>
{/if}
