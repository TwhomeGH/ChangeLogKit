/* 輕量語法上色（零依賴）：檔案檢視的逐行來源與 Markdown 程式碼區塊共用。

   設計重點：
   1) 無損：輸出 HTML 去掉標籤、還原實體後必須等於原字串（見 markdown.js 的排版檢視）。
   2) 語言感知：每種語言有自己的行註釋、區塊註釋、字串引號與關鍵字；
      不能拿 Swift 的 `//` 規則套到 PowerShell 的 `#`，也不能把 `http://…` 當成註釋。
   3) 進度保證：每個分支都必須前進，未知字元走單字元後備。 */
(function () {
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const span = (cls, text) => (cls ? `<span class="tok-${cls}">${esc(text)}</span>` : esc(text));

  /* 跨語言共用的關鍵字；各語言再追加自己的。 */
  const COMMON = new Set((
    "if else elif for while do switch case default break continue return function func fn def class struct " +
    "enum interface protocol extension implements extends new this self super import export from as is in of " +
    "not and or null nil true false try catch finally throw throws defer guard where var let const val type " +
    "alias public private protected internal static final abstract override async await yield lambda pass with " +
    "use namespace package module trait impl match when then fi done esac let mut ref pub crate dyn move loop " +
    "unsafe sizeof typedef union record"
  ).split(/\s+/));

  const SWIFT = new Set((
    "func var let class struct enum protocol extension init deinit subscript typealias associatedtype " +
    "import if else guard switch case default for while repeat return break continue throw throws rethrow " +
    "try catch defer do in where as is some any await async actor static self Self super nil true false " +
    "public private internal fileprivate open final override mutating nonmutating lazy weak unowned " +
    "indirect convenience required dynamic inout"
  ).split(/\s+/));

  const POWERSHELL = new Set((
    "param begin process end dynamicparam clean function filter workflow if elseif else switch foreach for " +
    "while do until try catch finally trap throw return break continue in class enum using hidden static " +
    "return default exit"
  ).split(/\s+/));

  /* 語言設定：每列註釋、區塊註釋 [開始, 結束]、字串引號、是否用 @／# 標記屬性。
     查不到就退回 C 風格（涵蓋 JS／Go／Rust 等多數語言）。 */
  const C_LIKE = {
    line: ["//"], block: [["/*", "*/"]], quotes: ['"', "'", "`"], attributes: false, keywords: COMMON,
  };
  const PROFILES = {
    swift: { line: ["//"], block: [["/*", "*/"]], quotes: ['"'], attributes: true, keywords: SWIFT },
    c: { line: ["//"], block: [["/*", "*/"]], quotes: ['"', "'"], attributes: true, keywords: COMMON },
    cpp: { line: ["//"], block: [["/*", "*/"]], quotes: ['"', "'"], attributes: true, keywords: COMMON },
    csharp: C_LIKE,
    java: C_LIKE, javascript: C_LIKE, typescript: C_LIKE, kotlin: C_LIKE, dart: C_LIKE, go: C_LIKE, rust: C_LIKE,
    json: { line: [], block: [], quotes: ['"'], attributes: false, keywords: COMMON },
    css: { line: [], block: [["/*", "*/"]], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    scss: { line: ["//"], block: [["/*", "*/"]], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    powershell: {
      line: ["#"], block: [["<#", "#>"]], quotes: ['"', "'"], attributes: false, keywords: POWERSHELL,
    },
    shell: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    python: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    ruby: { line: ["#"], block: [["=begin", "=end"]], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    perl: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    r: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    yaml: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    toml: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    ini: { line: ["#", ";"], block: [], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    dockerfile: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    makefile: { line: ["#"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    sql: { line: ["--"], block: [["/*", "*/"]], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    lua: { line: ["--"], block: [["--[[", "]]"]], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    haskell: { line: ["--"], block: [["{-", "-}"]], quotes: ['"'], attributes: false, keywords: COMMON },
    lisp: { line: [";"], block: [], quotes: ['"'], attributes: false, keywords: COMMON },
    clojure: { line: [";"], block: [], quotes: ['"'], attributes: false, keywords: COMMON },
    asm: { line: [";"], block: [], quotes: ['"', "'"], attributes: false, keywords: COMMON },
    html: { line: [], block: [["<!--", "-->"]], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    xml: { line: [], block: [["<!--", "-->"]], quotes: ['"', "'"], attributes: false, keywords: new Set() },
    vue: { line: ["//"], block: [["<!--", "-->"], ["/*", "*/"]], quotes: ['"', "'", "`"], attributes: false, keywords: COMMON },
    svelte: { line: ["//"], block: [["<!--", "-->"], ["/*", "*/"]], quotes: ['"', "'", "`"], attributes: false, keywords: COMMON },
  };

  /* 常見別名 → 語言設定。 */
  const ALIASES = {
    js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", mjs: "javascript", cjs: "javascript",
    py: "python", rb: "ruby", pl: "perl", rs: "rust", kt: "kotlin", cs: "csharp", sh: "shell", bash: "shell",
    zsh: "shell", console: "shell", ps1: "powershell", pwsh: "powershell", yml: "yaml", md: "markdown",
    markdown: "markdown", h: "c", hpp: "cpp", "c++": "cpp", golang: "go", docker: "dockerfile", make: "makefile",
    swiftinterface: "swift",
  };

  function profileOf(lang) {
    const key = String(lang || "").toLowerCase();
    /* 未指定語言時沿用舊行為（Swift）：開發索引的簽名區塊就是這樣呼叫 block()。 */
    if (!key) return PROFILES.swift;
    return PROFILES[ALIASES[key] || key] || C_LIKE;
  }

  /* 依副檔名或檔名推得語言（檔案檢視用）。 */
  function langFromPath(path) {
    const base = String(path || "").split("/").pop().toLowerCase();
    if (base === "dockerfile") return "dockerfile";
    if (base === "makefile" || base === "gnumakefile") return "makefile";
    const m = base.match(/\.([a-z0-9+]+)$/);
    return m ? m[1] : "";
  }

  /* 逐字掃描：區塊註釋（含跨行狀態）、行註釋、字串、屬性、數字、關鍵字、型別與呼叫。 */
  function scan(line, state, prof) {
    let out = "", i = 0;
    const n = line.length;
    while (i < n) {
      if (state.block) {
        const end = line.indexOf(state.block, i);
        if (end === -1) { out += span("c", line.slice(i)); return out; }
        out += span("c", line.slice(i, end + state.block.length));
        i = end + state.block.length;
        state.block = "";
        continue;
      }

      const block = prof.block.find((pair) => line.startsWith(pair[0], i));
      if (block) {
        const end = line.indexOf(block[1], i + block[0].length);
        if (end === -1) { out += span("c", line.slice(i)); state.block = block[1]; return out; }
        out += span("c", line.slice(i, end + block[1].length));
        i = end + block[1].length;
        continue;
      }

      const lineComment = prof.line.find((token) => line.startsWith(token, i));
      if (lineComment) { out += span("c", line.slice(i)); return out; }

      if (prof.quotes.includes(line[i])) {
        const quote = line[i];
        let j = i + 1;
        while (j < n) {
          if (line[j] === "\\") { j += 2; continue; }
          if (line[j] === quote) { j++; break; }
          j++;
        }
        out += span("s", line.slice(i, j));
        i = j;
        continue;
      }

      const c = line[i];
      if (prof.attributes && (c === "@" || c === "#")) {
        const m = line.slice(i).match(/^[@#][A-Za-z_]\w*/);
        if (m) { out += span("a", m[0]); i += m[0].length; continue; }
      }
      if (/[0-9]/.test(c) && !/[A-Za-z0-9_]/.test(line[i - 1] || "")) {
        const m = line.slice(i).match(/^0[xX][0-9A-Fa-f_]+|^0[bB][01_]+|^\d[\d_.eExX]*/);
        out += span("n", m[0]); i += m[0].length; continue;
      }
      if (/[A-Za-z_]/.test(c)) {
        const m = line.slice(i).match(/^[A-Za-z_]\w*/)[0];
        const isCall = /^\s*\(/.test(line.slice(i + m.length));
        const cls = prof.keywords.has(m) ? "k" : (/^[A-Z]/.test(m) ? "t" : (isCall ? "f" : ""));
        out += span(cls, m); i += m.length; continue;
      }

      /* 標點／空白：整個 alternation 都要錨定；否則 `\s+` 會從後面的空白開始匹配，
         讓 i 一次跳過中間被忽略的字元（曾造成 `/tools/forward-qu` 整段消失）。 */
      const m = line.slice(i).match(/^(?:[^\sA-Za-z0-9_@#"/]+|\s+)/);
      if (m) { out += esc(m[0]); i += m[0].length; } else { out += esc(c); i += 1; }
    }
    return out;
  }

  /* Swift 專用（保留舊介面；static_dev 等仍會呼叫）。 */
  function swift(line, state) {
    return scan(line, state || { block: "" }, PROFILES.swift);
  }

  /* 單行、可帶語言（檔案檢視用；state 需跨行保存區塊註釋）。 */
  function code(line, state, lang) {
    return scan(line, state || { block: "" }, profileOf(lang));
  }

  /* Markdown 逐行上色（原始碼檢視用）：標題、引言、行內程式碼與連結。
     只加色、不改字——上色輸出去掉標籤後必須等於原字串（否則會汙染下游用途，例如
     檔案檢視以逐行 textContent 取回 markdown 來源）。 */
  function markdownLine(line) {
    if (/^\s{0,3}#{1,6}\s/.test(line)) return span("k", line);
    if (/^\s{0,3}>\s?/.test(line)) return span("c", line);
    return esc(line)
      .replace(/`([^`]+)`/g, '<span class="tok-s">`$1`</span>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '[<span class="tok-t">$1</span>]($2)');
  }

  /* 整段程式碼上色：Markdown 用逐行；其餘依語言設定掃描。 */
  function block(text, lang) {
    const language = String(lang || "").toLowerCase();
    const lines = String(text).split("\n");
    if (language === "md" || language === "markdown") return lines.map(markdownLine).join("\n");
    const prof = profileOf(language);
    const state = { block: "" };
    return lines.map((line) => scan(line, state, prof)).join("\n");
  }

  window.HL = { swift, code, block, markdownLine, langFromPath, esc };
})();
