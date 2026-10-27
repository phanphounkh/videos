<script lang="ts">
  /** Usage lives under Settings now; old links and bookmarks land there. */
  import { goto } from '$app/navigation';

  $effect(() => {
    void goto('/settings?tab=usage', { replaceState: true });
  });
</script>
