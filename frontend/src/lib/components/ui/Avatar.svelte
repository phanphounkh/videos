<script lang="ts">
  /**
   * A person's picture, or a default avatar when they have none: their initial on a soft
   * gradient. The gradient is picked from the user id, so a person always keeps the same
   * colour and different people are easy to tell apart.
   */
  type Person = { id?: string; email: string; full_name?: string | null; avatar_url?: string | null };

  let {
    user,
    size = 32,
    class: extra = ''
  }: { user: Person; size?: number; class?: string } = $props();

  const PALETTE = [
    'from-amber-400 to-orange-500',
    'from-rose-400 to-pink-600',
    'from-teal-400 to-cyan-600',
    'from-violet-400 to-purple-600',
    'from-sky-400 to-blue-600',
    'from-emerald-400 to-green-600',
    'from-fuchsia-400 to-purple-500',
    'from-red-400 to-rose-600'
  ];

  const label = $derived((user.full_name?.trim() || user.email.split('@')[0] || '?').trim());
  // Khmer and other scripts: the first character, not the first byte.
  const initial = $derived(Array.from(label)[0]?.toUpperCase() ?? '?');
  const tone = $derived.by(() => {
    let h = 0;
    for (const ch of user.id ?? user.email) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  });

  // If the picture fails to load, fall back to the default instead of a broken image.
  let broken = $state(false);
  $effect(() => {
    void user.avatar_url;
    broken = false;
  });
</script>

<span
  class="inline-grid shrink-0 place-items-center overflow-hidden rounded-full bg-gradient-to-br font-bold text-white select-none {tone} {extra}"
  style="width:{size}px; height:{size}px; font-size:{Math.round(size * 0.42)}px"
  aria-hidden="true"
>
  {#if user.avatar_url && !broken}
    <img src={user.avatar_url} alt="" class="h-full w-full object-cover" draggable="false" onerror={() => (broken = true)} />
  {:else}
    {initial}
  {/if}
</span>
