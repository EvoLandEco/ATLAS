export function connectParent(setTheme) {
  if (window.parent === window) return;
  document.documentElement.dataset.embedded = 'true';
  const origin = 'https://qtj.me';
  document.getElementById('close-review').addEventListener('click', () => {
    window.parent.postMessage({type: 'atlas-review-close'}, origin);
  });
  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.origin !== origin || event.data?.type !== 'atlas-review-theme') return;
    if (['light', 'dark'].includes(event.data.theme)) setTheme(event.data.theme === 'dark');
  });
  const announce = ready => window.parent.postMessage({type: 'atlas-review-ready', ready}, origin);
  window.addEventListener('pageshow', () => announce(true));
  window.addEventListener('pagehide', () => announce(false));
  announce(true);
}
