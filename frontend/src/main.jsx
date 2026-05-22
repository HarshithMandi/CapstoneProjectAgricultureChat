import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Check,
  Database,
  History,
  Loader2,
  LogOut,
  MessageCircle,
  Pencil,
  Search,
  Settings,
  Shield,
  Sprout,
  Trash2,
  UserCog,
  Users,
  Upload,
  X,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const GREETING = "Hi! Do you have any agriculture-related questions you'd like help with?";

const ROUTES = {
  login: "/login",
  register: "/register",
  adminSetup: "/admin-setup",
  chat: "/chat",
  ingest: "/ingest",
  search: "/search",
  users: "/users",
  settings: "/settings",
};

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function useRoute() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  return path;
}

async function request(endpoint, { method = "GET", body, token, signal } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail || response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return data;
}

async function requestMultipart(endpoint, { method = "POST", formData, token, signal } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: formData,
    signal,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail || response.statusText;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return data;
}

function App() {
  const route = useRoute();
  const [token, setToken] = useState(() => localStorage.getItem("agri_token"));
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("agri_user");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem("agri_user");
      return null;
    }
  });
  const [authChecked, setAuthChecked] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessionListVersion, setSessionListVersion] = useState(0);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    let cancelled = false;

    async function refreshUser() {
      if (!token) {
        setAuthChecked(true);
        return;
      }

      try {
        const freshUser = await request("/auth/me", { token });
        if (cancelled) return;
        localStorage.setItem("agri_user", JSON.stringify(freshUser));
        setUser(freshUser);
      } catch {
        if (cancelled) return;
        localStorage.removeItem("agri_token");
        localStorage.removeItem("agri_user");
        setToken(null);
        setUser(null);
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    }

    setAuthChecked(false);
    refreshUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!authChecked) return;

    const allowedRoutes = isAdmin
      ? ["/chat", "/ingest", "/search", "/users", "/settings"]
      : ["/chat", "/settings"];

    if (!token || !user) {
      if (!["/login", "/register", "/admin-setup"].includes(route)) navigate("/login");
      return;
    }

    if (["/", "/login", "/register", "/admin-setup"].includes(route)) navigate("/chat");
    if (!isAdmin && ["/ingest", "/search", "/users"].includes(route)) navigate("/chat");
    if (!allowedRoutes.includes(route)) navigate("/chat");
  }, [authChecked, token, user, route, isAdmin]);

  function onAuth(result) {
    localStorage.setItem("agri_token", result.access_token);
    localStorage.setItem("agri_user", JSON.stringify(result.user));
    setToken(result.access_token);
    setUser(result.user);
    navigate("/chat");
  }

  function logout() {
    localStorage.removeItem("agri_token");
    localStorage.removeItem("agri_user");
    setToken(null);
    setUser(null);
    setActiveSessionId(null);
    navigate("/login");
  }

  function onSessionChanged(sessionId) {
    setActiveSessionId(sessionId);
    setSessionListVersion((version) => version + 1);
  }

  if (!authChecked) {
    return (
      <main className="loading-screen">
        <Loader2 size={24} />
        <span>Loading dashboard...</span>
      </main>
    );
  }

  if (!token || !user) {
    return <AuthShell route={route} onAuth={onAuth} />;
  }

  return (
    <DashboardShell
      user={user}
      token={token}
      onLogout={logout}
      route={route}
      activeSessionId={activeSessionId}
      onSelectSession={(sessionId) => {
        setActiveSessionId(sessionId);
        navigate("/chat");
      }}
      onSessionsMutated={() => setSessionListVersion((version) => version + 1)}
      sessionListVersion={sessionListVersion}
    >
      {route === "/chat" && <ChatPage token={token} activeSessionId={activeSessionId} onSessionChanged={onSessionChanged} />}
      {route === "/ingest" && isAdmin && <IngestPage token={token} />}
      {route === "/search" && isAdmin && <SearchPage token={token} />}
      {route === "/users" && isAdmin && <UsersPage token={token} currentUser={user} />}
      {route === "/settings" && <SettingsPage />}
    </DashboardShell>
  );
}

