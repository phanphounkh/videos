<script lang="ts">
  /** Shared frame for login and register: brand panel on the left, form on the right. */
  import { onMount } from 'svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';

  let {
    title,
    subtitle,
    children,
    footer
  }: {
    title: string;
    subtitle: string;
    children?: import('svelte').Snippet;
    footer?: import('svelte').Snippet;
  } = $props();

  // Logo's SVG gradient has a fixed id, and a display:none copy cannot supply it
  // to the visible one. So exactly one Logo is rendered at a time.
  let wide = $state(false);
  onMount(() => {
    const query = window.matchMedia('(min-width: 1024px)');
    const sync = () => (wide = query.matches);
    sync();
    query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  });

  const benefits: { icon: IconName; text: string }[] = [
    { icon: 'sparkles', text: 'Write the script, scenes and voice from one prompt' },
    { icon: 'film', text: 'Product demos, social posts, stories and explainers' },
    { icon: 'captions', text: 'Khmer and English, with timed captions built in' }
  ];
</script>

<main class="grid min-h-full lg:grid-cols-[1.05fr_1fr]">
  <aside
    class="relative hidden overflow-hidden border-r border-slate-800 bg-slate-900/40 p-12 lg:flex lg:flex-col lg:justify-between"
  >
    <div
      class="pointer-events-none absolute -top-40 -left-32 h-[34rem] w-[34rem] rounded-full bg-sun-500/20 blur-3xl"
    ></div>
    <div
      class="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-sun-700/15 blur-3xl"
    ></div>
    <div class="relative">{#if wide}<Logo size={34} />{/if}</div>
    <div class="relative max-w-md">
      <h2 class="text-[28px] leading-tight font-semibold tracking-tight text-slate-50">
        Turn an idea into a <span class="sun-text">finished video</span>
      </h2>
      <ul class="mt-8 flex flex-col gap-4">
        {#each benefits as benefit (benefit.text)}
          <li class="flex items-start gap-3 text-sm leading-relaxed text-slate-300">
            <span
              class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-sun-500/15 text-sun-300"
            >
              <Icon name={benefit.icon} size={15} />
            </span>
            {benefit.text}
          </li>
        {/each}
      </ul>
    </div>
    <p class="relative text-xs text-slate-500">សូរ្យ · Sorya means “the sun” in Khmer</p>
  </aside>

  <section class="flex items-center justify-center px-5 py-10 sm:px-10">
    <div class="w-full max-w-sm">
      <div class="mb-8 lg:hidden">{#if !wide}<Logo size={30} />{/if}</div>
      <h1 class="text-[28px] leading-tight font-semibold tracking-tight text-slate-50">{title}</h1>
      <p class="mt-1.5 mb-7 text-sm text-slate-400">{subtitle}</p>
      {@render children?.()}
      <div class="mt-6 text-sm text-slate-400">{@render footer?.()}</div>
    </div>
  </section>
</main>
