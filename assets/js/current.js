/* ============================================================
   current.js — 整屏「电流」
   每条电流 = 一条随机 PCB 走线 + 一段沿走线流动的亮段。
   走线只走 0° / 45° / 90°（PCB 规矩），出画就换一条新的。

   为什么用 canvas 而不是 CSS：
   PCB 的电流感来自「细走线 + 一条带渐变拖尾的亮段 + 一点辉光」，
   CSS 的逐点点亮做不出这种连续流动，索性整层用 canvas 画。

   视野约束：整块 canvas 是 z-index:-1，卡片自带白底会盖住它，
   所以电流只在页面留白和卡片缝隙里出现，永远压不住正文。
   ============================================================ */
(function () {
  'use strict';

  var cv = document.querySelector('.current');
  if (!cv) return;

  var ctx = cv.getContext('2d', { alpha: true });
  var wide = window.matchMedia('(min-width: 1600px)');
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');

  var W = 0, H = 0;
  var brand = '27, 77, 255';          // 兜底：#1B4DFF
  var lines = [];
  var raf = 0, prev = 0, running = false;

  var SPEED_MIN = 210, SPEED_MAX = 340;   // px/s，逐条随机
  var TAIL_MIN = 90, TAIL_MAX = 150;      // 拖尾长度 px
  var HOLD = 1.1;                          // 走完后再留多久（秒）
  var FADE = 1.5;                          // 淡出时长（秒）

  /* ---------- 颜色：把 --brand 换成 "r, g, b" ---------- */

  function hexToRgb(hex) {
    hex = (hex || '').trim();
    if (hex.charAt(0) === '#') hex = hex.slice(1);
    if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    var n = parseInt(hex, 16);
    if (!isFinite(n) || hex.length !== 6) return '27, 77, 255';
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', ');
  }

  function readBrand() {
    // 取到的自定义属性可能带前后空白，先 trim 再判格式
    var v = (getComputedStyle(document.documentElement).getPropertyValue('--brand') || '').trim();
    if (v.charAt(0) === '#') brand = hexToRgb(v);
  }

  function rgba(a) { return 'rgba(' + brand + ', ' + a + ')'; }

  /* ---------- 一条走线 ---------- */

  function rand(a, b) { return a + Math.random() * (b - a); }

  function makeLine() {
    var pad = 80;
    var side = Math.floor(Math.random() * 4);
    var x, y, ang;

    if (side === 0) { x = rand(0, W); y = -pad; ang = Math.PI / 2; }
    else if (side === 1) { x = W + pad; y = rand(0, H); ang = Math.PI; }
    else if (side === 2) { x = rand(0, W); y = H + pad; ang = -Math.PI / 2; }
    else { x = -pad; y = rand(0, H); ang = 0; }

    var pts = [{ x: x, y: y }];
    var out = false;

    for (var i = 0; i < 48 && !out; i++) {
      var r = Math.random();
      if (r < 0.58) ang += 0;                       // 直行
      else if (r < 0.79) ang += Math.PI / 4;        // 45°
      else if (r < 0.94) ang -= Math.PI / 4;
      else ang += Math.PI / 2;                      // 直角拐

      // 吸附到 45° 网格，走线永远只有 0/45/90
      ang = Math.round(ang / (Math.PI / 4)) * (Math.PI / 4);

      var len = rand(60, 190);
      x += Math.cos(ang) * len;
      y += Math.sin(ang) * len;
      pts.push({ x: x, y: y });

      if (x < -160 || x > W + 160 || y < -160 || y > H + 160) out = true;
    }

    // 兜底：48 段还没出画，就顺着最后方向延长到画外，保证「走出画面」这件事成立
    if (!out) {
      var last = pts[pts.length - 1];
      pts.push({ x: last.x + Math.cos(ang) * 2600, y: last.y + Math.sin(ang) * 2600 });
    }

    var cum = [0];
    for (var k = 1; k < pts.length; k++) {
      cum.push(cum[k - 1] + Math.hypot(pts[k].x - pts[k - 1].x, pts[k].y - pts[k - 1].y));
    }

    return {
      pts: pts,
      cum: cum,
      total: cum[cum.length - 1],
      p: -rand(0, 260),           // 负值 = 还没出发，错开各条的出现时机
      tail: rand(TAIL_MIN, TAIL_MAX),
      speed: rand(SPEED_MIN, SPEED_MAX),
      fade: 1,
      hold: 0,
      phase: 'run'
    };
  }

  function pointAt(L, d) {
    var cum = L.cum, pts = L.pts;
    if (d <= 0) return pts[0];
    if (d >= L.total) return pts[pts.length - 1];
    var lo = 0, hi = cum.length - 1;
    while (lo + 1 < hi) {
      var mid = (lo + hi) >> 1;
      if (cum[mid] <= d) lo = mid; else hi = mid;
    }
    var span = cum[lo + 1] - cum[lo] || 1;
    var t = (d - cum[lo]) / span;
    return {
      x: pts[lo].x + (pts[lo + 1].x - pts[lo].x) * t,
      y: pts[lo].y + (pts[lo + 1].y - pts[lo].y) * t
    };
  }

  /* ---------- 画 ---------- */

  function draw(L, a, still) {
    var i, pts = L.pts;

    // 1) 走线本体
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.strokeStyle = rgba(0.17 * a);
    ctx.lineWidth = 1;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();

    // 2) 过孔：每个拐点一枚小圈，PCB 味主要来自这里
    ctx.strokeStyle = rgba(0.22 * a);
    ctx.lineWidth = 1;
    for (i = 1; i < pts.length - 1; i++) {
      ctx.beginPath();
      ctx.arc(pts[i].x, pts[i].y, 2.6, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (still) return;

    // 3) 拖尾：从尾到头逐段加粗加亮，读作「电流正往这边跑」
    var head = Math.min(L.p, L.total);
    var tail = Math.max(0, head - L.tail);
    var N = 22;
    ctx.lineCap = 'round';
    for (i = 0; i < N; i++) {
      var d0 = tail + (head - tail) * (i / N);
      var d1 = tail + (head - tail) * ((i + 1) / N);
      var p0 = pointAt(L, d0), p1 = pointAt(L, d1);
      var f = (i + 1) / N;
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.strokeStyle = rgba((0.06 + 0.9 * f * f) * a);
      ctx.lineWidth = 1 + 2.4 * f;
      ctx.stroke();
    }

    // 4) 头：一枚带辉光的小亮点，是整条线的视觉落点
    var hp = pointAt(L, head);
    ctx.save();
    ctx.shadowColor = rgba(0.9 * a);
    ctx.shadowBlur = 18;
    ctx.fillStyle = rgba(0.98 * a);
    ctx.beginPath();
    ctx.arc(hp.x, hp.y, 2.9, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  /* ---------- 主循环 ---------- */

  function tick(now) {
    if (!running) return;
    var dt = prev ? Math.min(0.05, (now - prev) / 1000) : 0.016;
    prev = now;

    var still = calm.matches;
    var want = Math.max(4, Math.min(8, Math.round(W / 400)));
    while (lines.length < want) lines.push(makeLine());

    ctx.clearRect(0, 0, W, H);

    for (var i = lines.length - 1; i >= 0; i--) {
      var L = lines[i];

      if (!still) {
        if (L.p < 0) {                     // 还没出发：整条不画，避免一上来铺满屏
          L.p += L.speed * dt;
          continue;
        }
        if (L.phase === 'run') {
          L.p += L.speed * dt;
          if (L.p >= L.total) { L.p = L.total; L.phase = 'hold'; }
        } else if (L.phase === 'hold') {
          L.hold += dt;
          if (L.hold > HOLD) L.phase = 'fade';
        } else {
          L.fade -= dt / FADE;
          if (L.fade <= 0) { lines.splice(i, 1); continue; }
        }
      }

      // 前 240px 淡入，避免走线「啪」一下出现
      draw(L, still ? 1 : Math.min(1, L.p / 240) * L.fade, still);
    }

    // 减少动效：只画一次静态电路，然后停帧
    if (still) { running = false; raf = 0; return; }

    raf = requestAnimationFrame(tick);
  }

  /* ---------- 尺寸 / 开关 ---------- */

  function stop() {
    running = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    lines.length = 0;
    if (W && H) ctx.clearRect(0, 0, W, H);
  }

  function start() {
    if (running) return;
    running = true;
    prev = 0;
    raf = requestAnimationFrame(tick);
  }

  function resize() {
    var on = wide.matches;          // 减少动效时不隐藏，改成只画静态电路
    cv.style.display = on ? '' : 'none';
    if (!on) { stop(); return; }

    // dpr 固定 1：装饰层不需要高清，省掉四分之三的填充开销
    W = cv.clientWidth;
    H = cv.clientHeight;
    cv.width = W;
    cv.height = H;

    lines.length = 0;
    readBrand();
    start();
  }

  var rt = 0;
  window.addEventListener('resize', function () {
    clearTimeout(rt);
    rt = setTimeout(resize, 160);
  });

  // 切主题要换电流颜色（浅色 #1B4DFF / 深色 #6C8CFF）
  new MutationObserver(readBrand).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { running = false; if (raf) cancelAnimationFrame(raf); raf = 0; }
    else if (wide.matches && !calm.matches) { start(); }
  });

  if (wide.addEventListener) {
    wide.addEventListener('change', resize);
    calm.addEventListener('change', resize);
  }

  resize();
})();
