if (window.opener) {
  window.opener.postMessage({type: 'atlas-review-signed-in'}, 'https://qtj.me');
  window.close();
}