function AuthShell({ route, onAuth }) {
  const [adminSetup, setAdminSetup] = useState({ loading: true, available: false });
  const mode = route === "/admin-setup" ? "admin-setup" : route === "/register" ? "register" : "login";

  useEffect(() => {
    let cancelled = false;
    request("/auth/admin-setup/status")
      .then((result) => {
        if (!cancelled) setAdminSetup({ loading: false, available: !result.has_admin });
      })
      .catch(() => {
        if (!cancelled) setAdminSetup({ loading: false, available: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!adminSetup.loading && mode === "admin-setup" && !adminSetup.available) {
      navigate("/login");
    }
  }, [adminSetup, mode]);

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <div className="brand-lockup">
          <div className="brand-mark"><Sprout size={26} /></div>
          <div>
            <h1>Agri RAG Assistant</h1>
            <p>Secure agricultural assistance powered by your knowledge base.</p>
          </div>
        </div>

        <div className="tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => navigate("/login")}>Login</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => navigate("/register")}>Create Account</button>
        </div>

        {adminSetup.available && mode !== "admin-setup" && (
          <div className="setup-callout">
            <Shield size={20} />
            <div>
              <strong>No admin account exists</strong>
              <span>Create one to unlock the admin dashboard.</span>
            </div>
            <button type="button" onClick={() => navigate("/admin-setup")}>Create Admin</button>
          </div>
        )}

        {mode === "login" && <LoginForm onAuth={onAuth} />}
        {mode === "register" && <RegisterForm onAuth={onAuth} />}
        {mode === "admin-setup" && <RegisterForm onAuth={onAuth} adminSetup />}
      </section>
    </main>
  );
}

function LoginForm({ onAuth }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      onAuth(await request("/auth/login", { method: "POST", body: form }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <Field label="Email" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} />
      <Field label="Password" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} />
      {error && <div className="error">{error}</div>}
      <button className="primary-button" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
    </form>
  );
}

function RegisterForm({ onAuth, adminSetup = false }) {
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = adminSetup ? "/auth/admin-setup" : "/auth/register";
      onAuth(await request(endpoint, { method: "POST", body: { ...form, full_name: form.full_name || null } }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="form-stack" onSubmit={submit}>
      <Field label="Full name" value={form.full_name} onChange={(full_name) => setForm({ ...form, full_name })} />
      <Field label="Email" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} />
      <Field label="Password" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} />
      <p className="hint">
        {adminSetup
          ? "This creates the admin account for managing users, ingestion, and search."
          : "Standard accounts can chat with the assistant. Admin access is created separately when no admin exists."}
      </p>
      {error && <div className="error">{error}</div>}
      <button className="primary-button" disabled={loading}>
        {loading ? "Creating..." : adminSetup ? "Create Admin Account" : "Create Account"}
      </button>
    </form>
  );
}

