/* ============================================================
   doc.js — 详情页增强：代码复制 / 目录高亮
   无依赖，约 2KB；不启用时页面仍完整可用。
   ============================================================ */
(function () {
  'use strict';

  /* ---------- 代码复制 ---------- */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // file:// 或旧浏览器的兜底
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      ok ? resolve() : reject(new Error('copy failed'));
    });
  }

  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    var label = btn.textContent;
    var timer = null;

    btn.addEventListener('click', function () {
      var box = btn.closest('.code');
      var pre = box && box.querySelector('pre');
      if (!pre) return;

      copyText(pre.innerText).then(function () {
        btn.textContent = '已复制';
        btn.classList.add('is-done');
      }).catch(function () {
        btn.textContent = '复制失败';
      }).then(function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          btn.textContent = label;
          btn.classList.remove('is-done');
        }, 1800);
      });
    });
  });

  /* ---------- 目录跟随滚动高亮 ---------- */
  var list = document.querySelector('[data-toc-list]');
  if (!list) return;

  var links = Array.prototype.slice.call(list.querySelectorAll('a'));
  var heads = links.map(function (a) {
    return document.getElementById(a.getAttribute('href').slice(1));
  });

  if (!heads.length || heads.some(function (h) { return !h; })) return;

  var navH = parseInt(
    getComputedStyle(document.documentElement).getPropertyValue('--nav-h'),
    10
  ) || 64;

  var bar = document.querySelector('.doc__actions');
  var ticking = false;

  function sync() {
    ticking = false;
    var active = 0;

    // 工具条吸附到导航下方后浮现阴影，静止时保持贴合
    if (bar) {
      bar.classList.toggle('is-stuck', bar.getBoundingClientRect().top <= navH + 15);
    }

    heads.forEach(function (h, i) {
      if (h.getBoundingClientRect().top - navH - 48 <= 0) active = i;
    });

    // 滚到底时强制点亮最后一项
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) {
      active = heads.length - 1;
    }

    links.forEach(function (a, i) {
      a.classList.toggle('is-active', i === active);
      if (i === active) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(sync);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  sync();
})();
