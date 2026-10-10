<template>
  <div class="app">
    <div class="lamp" aria-hidden="true"></div>

    <main class="desk">
      <!-- Masthead -->
      <header class="masthead">
        <p class="eyebrow">Retrieval-grounded Q&amp;A</p>
        <h1 class="title">Document Q&amp;A</h1>
        <p class="lede">
          Load a document and ask it anything. Every answer is traced back to
          the page it came from &mdash; nothing invented.
        </p>
      </header>

      <!-- Workspace -->
      <section class="workspace" aria-label="Document workspace">
        <!-- Load document -->
        <label
          class="dropzone"
          :class="{ 'is-dragging': isDragging, 'is-loaded': selectedFile }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <input
            ref="fileInput"
            class="visually-hidden"
            type="file"
            accept=".pdf"
            @change="handleFileChange"
          />
          <span class="drop-mark" aria-hidden="true">&#9671;</span>
          <span class="drop-text">
            <template v-if="selectedFile">{{ selectedFile.name }}</template>
            <template v-else>Drop a PDF here, or <u>browse</u></template>
          </span>
          <button
            v-if="selectedFile"
            type="button"
            class="drop-remove"
            @click.stop.prevent="removeFile"
            aria-label="Remove this file"
          >
            &times;
          </button>
          <span v-else class="drop-hint">PDF only</span>
        </label>

        <div class="load-row">
          <button
            class="btn btn-ghost"
            @click.prevent="uploadFile"
            :disabled="loadingUpload || !selectedFile"
          >
            {{ loadingUpload ? 'Indexing…' : 'Index document' }}
          </button>

          <p
            v-if="documentReady"
            class="status status-ok"
            aria-live="polite"
          >
            <span class="tick" aria-hidden="true"></span>
            {{ indexedName }} &middot; {{ indexedCount }} passages ready
          </p>
          <p
            v-else-if="uploadError"
            class="status status-err"
            aria-live="polite"
          >
            {{ uploadError }}
          </p>
        </div>

        <hr class="rule" />

        <!-- Ask -->
        <div class="ask-row">
          <input
            class="ask-input"
            v-model="question"
            type="text"
            placeholder="Ask anything about this document&hellip;"
            @keyup.enter="sendQuery"
            aria-label="Your question"
          />
          <button
            class="btn btn-accent"
            @click="sendQuery"
            :disabled="loadingQuery || !question.trim()"
          >
            <span v-if="loadingQuery" class="pulse" aria-hidden="true"></span>
            {{ loadingQuery ? 'Reading' : 'Ask' }}
          </button>
        </div>

        <div class="workspace-foot">
          <button
            type="button"
            class="link-btn"
            @click="clearIndex"
            :disabled="loadingClear"
          >
            {{ loadingClear ? 'Clearing…' : 'Start fresh' }}
          </button>
          <span class="foot-note">Removes all uploaded documents</span>
        </div>
      </section>

      <!-- Answer sheet -->
      <transition name="rise">
        <section v-if="response" class="sheet" key="answer" aria-live="polite">
          <p class="sheet-label">Answer</p>
          <p class="answer">{{ response.answer }}</p>

          <template v-if="response.sources && response.sources.length">
            <p class="sheet-label traced">
              Traced to <span class="count">{{ response.sources.length }}</span>
            </p>
            <ul class="clippings">
              <li
                v-for="(src, idx) in response.sources"
                :key="idx"
                class="clipping"
              >
                <span class="page">PAGE {{ pad(src.page) }}</span>
                <p class="excerpt">{{ src.content }}</p>
              </li>
            </ul>
          </template>
        </section>
      </transition>

      <!-- Empty state -->
      <section v-if="!response && !loadingQuery" class="empty" aria-hidden="true">
        <span class="empty-mark">&#167;</span>
        <p>
          Answers appear here as a sheet, with the passages they were drawn
          from clipped beneath.
        </p>
      </section>

      <footer class="colophon">
        FastAPI &middot; LangChain &middot; Gemini &middot; ChromaDB
      </footer>
    </main>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedFile: null,
      question: "",
      uploadError: "",
      indexedName: "",
      indexedCount: 0,
      documentReady: false,
      loadingUpload: false,
      loadingQuery: false,
      loadingClear: false,
      isDragging: false,
      response: null,
      apiBase: "http://localhost:8000",
    };
  },
  methods: {
    pad(n) {
      return String(n).padStart(2, "0");
    },
    handleFileChange(e) {
      this.selectedFile = e.target.files[0] || null;
      this.uploadError = "";
    },
    handleDrop(e) {
      this.isDragging = false;
      const file = e.dataTransfer.files[0];
      if (file && file.name.toLowerCase().endsWith(".pdf")) {
        this.selectedFile = file;
        this.uploadError = "";
      } else {
        this.uploadError = "That is not a PDF. Choose a .pdf file.";
      }
    },
    removeFile() {
      this.selectedFile = null;
      this.uploadError = "";
      if (this.$refs.fileInput) this.$refs.fileInput.value = "";
    },
    async clearIndex() {
      const ok = window.confirm(
        "Remove all uploaded documents and start over? This can't be undone."
      );
      if (!ok) return;
      this.loadingClear = true;
      try {
        const res = await fetch(`${this.apiBase}/reset`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Could not clear.");
        this.selectedFile = null;
        this.documentReady = false;
        this.indexedName = "";
        this.indexedCount = 0;
        this.response = null;
        this.question = "";
        this.uploadError = "";
        if (this.$refs.fileInput) this.$refs.fileInput.value = "";
      } catch (err) {
        this.uploadError = `Could not clear documents: ${err.message}`;
      } finally {
        this.loadingClear = false;
      }
    },
    async uploadFile() {
      if (!this.selectedFile) return;
      this.loadingUpload = true;
      this.uploadError = "";
      this.documentReady = false;
      const formData = new FormData();
      formData.append("file", this.selectedFile);

      try {
        const res = await fetch(`${this.apiBase}/upload`, {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Indexing failed.");
        this.indexedName = data.filename;
        this.indexedCount = data.chunks_indexed;
        this.documentReady = true;
      } catch (err) {
        this.uploadError = `Could not index this document: ${err.message}`;
      } finally {
        this.loadingUpload = false;
      }
    },
    async sendQuery() {
      if (!this.question.trim()) return;
      this.loadingQuery = true;
      try {
        const res = await fetch(`${this.apiBase}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: this.question }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Query failed.");
        this.response = data;
        this.question = "";
      } catch (err) {
        this.response = {
          answer: `Something went wrong reaching the document: ${err.message}`,
          sources: [],
        };
      } finally {
        this.loadingQuery = false;
      }
    },
  },
};
</script>

<style>
:root {
  --ground: #161924;
  --ground-2: #1e2230;
  --ground-inset: #12141c;
  --text: #ede9e0;
  --muted: #9a9db2;
  --accent: #e7a338;
  --accent-soft: rgba(231, 163, 56, 0.14);
  --paper: #f6f3ec;
  --paper-2: #fbf9f4;
  --paper-ink: #23252f;
  --paper-muted: #6e6f78;
  --line: rgba(237, 233, 224, 0.1);
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  background: var(--ground);
  color: var(--text);
  font-family: "Inter Tight", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.app {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Desk-lamp glow — the one atmospheric element */
.lamp {
  position: fixed;
  top: -28vh;
  left: 50%;
  width: 120vw;
  height: 80vh;
  transform: translateX(-50%);
  background: radial-gradient(
    ellipse at center,
    rgba(231, 163, 56, 0.1) 0%,
    rgba(231, 163, 56, 0.03) 35%,
    transparent 65%
  );
  pointer-events: none;
  z-index: 0;
}

.desk {
  position: relative;
  z-index: 1;
  max-width: 720px;
  margin: 0 auto;
  padding: 72px 24px 48px;
}

/* ---- Masthead ---- */
.masthead {
  margin-bottom: 40px;
}
.eyebrow {
  font-family: "Space Mono", monospace;
  font-size: 0.72rem;
  letter-spacing: 0.26em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 14px;
}
.title {
  font-family: "Fraunces", serif;
  font-optical-sizing: auto;
  font-weight: 600;
  font-size: clamp(3.2rem, 9vw, 5rem);
  line-height: 0.95;
  letter-spacing: -0.015em;
  margin: 0;
}
.lede {
  max-width: 44ch;
  margin: 18px 0 0;
  font-size: 1.05rem;
  line-height: 1.55;
  color: var(--muted);
}

/* ---- Workspace ---- */
.workspace {
  background: var(--ground-2);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 24px 60px -30px rgba(0, 0, 0, 0.7);
}

.dropzone {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 18px;
  border: 1.5px dashed rgba(237, 233, 224, 0.2);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}
.dropzone:hover {
  border-color: rgba(231, 163, 56, 0.5);
}
.dropzone.is-dragging {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.dropzone.is-loaded {
  border-style: solid;
  border-color: rgba(231, 163, 56, 0.4);
}
.drop-mark {
  font-size: 1.2rem;
  color: var(--accent);
}
.drop-text {
  flex: 1;
  font-size: 0.98rem;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drop-text u {
  text-decoration-color: var(--accent);
  text-underline-offset: 3px;
}
.drop-hint {
  font-family: "Space Mono", monospace;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  color: var(--muted);
}
.drop-remove {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 50%;
  background: rgba(237, 233, 224, 0.08);
  color: var(--muted);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
}
.drop-remove:hover {
  background: rgba(231, 138, 122, 0.18);
  color: #e78a7a;
}

.load-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.status {
  font-family: "Space Mono", monospace;
  font-size: 0.78rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-ok {
  color: var(--text);
}
.status-err {
  color: #e78a7a;
}
.tick {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-soft);
}

.rule {
  border: none;
  border-top: 1px solid var(--line);
  margin: 22px 0;
}

/* ---- Ask ---- */
.ask-row {
  display: flex;
  gap: 10px;
}
.ask-input {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  font-family: inherit;
  font-size: 1rem;
  color: var(--text);
  background: var(--ground-inset);
  border: 1px solid var(--line);
  border-radius: 10px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.ask-input::placeholder {
  color: var(--muted);
}
.ask-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* ---- Workspace footer ---- */
.workspace-foot {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--muted);
  transition: color 0.16s ease;
}
.link-btn:hover:not(:disabled) {
  color: #e78a7a;
}
.link-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.link-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 3px;
}
.foot-note {
  font-family: "Space Mono", monospace;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  color: rgba(154, 157, 178, 0.6);
}

/* ---- Buttons ---- */
.btn {
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  padding: 13px 22px;
  cursor: pointer;
  transition: transform 0.12s ease, opacity 0.18s ease, background 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  white-space: nowrap;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn:not(:disabled):hover {
  transform: translateY(-1px);
}
.btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.btn-accent {
  background: var(--accent);
  color: #2a1c05;
}
.btn-accent:not(:disabled):hover {
  background: #f0b149;
}
.btn-ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid rgba(237, 233, 224, 0.22);
}
.btn-ghost:not(:disabled):hover {
  border-color: var(--accent);
  color: var(--accent);
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2a1c05;
  animation: pulse 0.9s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: scale(0.7);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* ---- Answer sheet ---- */
.sheet {
  margin-top: 28px;
  background: var(--paper);
  color: var(--paper-ink);
  border-radius: 14px;
  padding: 32px 30px;
  box-shadow: 0 30px 70px -32px rgba(0, 0, 0, 0.8);
}
.sheet-label {
  font-family: "Space Mono", monospace;
  font-size: 0.68rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--paper-muted);
  margin: 0 0 12px;
}
.sheet-label.traced {
  margin-top: 30px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.count {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  background: var(--accent);
  color: #2a1c05;
  border-radius: 6px;
  font-size: 0.72rem;
}
.answer {
  font-family: "Fraunces", serif;
  font-optical-sizing: auto;
  font-weight: 400;
  font-size: 1.3rem;
  line-height: 1.5;
  margin: 0;
  letter-spacing: -0.003em;
}

.clippings {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}
.clipping {
  position: relative;
  background: var(--paper-2);
  border: 1px solid rgba(35, 37, 47, 0.08);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  padding: 14px 16px;
}
.page {
  font-family: "Space Mono", monospace;
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  color: var(--accent);
  font-weight: 700;
}
.excerpt {
  margin: 6px 0 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #44454e;
}

/* ---- Empty state ---- */
.empty {
  margin-top: 28px;
  padding: 36px 30px;
  border: 1px dashed var(--line);
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 18px;
  color: var(--muted);
}
.empty-mark {
  font-family: "Fraunces", serif;
  font-size: 2.4rem;
  color: rgba(231, 163, 56, 0.55);
  line-height: 1;
}
.empty p {
  margin: 0;
  max-width: 42ch;
  line-height: 1.55;
  font-size: 0.98rem;
}

.colophon {
  margin-top: 40px;
  text-align: center;
  font-family: "Space Mono", monospace;
  font-size: 0.68rem;
  letter-spacing: 0.16em;
  color: rgba(154, 157, 178, 0.6);
}

/* ---- Motion ---- */
.rise-enter-active {
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.rise-enter-from {
  opacity: 0;
  transform: translateY(14px);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  .rise-enter-active {
    transition: opacity 0.3s ease;
  }
  .rise-enter-from {
    transform: none;
  }
  .btn:not(:disabled):hover {
    transform: none;
  }
  .pulse {
    animation: none;
  }
}

@media (max-width: 560px) {
  .desk {
    padding: 48px 18px 40px;
  }
  .ask-row {
    flex-direction: column;
  }
  .btn-accent {
    justify-content: center;
  }
}
</style>
