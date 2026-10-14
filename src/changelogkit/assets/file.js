/* 檔案檢視：行號、行跳轉、目標行高亮；Swift 上色；Markdown 預設排版檢視（可切回原始碼）。 */
(function () {
  const src = document.getElementById("src");
  if (!src) return;
  const rendered = document.getElementById("rendered");
  const modeBtn = document.getElementById("mode");
  const jump = document.getElementById("jump");
  const isMarkdown = /\.(md|markdown)$/i.test(src.dataset.path || "");

  // 1) 原始碼逐行上色（Markdown 也用於「原始碼」模式）。
  //    上色只影響「顯示」：先保留原始文字供排版檢視當來源，避免被上色改寫汙染。
  const rawLines = Array.from(src.querySelectorAll(".code")).map((el) => el.textContent);
  const state = { block: false };
  src.querySelectorAll(".code").forEach((el) => {
    el.innerHTML = isMarkdown ? HL.markdownLine(el.textContent) : HL.swift(el.textContent, state);
  });

  const lines = src.querySelectorAll(".ln");
  const total = lines.length;
  const initial = parseInt(src.dataset.line || "0", 10);

  function highlight(line) {
    if (!(line >= 1 && line <= total)) return;
    src.querySelectorAll(".ln.hit").forEach((el) => el.classList.remove("hit"));
    const el = document.getElementById("L" + line);
    if (el) { el.classList.add("hit"); el.scrollIntoView({ block: "center" }); }
  }
  function fromHash() {
    const m = (location.hash || "").match(/^#L(\d+)$/);
    return m ? parseInt(m[1], 10) : initial;
  }
  function go(line, push) {
    if (!(line >= 1 && line <= total)) return;
    if (push) history.replaceState(null, "", "#L" + line);
    highlight(line);
  }

  src.addEventListener("click", (e) => {
    const a = e.target.closest ? e.target.closest("a.no") : null;
    const href = a && a.getAttribute("href");
    if (href && href.indexOf("#L") === 0) { e.preventDefault(); go(parseInt(href.slice(2), 10), true); }
  });

  if (jump) {
    jump.max = total;
    jump.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); go(parseInt(jump.value, 10), true); }
    });
  }

  document.getElementById("copy")?.addEventListener("click", async (e) => {
    const path = src.dataset.path || "";
    try { await navigator.clipboard.writeText(path); e.currentTarget.textContent = CK_T("file.copied"); }
    catch { e.currentTarget.textContent = path; }
    setTimeout(() => { e.currentTarget.textContent = CK_T("file.copy"); }, 1500);
  });

  document.getElementById("back")?.addEventListener("click", (e) => {
    if (history.length > 1) { e.preventDefault(); history.back(); }
  });

  window.addEventListener("hashchange", () => { if (!src.hidden) highlight(fromHash()); });

  // 2) Markdown：排版檢視（預設）＋可切回原始碼。
  // 連結改寫共用 markdown.js 的解析器（依本檔在 repo 內的路徑推相對基準）。
  const resolveHref = window.markdownResolver(src.dataset.repo || "app", src.dataset.path || "");

  function setMode(mode) {
    const renderedMode = mode === "rendered";
    src.hidden = renderedMode;
    if (rendered) rendered.hidden = !renderedMode;
    if (jump) jump.hidden = renderedMode;
    if (modeBtn) modeBtn.textContent = renderedMode ? CK_T("file.source") : CK_T("file.rendered");
  }

  if (isMarkdown && rendered && modeBtn) {
    rendered.innerHTML = window.renderMarkdown(rawLines.join("\n"), resolveHref);
    // 文件內的 #L 行號連結：切回原始碼模式再跳行（就地，不重載）。
    rendered.addEventListener("click", (e) => {
      const a = e.target.closest ? e.target.closest("a") : null;
      const href = a && a.getAttribute("href");
      if (href && href.startsWith("#L")) { e.preventDefault(); setMode("source"); go(parseInt(href.slice(2), 10), true); }
    });
    modeBtn.hidden = false;
    let mode = "rendered";
    setMode(mode);
    modeBtn.addEventListener("click", () => { mode = mode === "rendered" ? "source" : "rendered"; setMode(mode); });
  } else {
    highlight(fromHash());
  }
})();
