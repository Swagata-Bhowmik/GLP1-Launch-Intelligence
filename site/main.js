// LaunchLens site: smooth scroll, scroll reveals, count-up numbers, glowing cursor with light trail, parallax.
(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;

  // ── smooth scrolling (Lenis); native scrolling still works if the CDN is unavailable ──
  let lenis = null;
  if (!reduce && window.Lenis) {
    lenis = new Lenis({ duration: 1.15, smoothWheel: true });
    window.lenis = lenis;
    const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
    document.querySelectorAll('a[href^="#"]').forEach((a) => a.addEventListener("click", (e) => {
      const target = document.querySelector(a.getAttribute("href"));
      if (target) { e.preventDefault(); lenis.scrollTo(target, { offset: -20 }); }
    }));
  }

  // ── count-up numbers ──
  const fmt = (v, dec) => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const countUp = (el) => {
    if (el.dataset.done) return; el.dataset.done = 1;
    const target = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0);
    const pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
    if (reduce) { el.textContent = pre + fmt(target, dec) + suf; return; }
    const t0 = performance.now(), dur = 1600;
    const tick = (now) => {
      const p = Math.min((now - t0) / dur, 1), e = 1 - Math.pow(1 - p, 4);
      el.textContent = pre + fmt(target * e, dec) + suf;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  // ── reveal on scroll ──
  const io = new IntersectionObserver((entries) => entries.forEach((en) => {
    if (!en.isIntersecting) return;
    en.target.classList.add("in");
    en.target.querySelectorAll("[data-count]").forEach(countUp);
    if (en.target.matches("[data-count]")) countUp(en.target);
    io.unobserve(en.target);
  }), { threshold: 0.18, rootMargin: "0px 0px -6% 0px" });
  document.querySelectorAll(".reveal, .fc").forEach((el) => io.observe(el));
  // hero numbers start right away
  setTimeout(() => document.querySelectorAll(".fc [data-count]").forEach(countUp), 500);

  // ── nav background after scrolling ──
  const nav = document.querySelector(".nav");
  const onScroll = () => {
    const y = window.scrollY;
    nav.classList.toggle("scrolled", y > 40);
    if (!reduce) {
      const bg = document.querySelector(".hero-bg");
      if (bg && y < innerHeight * 1.2) bg.style.transform = `translate3d(0, ${y * 0.18}px, 0) scale(1.04)`;
      drawStoryLine();
    }
  };
  addEventListener("scroll", onScroll, { passive: true });

  // ── story line draws itself as the section scrolls into view ──
  const line = document.getElementById("storyLine");
  const len = line ? line.getTotalLength() : 0;
  if (line) { line.style.strokeDasharray = len; line.style.strokeDashoffset = reduce ? 0 : len; }
  function drawStoryLine() {
    if (!line) return;
    const r = document.getElementById("story").getBoundingClientRect();
    const p = Math.min(Math.max((innerHeight - r.top) / (innerHeight * 0.9), 0), 1);
    line.style.strokeDashoffset = len * (1 - p);
  }
  onScroll();

  // ── glowing cursor + light trail ──
  if (finePointer && !reduce) {
    document.body.classList.add("has-cursor");
    const dot = document.querySelector(".cursor-dot"), ring = document.querySelector(".cursor-ring");
    const cv = document.getElementById("trail"), ctx = cv.getContext("2d");
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const size = () => { cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
    size(); addEventListener("resize", size);
    let mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my;
    const pts = [];
    addEventListener("pointermove", (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      pts.push({ x: mx, y: my, life: 1 });
      if (pts.length > 60) pts.shift();
    }, { passive: true });
    const hoverables = "a, button, [data-hover], .step";
    document.addEventListener("pointerover", (e) => { if (e.target.closest(hoverables)) ring.classList.add("hover"); });
    document.addEventListener("pointerout", (e) => { if (e.target.closest(hoverables)) ring.classList.remove("hover"); });
    const loop = () => {
      rx += (mx - rx) * 0.18; ry += (my - ry) * 0.18;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i];
        b.life -= 0.022;
        if (b.life <= 0) continue;
        const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        g.addColorStop(0, `rgba(34,211,197,${a.life * 0.55})`);
        g.addColorStop(1, `rgba(79,107,255,${b.life * 0.65})`);
        ctx.strokeStyle = g; ctx.lineWidth = 3 * b.life; ctx.lineCap = "round";
        ctx.shadowColor = "rgba(34,211,197,.8)"; ctx.shadowBlur = 12;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      while (pts.length && pts[0].life <= 0) pts.shift();
      requestAnimationFrame(loop);
    };
    loop();
    addEventListener("pointerleave", () => { dot.style.opacity = ring.style.opacity = 0; });
    addEventListener("pointerenter", () => { dot.style.opacity = ring.style.opacity = 1; });
  }

  // ── gentle 3-D tilt on the floating hero cards ──
  if (finePointer && !reduce) {
    const hero = document.querySelector(".hero");
    hero.addEventListener("pointermove", (e) => {
      const nx = e.clientX / innerWidth - 0.5, ny = e.clientY / innerHeight - 0.5;
      document.querySelectorAll("[data-tilt]").forEach((c, i) => {
        const k = (i + 1) * 6;
        c.style.transform = `perspective(800px) rotateY(${nx * 10}deg) rotateX(${-ny * 10}deg) translate3d(${-nx * k}px, ${-ny * k}px, 0)`;
      });
    });
  }
})();
