<script lang="ts" generics="T extends string | number">
  /** A row of mutually exclusive choices: clearer than a dropdown for 2-5 options. */
  let {
    options,
    value = $bindable(),
    label = undefined,
    onchange = undefined
  }: {
    options: { value: T; label: string; hint?: string }[];
    value: T;
    label?: string;
    onchange?: (value: T) => void;
  } = $props();
</script>

<div
  class="inline-flex w-full rounded-[0.7rem] border border-slate-700 bg-slate-900 p-0.5"
  role="radiogroup"
  aria-label={label}
>
  {#each options as option (option.value)}
    <button
      type="button"
      role="radio"
      aria-checked={value === option.value}
      title={option.hint}
      class="flex-1 rounded-[0.55rem] px-2.5 py-1.5 text-center text-sm font-medium whitespace-nowrap transition {value ===
      option.value
        ? 'bg-slate-700 text-slate-50 shadow-sm'
        : 'text-slate-400 hover:text-slate-200'}"
      onclick={() => {
        value = option.value;
        onchange?.(option.value);
      }}
    >
      {option.label}
    </button>
  {/each}
</div>
