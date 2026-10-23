// LaunchLens site: app links, scroll reveals, count-up numbers, glowing cursor with light trail, light parallax.
// Performance: native scrolling (no scroll-jacking library), all scroll work batched into one animation frame,
// and the cursor trail only draws while the pointer moves.
(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const APP = "https://glp1-launchlens.streamlit.app/";

  // ── app links ──
  // Inside the app (Streamlit Community Cloud), this page runs in nested frames that may not navigate the whole
  // browser tab, so open the page in the app's own frame (same origin). Standalone (GitHub Pages): normal link.
  document.querySelectorAll("a[data-page]").forEach((a) => a.addEventListener("click", (e) => {
    const page = a.dataset.page;
    if (window.parent !== window) {
      try {
        const base = window.parent.document.baseURI;      // e.g. https://…streamlit.app/~/+/ on Cloud, http://localhost:8501/ locally
        e.preventDefault();
        window.parent.location.href = new URL(page, base).href;
        return;
      } catch (err) { /* cross-origin parent: fall back to the normal link */ }
    }
    e.preventDefault();
    window.location.href = APP + page;
  }));

  // ── in-page anchors: native smooth scroll with an offset for the fixed nav ──
  document.querySelectorAll('a[href^="#"]').forEach((a) => a.addEventListener("click", (e) => {
    const t = document.querySelector(a.getAttribute("href"));
    if (!t) return;
    e.preventDefault();
    window.scrollTo({ top: t.getBoundingClientRect().top + window.scrollY - 20, behavior: reduce ? "auto" : "smooth" });
  }));

  // ── count-up numbers ──
  const fmt = (v, dec) => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const countUp = (el) => {
    if (el.dataset.done) return; el.dataset.done = 1;
    const target = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0);
    const pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
    if (reduce) { el.textContent = pre + fmt(target, dec) + suf; return; }
    const t0 = performance.now(), dur = 1500;
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
    io.unobserve(en.target);
  }), { threshold: 0.15, rootMargin: "0px 0px -5% 0px" });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  setTimeout(() => document.querySelectorAll(".fc [data-count]").forEach(countUp), 400);

  // ── scroll effects, batched into one frame ──
  const nav = document.querySelector(".nav");
  const bg = document.querySelector(".hero-bg");
  const line = document.getElementById("storyLine");
  const story = document.getElementById("story");
  const len = line ? line.getTotalLength() : 0;
  if (line) { line.style.strokeDasharray = len; line.style.strokeDashoffset = reduce ? 0 : len; }
  let ticking = false;
  const update = () => {
    ticking = false;
    const y = window.scrollY, h = window.innerHeight;
    nav.classList.toggle("scrolled", y > 40);
    if (reduce) return;
    if (bg && y < h * 1.2) bg.style.transform = `translate3d(0, ${y * 0.15}px, 0)`;
    if (line) {
      const r = story.getBoundingClientRect();
      const p = Math.min(Math.max((h - r.top) / (h * 0.9), 0), 1);
      line.style.strokeDashoffset = len * (1 - p);
    }
  };
  addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  update();

  // ── glowing cursor + light trail (desktop only) ──
  if (finePointer && !reduce) {
    document.body.classList.add("has-cursor");
    const dot = document.querySelector(".cursor-dot"), ring = document.querySelector(".cursor-ring");
    const cv = document.getElementById("trail"), ctx = cv.getContext("2d");
    const size = () => { cv.width = innerWidth; cv.height = innerHeight; };
    size(); addEventListener("resize", size);
    let mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my, running = false;
    const pts = [];
    const frame = () => {
      rx += (mx - rx) * 0.22; ry += (my - ry) * 0.22;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.lineCap = "round";
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i];
        b.life -= 0.04;
        if (b.life <= 0) continue;
        ctx.strokeStyle = `rgba(34,211,197,${b.life * 0.55})`;
        ctx.lineWidth = 3.2 * b.life;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      while (pts.length && pts[0].life <= 0) pts.shift();
      // keep animating only while something is still moving
      if (pts.length > 1 || Math.abs(mx - rx) + Math.abs(my - ry) > 0.5) requestAnimationFrame(frame);
      else { running = false; ctx.clearRect(0, 0, cv.width, cv.height); }
    };
    addEventListener("pointermove", (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      pts.push({ x: mx, y: my, life: 1 });
      if (pts.length > 28) pts.shift();
      if (!running) { running = true; requestAnimationFrame(frame); }
    }, { passive: true });
    const hoverables = "a, button, [data-hover], .step";
    document.addEventListener("pointerover", (e) => { if (e.target.closest(hoverables)) ring.classList.add("hover"); });
    document.addEventListener("pointerout", (e) => { if (e.target.closest(hoverables)) ring.classList.remove("hover"); });
    document.addEventListener("pointerleave", () => { dot.style.opacity = ring.style.opacity = 0; });
    document.addEventListener("pointerenter", () => { dot.style.opacity = ring.style.opacity = 1; });

    // gentle tilt on the floating hero cards (only while the pointer is over the hero)
    const hero = document.querySelector(".hero"), cards = [...document.querySelectorAll("[data-tilt]")];
    hero.addEventListener("pointermove", (e) => {
      const nx = e.clientX / innerWidth - 0.5, ny = e.clientY / innerHeight - 0.5;
      cards.forEach((c, i) => {
        const k = (i + 1) * 5;
        c.style.transform = `perspective(800px) rotateY(${nx * 8}deg) rotateX(${-ny * 8}deg) translate3d(${-nx * k}px, ${-ny * k}px, 0)`;
      });
    }, { passive: true });
  }
})();