function DashboardShell({ user, token, onLogout, route, children, activeSessionId, onSelectSession, onSessionsMutated, sessionListVersion }) {
  const nav = [
    { path: "/chat", label: "Chat", icon: MessageCircle },
    ...(user.role === "admin"
      ? [
          { path: "/ingest", label: "Ingest Data", icon: Database },
          { path: "/search", label: "Search", icon: Search },
          { path: "/users", label: "Manage Users", icon: Users },
        ]
      : []),
    { path: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Sprout size={26} />
          <span>Agri RAG</span>
        </div>
        <div className="user-chip">
          <Shield size={16} />
          <div>
            <strong>{user.email}</strong>
            <span>{user.role}</span>
          </div>
        </div>
        <nav>
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.path} className={route === item.path ? "active" : ""} onClick={() => navigate(item.path)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <SessionHistory
          token={token}
          route={route}
          activeSessionId={activeSessionId}
          onSelectSession={onSelectSession}
          onSessionsMutated={onSessionsMutated}
          refreshKey={sessionListVersion}
        />
        <button className="logout-button" onClick={onLogout}>
          <LogOut size={18} />
          Logout
        </button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

function SessionHistory({ token, route, activeSessionId, onSelectSession, onSessionsMutated, refreshKey }) {
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [draftTitle, setDraftTitle] = useState("");

  async function loadSessions() {
    setError("");
    try {
      setSessions(await request("/chat/sessions", { token }));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadSessions();
  }, [token, refreshKey]);

  async function renameSession(sessionId) {
    const title = draftTitle.trim();
    if (!title) {
      setError("Session name cannot be empty.");
      return;
    }

    try {
      setError("");
      await request(`/chat/sessions/${sessionId}`, { method: "PATCH", body: { title }, token });
      setEditingId(null);
      await loadSessions();
      onSessionsMutated();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm("Delete this session and its saved messages?")) return;

    try {
      setError("");
      await request(`/chat/sessions/${sessionId}`, { method: "DELETE", token });
      if (sessionId === activeSessionId) onSelectSession(null);
      await loadSessions();
      onSessionsMutated();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="session-history">
      <div className="sidebar-section-title">
        <History size={16} />
        <span>Sessions</span>
      </div>
      <button className={!activeSessionId && route === "/chat" ? "active" : ""} onClick={() => onSelectSession(null)}>
        New chat
      </button>
      <div className="session-list">
        {sessions.map((session) => {
          const id = getSessionId(session);
          const title = session.title || "Untitled chat";
          const isEditing = editingId === id;
          return (
            <div key={id} className={`session-row ${id === activeSessionId ? "active" : ""}`}>
              {isEditing ? (
                <>
                  <input
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") renameSession(id);
                      if (event.key === "Escape") setEditingId(null);
                    }}
                    autoFocus
                  />
                  <button className="icon-button" title="Save session name" onClick={() => renameSession(id)}>
                    <Check size={15} />
                  </button>
                  <button className="icon-button" title="Cancel rename" onClick={() => setEditingId(null)}>
                    <X size={15} />
                  </button>
                </>
              ) : (
                <>
                  <button className="session-select" onClick={() => onSelectSession(id)} title={title}>
                    <span>{title}</span>
                    <small>{formatSessionDate(session.updated_at || session.created_at)}</small>
                  </button>
                  <button
                    className="icon-button"
                    title="Rename session"
                    onClick={() => {
                      setEditingId(id);
                      setDraftTitle(title);
                    }}
                  >
                    <Pencil size={15} />
                  </button>
                  <button className="icon-button danger" title="Delete session" onClick={() => deleteSession(id)}>
                    <Trash2 size={15} />
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>
      {error && <small className="sidebar-error">{error}</small>}
    </section>
  );
}

function ChatPage({ token, activeSessionId, onSessionChanged }) {
  const [sessionId, setSessionId] = useState(activeSessionId);
  const [messages, setMessages] = useState([{ role: "assistant", content: GREETING }]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState("");
  const sendingRef = useRef(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
    setError("");
    setLoading(false);
    sendingRef.current = false;
      if (!activeSessionId) {
        setSessionId(null);
        setMessages([{ role: "assistant", content: GREETING }]);
        return;
      }

      try {
        const session = await request(`/chat/sessions/${activeSessionId}`, { token });
        if (cancelled) return;
        setSessionId(getSessionId(session));
        setMessages(normalizeSessionMessages(session.messages));
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
      }
    }

    loadSession();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, token]);

  function newSession() {
    setSessionId(null);
    setMessages([{ role: "assistant", content: GREETING }]);
    setError("");
    setUploadStatus(null);
    onSessionChanged(null);
  }

  async function ensureSession() {
    if (sessionId) return sessionId;
    const session = await request("/chat/sessions", { method: "POST", body: {}, token });
    const id = session.id || session._id;
    setSessionId(id);
    return id;
  }

  async function uploadPdfFiles(files) {
    const pdfFiles = Array.from(files || []).filter((file) => {
      const name = (file?.name || "").toLowerCase();
      const type = (file?.type || "").toLowerCase();
      return type === "application/pdf" || name.endsWith(".pdf");
    });

    if (!pdfFiles.length) {
      setUploadStatus({ type: "error", message: "Please upload PDF files only." });
      return;
    }

    setUploading(true);
    setDragActive(false);
    setUploadStatus(null);
    setError("");

    try {
      const currentSessionId = await ensureSession();
      let uploadedCount = 0;
      let chunkCount = 0;

      for (const file of pdfFiles) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", file.name.replace(/\.pdf$/i, ""));

        const result = await requestMultipart(`/chat/sessions/${currentSessionId}/attachments/pdf`, {
          token,
          formData,
        });

        uploadedCount += 1;
        chunkCount += Number(result.chunks_created || 0);
      }

      setUploadStatus({
        type: "success",
        message: `Uploaded ${uploadedCount} PDF${uploadedCount === 1 ? "" : "s"} and added ${chunkCount} chunk${chunkCount === 1 ? "" : "s"} to this chat.`,
      });
      onSessionChanged(currentSessionId);
    } catch (err) {
      setUploadStatus({ type: "error", message: err.message });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    if (event.dataTransfer.files?.length) {
      uploadPdfFiles(event.dataTransfer.files);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || loading || sendingRef.current) return;

    sendingRef.current = true;
    setPrompt("");
    setError("");
    setLoading(true);
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);

    let currentSessionId = sessionId;
    try {
      currentSessionId = await ensureSession();
      await streamAssistantResponse(currentSessionId, text, token, (event) => {
        if (event.type === "meta") {
          setMessages((current) => replaceLastAssistant(current, { sources: event.sources || [] }));
        }
        if (event.type === "token") {
          setMessages((current) => appendToLastAssistant(current, event.content || ""));
        }
      });
    } catch (err) {
      setError(err.message);
      setMessages((current) => replaceLastAssistant(current, { content: "I couldn't reach the chat service. Please check the backend and try again." }));
    } finally {
      sendingRef.current = false;
      setLoading(false);
      if (currentSessionId) onSessionChanged(currentSessionId);
    }
  }

  return (
    <section className="page chat-page">
      <PageHeader title="Agriculture Chat Assistant" icon={<MessageCircle />} action={<button onClick={newSession}>New Session</button>} />
      {sessionId && <p className="session-caption">Session ID: {sessionId}</p>}
      <div className="chat-window">
        {messages.map((message, index) => (
          <ChatBubble key={`${message.role}-${index}`} message={message} />
        ))}
      </div>
      {error && <div className="error">{error}</div>}
      {uploadStatus && <div className={uploadStatus.type}>{uploadStatus.message}</div>}
      <div
        className={`chat-composer ${dragActive ? "drag-active" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragActive(false);
        }}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden-file-input"
          onChange={(event) => uploadPdfFiles(event.target.files)}
        />
        <div className="chat-dropzone" onClick={openFilePicker} role="button" tabIndex={0}>
          <Upload size={18} />
          <div>
            <strong>Upload PDF reports</strong>
            <span>Drop soil analysis reports or browse files to add them to this chat’s RAG context.</span>
          </div>
          <span className="dropzone-action">Browse</span>
        </div>
        <form className="chat-input-row" onSubmit={sendMessage}>
          <input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask about crops, diseases, fertilizers..." />
          <button type="button" className="secondary-button upload-button" onClick={openFilePicker} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload PDF"}
          </button>
          <button className="primary-button" disabled={loading || uploading}>{loading ? "Sending..." : "Send"}</button>
        </form>
      </div>
    </section>
  );
}

async function streamAssistantResponse(sessionId, message, token, onEvent) {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || response.statusText);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const raw of events) {
      const line = raw.split("\n").find((part) => part.startsWith("data:"));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(5).trim()));
    }
  }
}

function replaceLastAssistant(messages, patch) {
  const next = [...messages];
  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index].role === "assistant") {
      next[index] = { ...next[index], ...patch };
      break;
    }
  }
  return next;
}

function appendToLastAssistant(messages, text) {
  const next = [...messages];
  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index].role === "assistant") {
      next[index] = { ...next[index], content: `${next[index].content || ""}${text}` };
      break;
    }
  }
  return next;
}

function ChatBubble({ message }) {
  return (
    <article className={`chat-bubble ${message.role}`}>
      <div className="markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content || "..."}
        </ReactMarkdown>
      </div>
      {Boolean(message.sources?.length) && (
        <details>
          <summary>Sources</summary>
          <ul className="source-list">
            {message.sources.map((source, index) => (
              <SourceItem key={index} source={source} />
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

function SourceItem({ source }) {
  if (typeof source === "string") {
    return <li>{source}</li>;
  }

  const title = source.title || source.source || source.url || "Untitled reference";
  const score = Number.isFinite(Number(source.best_score)) ? Number(source.best_score).toFixed(2) : null;
  const chunkText = source.chunk_count ? `${source.chunk_count} matched chunk${source.chunk_count === 1 ? "" : "s"}` : "matched RAG context";

  if (source.reference_type === "web" && source.url) {
    return (
      <li>
        <a href={source.url} target="_blank" rel="noreferrer">{title}</a>
        <span className="source-meta">{chunkText}{score ? ` · score ${score}` : ""}</span>
      </li>
    );
  }

  return (
    <li>
      <span>{title}</span>
      <span className="source-meta">
        RAG storage{source.source && source.source !== title ? ` · ${source.source}` : ""}{source.document_type ? ` · ${source.document_type}` : ""}{source.topic ? ` · ${source.topic}` : ""}{score ? ` · score ${score}` : ""}{source.chunk_ids?.[0] ? ` · ${source.chunk_ids[0]}` : ""}
      </span>
    </li>
  );
}

function IngestPage({ token }) {
  const [tab, setTab] = useState("text");
  const [status, setStatus] = useState(null);

  return (
    <section className="page">
      <PageHeader title="Ingest Agriculture Data" icon={<Database />} />
      <div className="tabs compact">
        {["text", "url", "urls"].map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item === "urls" ? "Multiple URLs" : item === "url" ? "Single URL" : "Raw Text"}</button>
        ))}
      </div>
      {tab === "text" && <RawTextIngest token={token} onStatus={setStatus} />}
      {tab === "url" && <UrlIngest token={token} onStatus={setStatus} />}
      {tab === "urls" && <UrlsIngest token={token} onStatus={setStatus} />}
      {status && <div className={status.type}>{status.message}</div>}
    </section>
  );
}

function RawTextIngest({ token, onStatus }) {
  const [form, setForm] = useState({ text: "", title: "", source: "", topic: "general" });
  return (
    <form className="form-grid" onSubmit={(event) => submitIngest(event, token, "/ingest/text", form, onStatus)}>
      <label className="wide">Text Content<textarea value={form.text} onChange={(event) => setForm({ ...form, text: event.target.value })} rows={8} /></label>
      <Field label="Title" value={form.title} onChange={(title) => setForm({ ...form, title })} />
      <Field label="Source" value={form.source} onChange={(source) => setForm({ ...form, source })} />
      <TopicSelect value={form.topic} onChange={(topic) => setForm({ ...form, topic })} />
      <button className="primary-button">Ingest Text</button>
    </form>
  );
}

function UrlIngest({ token, onStatus }) {
  const [form, setForm] = useState({ url: "", title: "", topic: "general" });
  return (
    <form className="form-grid" onSubmit={(event) => submitIngest(event, token, "/ingest/url", form, onStatus)}>
      <Field label="URL" value={form.url} onChange={(url) => setForm({ ...form, url })} />
      <Field label="Title" value={form.title} onChange={(title) => setForm({ ...form, title })} />
      <TopicSelect value={form.topic} onChange={(topic) => setForm({ ...form, topic })} />
      <button className="primary-button">Ingest URL</button>
    </form>
  );
}

function UrlsIngest({ token, onStatus }) {
  const [form, setForm] = useState({ urls: "", topic: "general" });
  return (
    <form className="form-grid" onSubmit={(event) => submitIngest(event, token, "/ingest/urls", { urls: form.urls.split("\n").map((url) => url.trim()).filter(Boolean), topic: form.topic }, onStatus)}>
      <label className="wide">URLs<textarea value={form.urls} onChange={(event) => setForm({ ...form, urls: event.target.value })} rows={8} /></label>
      <TopicSelect value={form.topic} onChange={(topic) => setForm({ ...form, topic })} />
      <button className="primary-button">Ingest URLs</button>
    </form>
  );
}

async function submitIngest(event, token, endpoint, body, onStatus) {
  event.preventDefault();
  onStatus(null);
  try {
    const result = await request(endpoint, { method: "POST", body, token });
    onStatus({ type: "success", message: `Ingested ${result.chunks_created} chunks.` });
  } catch (err) {
    onStatus({ type: "error", message: err.message });
  }
}

function SearchPage({ token }) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await request("/retrieval/search", { method: "POST", body: { query, top_k: Number(topK) }, token });
      setResults(data.results || []);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="page">
      <PageHeader title="Semantic Search" icon={<Search />} />
      <form className="search-row" onSubmit={submit}>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="rice leaf blight symptoms" />
        <input type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(event.target.value)} />
        <button className="primary-button">Search</button>
      </form>
      {error && <div className="error">{error}</div>}
      <div className="result-list">
        {results.map((result, index) => (
          <details className="result-card" key={index}>
            <summary>Result {index + 1} · similarity {Number(result.similarity).toFixed(2)}</summary>
            <p>{result.content}</p>
            <pre>{JSON.stringify(result.metadata, null, 2)}</pre>
          </details>
        ))}
      </div>
    </section>
  );
}

function UsersPage({ token, currentUser }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadUsers() {
    setError("");
    setLoading(true);
    try {
      setUsers(await request("/admin/users", { token }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, [token]);

  async function updateUser(user, patch) {
    const userId = getUserId(user);
    if (userId === getUserId(currentUser) && (patch.role === "user" || patch.is_active === false)) {
      setError("You cannot remove admin access from your own active session.");
      return;
    }

    try {
      setError("");
      await request(`/admin/users/${userId}`, { method: "PATCH", body: patch, token });
      await loadUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="page">
      <PageHeader title="Manage Users" icon={<UserCog />} />
      {error && <div className="error">{error}</div>}
      <div className="table">
        <div className="table-header"><span>Email</span><span>Name</span><span>Role</span><span>Status</span></div>
        {loading && <div className="table-row wide-row">Loading users...</div>}
        {!loading && !users.length && <div className="table-row wide-row">No users found.</div>}
        {users.map((item) => (
          <div className="table-row" key={getUserId(item)}>
            <span>{item.email}</span>
            <span>{item.full_name || "-"}</span>
            <select value={item.role} disabled={getUserId(item) === getUserId(currentUser)} onChange={(event) => updateUser(item, { role: event.target.value })}>
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
            <label className="switch-row">
              <input
                type="checkbox"
                checked={item.is_active}
                disabled={getUserId(item) === getUserId(currentUser)}
                onChange={(event) => updateUser(item, { is_active: event.target.checked })}
              />
              Active
            </label>
          </div>
        ))}
      </div>
    </section>
  );
}

function getUserId(user) {
  return user?._id || user?.id;
}

function getSessionId(session) {
  return session?._id || session?.id;
}

function normalizeSessionMessages(messages = []) {
  const normalized = messages
    .filter((message) => message?.role && typeof message.content === "string")
    .map((message) => ({
      role: message.role,
      content: message.content,
      sources: message.sources || [],
    }));
  return normalized.length ? normalized : [{ role: "assistant", content: GREETING }];
}

function formatSessionDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function SettingsPage() {
  const [status, setStatus] = useState("");

  async function testConnection() {
    setStatus("");
    try {
      const result = await request("/health");
      setStatus(result.status === "healthy" ? "Connected to backend." : "Backend returned an unexpected response.");
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <section className="page">
      <PageHeader title="Settings" icon={<Settings />} />
      <div className="settings-panel">
        <label>Backend URL<input value={API_URL} disabled /></label>
        <button onClick={testConnection}>Test Connection</button>
        {status && <p className="hint">{status}</p>}
      </div>
    </section>
  );
}

function PageHeader({ title, icon, action }) {
  return (
    <header className="page-header">
      <h1>{icon}{title}</h1>
      {action}
    </header>
  );
}

function Field({ label, value, onChange, type = "text" }) {
  return (
    <label>
      {label}
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function TopicSelect({ value, onChange }) {
  const topics = ["general", "crops", "diseases", "fertilizers", "weather", "irrigation"];
  return (
    <label>
      Topic
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {topics.map((topic) => <option key={topic} value={topic}>{topic}</option>)}
      </select>
    </label>
  );
}

createRoot(document.getElementById("root")).render(<App />);
