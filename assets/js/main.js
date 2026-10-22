/* ============================================================
   main.js — 主题切换 / 入场动画
   无依赖，约 2.5KB。所有增强均在缺省可用（渐进增强）。
   ============================================================ */

(function () {
  'use strict';

  /* ---------- 主题 ---------- */
  var STORE_KEY = 'site-theme';
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem(STORE_KEY);
    if (saved === 'dark' || saved === 'light') root.setAttribute('data-theme', saved);
  } catch (e) { /* 隐私模式忽略 */ }

  function syncToggle() {
    var isDark = root.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(isDark));
      btn.setAttribute('aria-label', isDark ? '切换到浅色模式' : '切换到深色模式');
      var useEl = btn.querySelector('use');
      if (useEl) useEl.setAttribute('href', isDark ? '#i-sun' : '#i-moon');
    });
  }

  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem(STORE_KEY, next); } catch (e) {}
      syncToggle();
    });
  });
  syncToggle();

  /* 未手动选过主题时，跟随系统偏好的实时变化 */
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  function onSchemeChange(e) {
    var saved = null;
    try { saved = localStorage.getItem(STORE_KEY); } catch (err) {}
    if (saved === 'dark' || saved === 'light') return;
    root.setAttribute('data-theme', e.matches ? 'dark' : 'light');
    syncToggle();
  }
  if (mq.addEventListener) mq.addEventListener('change', onSchemeChange);
  else if (mq.addListener) mq.addListener(onSchemeChange);

  /* ---------- 滚动入场 ---------- */
  var reveals = document.querySelectorAll('.reveal');
  if (!reveals.length) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) {
    reveals.forEach(function (el) { el.classList.add('is-in'); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      io.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

  reveals.forEach(function (el) { io.observe(el); });
})();
