const source = document.getElementById("source");
const output = document.getElementById("output");
const preview = document.getElementById("preview");
const notes = document.getElementById("notes");
const status = document.getElementById("status");
const sourceName = document.getElementById("source-name");
const downloadBtn = document.getElementById("download");
const fileInput = document.getElementById("file");

const SAMPLE = `Getting started with backyard compost
=====================================

#### Why it matters

Kitchen scraps don't have to go in the trash.  They become soil.

![ ](bin-setup.png)

## tools
- bucket
* pitchfork

#### Common mistakes
Leaving the pile too dry. Turn it weekly.
`;

source.value = SAMPLE;

let lastMarkdown = "";
let lastName = "untitled.md";

function basename(name) {
  return name.replace(/\\/g, "/").split("/").pop() || "untitled.md";
}

function renderNotes(warnings, issues) {
  const lines = [];
  for (const issue of issues || []) {
    lines.push(`<p class="fail">issue: ${escapeHtml(issue)}</p>`);
  }
  for (const warning of warnings || []) {
    lines.push(`<p class="warn">warning: ${escapeHtml(warning)}</p>`);
  }
  if (!lines.length) {
    lines.push('<p class="ok">Publish-ready. No remaining required-field gaps.</p>');
  }
  notes.innerHTML = lines.join("");
  notes.hidden = false;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function splitPreview(markdown) {
  if (markdown.startsWith("---")) {
    const end = markdown.indexOf("\n---", 3);
    if (end !== -1) {
      return markdown.slice(end + 4).replace(/^\s+/, "");
    }
  }
  return markdown;
}

async function polish(event) {
  event.preventDefault();
  status.textContent = "Polishing…";
  downloadBtn.disabled = true;
  try {
    const response = await fetch("/api/polish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        markdown: source.value,
        preset: document.getElementById("preset").value,
        ai: document.getElementById("ai").checked,
        toc: document.getElementById("toc").checked,
        site_url: document.getElementById("site-url").value || null,
      }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || response.statusText);
    }
    const data = await response.json();
    lastMarkdown = data.markdown;
    output.textContent = data.markdown;
    preview.classList.remove("empty");
    preview.innerHTML = marked.parse(splitPreview(data.markdown));
    renderNotes(data.warnings, data.issues);
    const slug = data.frontmatter.slug || data.frontmatter.permalink || lastName;
    lastName = String(slug)
      .replaceAll("/", "")
      .replace(/\.md$/i, "");
    lastName = `${lastName || "untitled"}.md`;
    status.textContent = data.issues?.length ? "Needs fields" : "Publish-ready";
    downloadBtn.disabled = false;
  } catch (error) {
    status.textContent = "Failed";
    notes.hidden = false;
    notes.innerHTML = `<p class="fail">${escapeHtml(error.message)}</p>`;
  }
}

document.getElementById("controls").addEventListener("submit", polish);

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (!file) {
    return;
  }
  source.value = await file.text();
  lastName = basename(file.name);
  sourceName.textContent = lastName;
});

downloadBtn.addEventListener("click", () => {
  if (!lastMarkdown) {
    return;
  }
  const blob = new Blob([lastMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = lastName;
  link.click();
  URL.revokeObjectURL(url);
});
