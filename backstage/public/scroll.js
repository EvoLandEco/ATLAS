export function connectScrollCue(scroll, content, cue) {
  const update = () => {
    const more = scroll.clientHeight > 0 && Math.ceil(scroll.scrollTop) < scroll.scrollHeight - scroll.clientHeight;
    if (!more && document.activeElement === cue) scroll.focus({preventScroll:true});
    cue.dataset.more = String(more);
    cue.tabIndex = more ? 0 : -1;
    cue.setAttribute('aria-hidden', String(!more));
  };
  const observer = new ResizeObserver(update);
  observer.observe(scroll);
  observer.observe(content);
  scroll.addEventListener('scroll', update, {passive:true});
  cue.addEventListener('click', () => scroll.scrollBy({top:scroll.clientHeight, behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}));
  update();
}
