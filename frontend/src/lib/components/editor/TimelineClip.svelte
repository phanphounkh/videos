<script lang="ts">
  let {
    label,
    left,
    width,
    tone,
    selected = false,
    title = '',
    onclick = undefined
  }: {
    label: string;
    left: number;
    width: number;
    tone: string;
    selected?: boolean;
    title?: string;
    onclick?: () => void;
  } = $props();
</script>

<button
  class="absolute top-1 bottom-1 overflow-hidden rounded px-1.5 text-left text-[10px] whitespace-nowrap text-white/90 {tone} {selected
    ? 'ring-2 ring-sun-400'
    : ''}"
  style={`left:${left}%; width:${width}%`}
  {title}
  {onclick}
>
  {label}
</button>
