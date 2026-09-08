/**
 * CHERENKOV-QA Version Banner Controller
 * Ensures outdated warning banner is suppressed on canonical v1.4 / latest pages
 * and displayed on older versions (1.0, 1.1, 1.2, 1.3).
 */
(function () {
  function updateVersionBanner() {
    var path = window.location.pathname;
    var outdatedEls = document.querySelectorAll('[data-md-component="outdated"], .md-version-warning');

    if (!outdatedEls.length) return;

    var isLatest = (
      path.indexOf('/1.4/') !== -1 ||
      path.indexOf('/latest/') !== -1 ||
      path.indexOf('/1.4') === path.length - 4 ||
      (!path.match(/\/1\.[0-3]\//) && !path.match(/\/1\.[0-3]$/))
    );

    var isOlder = (
      path.indexOf('/1.0/') !== -1 ||
      path.indexOf('/1.1/') !== -1 ||
      path.indexOf('/1.2/') !== -1 ||
      path.indexOf('/1.3/') !== -1 ||
      path.match(/\/1\.[0-3]$/)
    );

    outdatedEls.forEach(function (el) {
      if (isLatest && !isOlder) {
        el.hidden = true;
        el.setAttribute('hidden', '');
        el.style.display = 'none';
      } else if (isOlder) {
        el.hidden = false;
        el.removeAttribute('hidden');
        el.style.display = 'block';
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateVersionBanner);
  } else {
    updateVersionBanner();
  }

  // Support Material for MkDocs instant loading
  if (window.location && typeof document$ !== 'undefined') {
    document$.subscribe(updateVersionBanner);
  }
})();
