/* 極簡 Markdown 渲染（零依賴）：標題、清單（含巢狀）、表格、程式碼區塊、引言與 GitHub 提示框。
   相對連結一律經 resolve 改寫；統一的解析器由 markdownResolver（動態）／
   markdownStaticResolver（靜態）提供，所有渲染點共用，避免各處連結行為不一致。 */
(function () {
  const esc = (s) => window.HL.esc(s);

  const ALERTS = {
    note: { label: "注意", icon: "\u2139\uFE0F" },
    tip: { label: "提示", icon: "\uD83D\uDCA1" },
    important: { label: "重要", icon: "\u2757" },
    warning: { label: "警告", icon: "\u26A0\uFE0F" },
    caution: { label: "小心", icon: "\uD83D\uDD25" },
  };

  /* 行內語法：程式碼、粗體、斜體、刪除線、圖片、連結。 */
  function inline(text, resolve) {
    let s = esc(text);
    s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<img alt="$1" src="$2" loading="lazy">');
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)[^)]*\)/g,
      (_m, label, href) => `<a href="${esc(resolve(href))}">${label}</a>`);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
    s = s.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    return s;
  }

  function splitRow(line) {
    return line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  }
  function table(header, rows, resolve) {
    const head = "<tr>" + header.map((c) => `<th>${inline(c, resolve)}</th>`).join("") + "</tr>";
    const body = rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c, resolve)}</td>`).join("") + "</tr>").join("");
    return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
  }

  /* 以縮排把清單項目組成樹，再遞迴輸出巢狀 ul/ol。 */
  function listHtml(items, resolve) {
    const root = { ordered: items[0].ordered, text: "", children: [] };
    const stack = [root];
    for (const it of items) {
      while (stack.length > 1 && it.indent <= stack[stack.length - 1].indent) stack.pop();
      const node = { ordered: it.ordered, text: it.text, indent: it.indent, children: [] };
      stack[stack.length - 1].children.push(node);
      stack.push(node);
    }
    const emit = (node) => {
      const tag = node.ordered ? "ol" : "ul";
      return `<${tag}>` + node.children.map((c) =>
        `<li>${inline(c.text, resolve)}${c.children.length ? emit(c) : ""}</li>`).join("") + `</${tag}>`;
    };
    return emit(root);
  }

  /* 標題 anchor：由純文字產生穩定 id；同一份文件重複標題自動加序號。 */
  function headingId(text, ids) {
    const plain = String(text)
      .replace(/`([^`]*)`/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/[*_~]/g, "")
      .trim();
    const base = plain.toLowerCase().replace(/[^\w\u00C0-\uFFFF]+/g, "-").replace(/^-+|-+$/g, "") || "section";
    let id = base, n = 2;
    while (ids.has(id)) { id = base + "-" + n; n++; }
    ids.add(id);
    return id;
  }

  /* 引言；若首行為 [!TYPE] 則輸出提示框，其餘內容照 markdown 渲染。 */
  function quote(lines, resolve, ids) {
    const alert = lines[0] && lines[0].match(/^\s*\[!(\w+)\]\s*(.*)$/);
    if (alert && ALERTS[alert[1].toLowerCase()]) {
      const meta = ALERTS[alert[1].toLowerCase()];
      const title = alert[2].trim() || meta.label;
      const body = render(lines.slice(1).join("\n"), resolve, ids);
      return `<div class="alert alert-${alert[1].toLowerCase()}">` +
        `<p class="alert-title"><span class="alert-icon">${meta.icon}</span>${inline(title, resolve)}</p>${body}</div>`;
    }
    return `<blockquote>${render(lines.join("\n"), resolve, ids)}</blockquote>`;
  }

  const isBlockStart = (line, next) => {
    if (!line.trim()) return true;
    if (/^\s{0,3}(#{1,6}\s|```|>)/.test(line)) return true;
    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) return true;
    if (/^(\s*)([-*+]|\d+[.)])\s+/.test(line)) return true;
    if (line.includes("|") && next && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(next)) return true;
    return false;
  };

  function render(text, resolve, ids) {
    const seen = ids || new Set();
    const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];

      const fence = line.match(/^\s*```(\S+)?\s*$/);
      if (fence) {
        const lang = fence[1] || "";
        const buf = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) { buf.push(lines[i]); i++; }
        i++;
        out.push(`<pre class="code"><code>${window.HL.block(buf.join("\n"), lang)}</code></pre>`);
        continue;
      }

      const heading = line.match(/^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/);
      if (heading) {
        const l = heading[1].length;
        const id = headingId(heading[2], seen);
        out.push(`<h${l} id="${esc(id)}">${inline(heading[2], resolve)}</h${l}>`);
        i++; continue;
      }

      if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) { out.push("<hr>"); i++; continue; }

      if (line.includes("|") && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
        const header = splitRow(line);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes("|") && lines[i].trim()) { rows.push(splitRow(lines[i])); i++; }
        out.push(table(header, rows, resolve));
        continue;
      }

      if (/^\s{0,3}>/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s{0,3}>/.test(lines[i])) { buf.push(lines[i].replace(/^\s{0,3}>\s?/, "")); i++; }
        out.push(quote(buf, resolve, seen));
        continue;
      }

      const item = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (item) {
        const items = [];
        while (i < lines.length) {
          const m = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
          if (!m) break;
          items.push({ indent: m[1].replace(/\t/g, "  ").length, ordered: /\d/.test(m[2]), text: m[3] });
          i++;
        }
        out.push(listHtml(items, resolve));
        continue;
      }

      if (!line.trim()) { i++; continue; }

      const para = [line];
      i++;
      while (i < lines.length && !isBlockStart(lines[i], lines[i + 1])) { para.push(lines[i]); i++; }
      out.push(`<p>${inline(para.join(" "), resolve)}</p>`);
    }
    return out.join("\n");
  }

  const IDENTITY = (href) => href;

  window.renderMarkdown = (text, resolveHref) =>
    render(text, typeof resolveHref === "function" ? resolveHref : IDENTITY, new Set());

  /* 把容器內的 h2–h4 建成目錄（h1 是頁面標題，h5+ 太細）；少於兩項就隱藏。 */
  window.renderTOC = function (content, nav, panel) {
    if (!content || !nav) return false;
    const heads = [...content.querySelectorAll("h2, h3, h4")].filter((h) => h.id);
    nav.textContent = "";
    if (heads.length < 2) {
      if (panel) panel.hidden = true;
      return false;
    }
    for (const h of heads) {
      const a = document.createElement("a");
      a.className = "toc-h" + h.tagName[1];
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      nav.append(a);
    }
    if (panel) panel.hidden = false;
    return true;
  };

  /* 手機目錄抽屜的開關；桌面由 CSS 固定顯示側欄。 */
  window.bindTOC = function (panel, btn, close) {
    if (!panel || !btn) return;
    const expanded = () => document.body.classList.contains("toc-open");
    const setOpen = (open) => {
      document.body.classList.toggle("toc-open", open);
      btn.setAttribute("aria-expanded", String(open));
    };
    btn.addEventListener("click", () => setOpen(!expanded()));
    if (close) close.addEventListener("click", () => setOpen(false));
    panel.addEventListener("click", (e) => {
      const link = e.target.closest ? e.target.closest("a") : null;
      if (link) setOpen(false);
    });
    addEventListener("resize", () => {
      if (innerWidth >= 1100) setOpen(false);   /* 回到桌面版時收起抽屜 */
    });
  };

  /* 目前章節高亮（scroll-spy）：scroller 省略時監聽視窗；動態檔檢視傳入 .wrap。 */
  window.watchTOC = function (content, nav, scroller) {
    const links = [...nav.querySelectorAll('a[href^="#"]')];
    if (!links.length) return;
    const appbar = document.querySelector(".appbar");
    let frame = 0;
    const update = () => {
      frame = 0;
      const offset = (appbar ? appbar.getBoundingClientRect().bottom : 0) + 12;
      let active = links[0];
      for (const link of links) {
        const id = link.getAttribute("href").slice(1);
        const head = document.getElementById(id);
        if (!head) continue;
        if (head.getBoundingClientRect().top <= offset) active = link;
        else break;
      }
      const box = scroller || document.scrollingElement || document.documentElement;
      if (box && box.scrollHeight - box.scrollTop - box.clientHeight < 8) {
        active = links[links.length - 1];
      }
      links.forEach((link) => {
        const on = link === active;
        link.classList.toggle("active", on);
        if (on) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    (scroller || window).addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    update();
  };

  /* ── 連結解析：所有渲染點共用的唯一來源 ─────────────────────
     依「來源文件」把相對連結改寫成站內連結。

     repo     來源名稱；docPath 來源文件在 repo 內的相對路徑（推得相對基準目錄）。
     options.baseDir  直接指定基準目錄（覆寫由 docPath 推得者）。
     options.staticMap 靜態站：{ base, docs, blob }
       - base：相對站根的前綴（"" 或 "../"…）
       - docs：{ "來源:文件相對路徑" → 站內文件頁相對路徑 }
       - blob：GitHub blob 前綴；比對不到文件頁時改用
     動態：相對路徑 → /development/file?repo=…&path=…（與檔案檢視一致）。 */
  window.markdownResolver = function (repo, docPath, options) {
    const opts = options || {};
    const baseDir = typeof opts.baseDir === "string"
      ? opts.baseDir
      : String(docPath || "").split("/").slice(0, -1).join("/");
    return function (href) {
      const raw = String(href == null ? "" : href);
      if (/^[a-z][a-z0-9+.-]*:/i.test(raw) || raw.startsWith("#") || raw.startsWith("/")) return raw;
      const [clean, ...rest] = raw.split("#");
      const parts = baseDir ? baseDir.split("/") : [];
      for (const seg of clean.split("/")) {
        if (seg === "" || seg === ".") continue;
        if (seg === "..") { parts.pop(); continue; }
        parts.push(seg);
      }
      const name = parts.join("/");
      const anchor = rest.length ? "#" + rest.join("#") : "";
      const map = opts.staticMap;
      if (map) {
        const key = repo ? repo + ":" + name : name;
        if (map.docs && Object.prototype.hasOwnProperty.call(map.docs, key)) {
          return (map.base || "") + map.docs[key] + anchor;
        }
        if (map.docs && Object.prototype.hasOwnProperty.call(map.docs, name)) {
          return (map.base || "") + map.docs[name] + anchor;
        }
        if (map.blob) return map.blob + name + anchor;
        return raw;
      }
      return "/development/file?" + new URLSearchParams({ repo: repo || "app", path: name }).toString() + anchor;
    };
  };

  /* 靜態站用的解析器；來源可由參數或 window.CK_DOC_REPO 指定。 */
  window.markdownStaticResolver = function (docPath, docRepo) {
    return window.markdownResolver(docRepo || window.CK_DOC_REPO || "", docPath, {
      staticMap: {
        base: window.CK_SITE_BASE || "",
        docs: window.CK_DOC_PAGES || {},
        blob: window.CK_BLOB_BASE || null,
      },
    });
  };

  /* i18n：優先取 CK_T，沒有就回退字串。 */
  function T(key, fallback) {
    const v = typeof window.CK_T === "function" ? window.CK_T(key) : "";
    return v && v !== key ? v : fallback;
  }

  /* 把標籤行（@tag …）與其續行收成一串 {tag, text}。 */
  function parseTags(lines) {
    const tags = [];
    let cur = null;
    for (const raw of lines) {
      const m = raw.match(/^\s*@(\w+)\b\s*([\s\S]*)$/);
      if (m) { cur = { tag: m[1].toLowerCase(), text: m[2].trim() }; tags.push(cur); }
      else if (cur && raw.trim()) { cur.text += (cur.text ? " " : "") + raw.trim(); }
    }
    return tags;
  }

  /* 由字串開頭的 {…} 取型別（支援巢狀大括號，如 {{post: Function}}）。 */
  function splitType(text) {
    const s = String(text == null ? "" : text).trim();
    if (s[0] !== "{") return { type: "", rest: s };
    let depth = 0;
    for (let i = 0; i < s.length; i++) {
      if (s[i] === "{") depth++;
      else if (s[i] === "}") { depth--; if (depth === 0) return { type: s.slice(1, i).trim(), rest: s.slice(i + 1).trim() }; }
    }
    return { type: "", rest: s };
  }

  /* 解析 JSDoc 形式的「{型別} 名稱 說明」。 */
  function parseParam(text) {
    const first = splitType(text);
    const rest = first.rest;
    const nm = rest.match(/^(\[?[\w.$]+\]?)\s*([\s\S]*)$/);
    return { type: first.type, name: nm ? nm[1] : "", desc: nm ? nm[2].trim() : rest };
  }

  /* JSDoc 風格註釋渲染：描述用 markdown；@param／@returns／其他標籤整理成結構。
     沒有標籤時退回 renderMarkdown（向後相容，Swift／Python 等註釋不受影響）。 */
  function renderDoc(text, resolveHref) {
    const resolve = typeof resolveHref === "function" ? resolveHref : IDENTITY;
    const lines = String(text == null ? "" : text).split("\n");
    const start = lines.findIndex((l) => /^\s*@\w+/.test(l));
    if (start === -1) return render(text, resolve);
    const desc = lines.slice(0, start).join("\n").trim();
    const tags = parseTags(lines.slice(start));
    let html = "";
    if (desc) html += `<div class="doc-desc">${render(desc, resolve)}</div>`;
    const params = tags.filter((t) => t.tag === "param").map((t) => parseParam(t.text));
    if (params.length) {
      html += '<table class="docparams"><thead><tr>' +
        `<th>${esc(T("dev.p_name", "Parameter"))}</th>` +
        `<th>${esc(T("dev.p_type", "Type"))}</th>` +
        `<th>${esc(T("dev.p_desc", "Description"))}</th></tr></thead><tbody>` +
        params.map((p) => `<tr><td><code>${esc(p.name)}</code></td>` +
          `<td>${p.type ? `<code>${esc(p.type)}</code>` : ""}</td>` +
          `<td>${inline(p.desc, resolve)}</td></tr>`).join("") + "</tbody></table>";
    }
    const ret = tags.find((t) => t.tag === "return" || t.tag === "returns");
    if (ret) {
      const r = parseParam(ret.text);
      html += `<p class="docreturns"><span class="lbl">${esc(T("dev.returns", "Returns"))}</span> ` +
        (r.type ? `<code>${esc(r.type)}</code> ` : "") + inline(r.desc || r.name, resolve) + "</p>";
    }
    const others = tags.filter((t) => !["param", "return", "returns"].includes(t.tag));
    if (others.length) {
      html += others.map((t) => `<div class="doctag"><span class="lbl">@${esc(t.tag)}</span>${inline(t.text, resolve)}</div>`).join("");
    }
    return html || render(text, resolve);
  }

  window.renderDoc = renderDoc;
})();
