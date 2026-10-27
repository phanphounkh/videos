/**
 * Fades an element up into place the first time it scrolls into view.
 *
 *     <section use:reveal>            <li use:reveal={{ delay: 80 }}>
 *
 * The starting look lives in CSS (`.reveal`), so nothing flashes; this only adds the
 * `.revealed` class. People who prefer reduced motion see everything immediately.
 */
export function reveal(node: HTMLElement, options: { delay?: number } = {}) {
  node.classList.add('reveal');
  if (options.delay) node.style.transitionDelay = `${options.delay}ms`;

  const show = () => node.classList.add('revealed');
  if (typeof IntersectionObserver === 'undefined' || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    show();
    return {};
  }
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        show();
        observer.disconnect();
      }
    },
    { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }
  );
  observer.observe(node);
  return { destroy: () => observer.disconnect() };
}
