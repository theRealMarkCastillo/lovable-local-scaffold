import React, { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

export default function Workbench({ config }) {
  const [supabase] = useState(() =>
    typeof window === "undefined"
      ? null
      : createClient(config.supabaseUrl, config.supabaseKey, {
          auth: {
            flowType: "pkce",
            detectSessionInUrl: true,
            persistSession: true,
          },
        }),
  );
  const [user, setUser] = useState(null),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState([]),
    [files, setFiles] = useState([]),
    [analysis, setAnalysis] = useState(null);
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [title, setTitle] = useState("My first portable note"),
    [body, setBody] = useState(
      "A local Supabase backend keeps familiar APIs, authentication, storage and functions.",
    );
  const [originMismatch, setOriginMismatch] = useState(false);
  const [realtime, setRealtime] = useState("connecting");
  async function loadNotes() {
    const { data, error } = await supabase
      .from("notes")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50);
    if (error) throw error;
    setNotes(data);
  }
  async function loadFiles(uid) {
    const { data, error } = await supabase.storage.from("uploads").list(uid);
    if (error) throw error;
    setFiles(data.filter((file) => file.name !== ".emptyFolderPlaceholder"));
  }
  async function perform(task) {
    setBusy(true);
    setNotice("");
    try {
      await task();
    } catch (error) {
      setNotice(error.message || "Request failed");
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    setOriginMismatch(new URL(config.publicUrl || config.supabaseUrl).origin !== location.origin);
    let alive = true;
    supabase.auth.getSession().then(({ data, error }) => {
      if (alive) {
        setUser(data.session?.user || null);
        if (error) setNotice(error.message);
      }
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
    });
    return () => {
      alive = false;
      subscription.unsubscribe();
    };
  }, []);
  useEffect(() => {
    if (!user) {
      setNotes([]);
      setFiles([]);
      setAnalysis(null);
      return;
    }
    loadNotes().catch((e) => setNotice(e.message));
    loadFiles(user.id).catch((e) => setNotice(e.message));
    const channel = supabase
      .channel("my-notes")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "notes",
          filter: `owner_id=eq.${user.id}`,
        },
        () => loadNotes().catch((e) => setNotice(e.message)),
      )
      .subscribe((status) => setRealtime(status.toLowerCase()));
    return () => {
      supabase.removeChannel(channel);
    };
  }, [user?.id]);
  async function login(event) {
    event.preventDefault();
    await perform(async () => {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
    });
  }
  async function signup() {
    await perform(async () => {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: location.origin },
      });
      if (error) throw error;
      setNotice(
        "Check the local Mailpit inbox, open the confirmation link, then sign in.",
      );
    });
  }
  async function save(event) {
    event.preventDefault();
    await perform(async () => {
      const { error } = await supabase.from("notes").insert({ title, body });
      if (error) throw error;
      await loadNotes();
    });
  }
  async function remove(id) {
    await perform(async () => {
      const { error } = await supabase.from("notes").delete().eq("id", id);
      if (error) throw error;
      await loadNotes();
    });
  }
  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    await perform(async () => {
      const name = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
      const path = `${user.id}/${crypto.randomUUID()}-${name}`;
      const { error } = await supabase.storage
        .from("uploads")
        .upload(path, file);
      if (error) throw error;
      await loadFiles(user.id);
    });
    event.target.value = "";
  }
  async function download(name) {
    await perform(async () => {
      const { data, error } = await supabase.storage
        .from("uploads")
        .download(`${user.id}/${name}`);
      if (error) throw error;
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  async function analyze() {
    await perform(async () => {
      const { data, error } = await supabase.functions.invoke("analyze", {
        body: { text: body },
      });
      if (error) throw error;
      setAnalysis(data);
    });
  }
  async function logout() {
    await perform(async () => {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    });
  }
  const backendOrigin = new URL(config.supabaseUrl).origin;
  return (
    <main>
      <header>
        <span className="eyebrow">LOCAL-FIRST · SUPABASE-COMPATIBLE</span>
        <h1>
          Your app.
          <br />
          Your own workbench.
        </h1>
        <p>
          A small React application using Supabase Auth, row-level security,
          private storage, realtime and an Edge Function. Keep these interfaces
          when moving an exported app.
        </p>
      </header>
      <div className="stack">
        <span>React</span>
        <b>→</b>
        <span>Supabase API</span>
        <b>→</b>
        <span>Postgres + RLS</span>
        <small>Auth · Storage · Realtime · Functions · Local email</small>
      </div>
      <div role="status" aria-live="polite" className={notice ? "notice" : ""}>
        {notice}
      </div>
      {originMismatch && (
        <p className="notice">
          Backend origin: {backendOrigin}. Use the configured origin for email
          links, or update it with the documented origin command.
        </p>
      )}
      {!user ? (
        <section className="signin">
          <h2>Sign in to your workspace</h2>
          <p>
            Create a local account. Confirmation mail is captured in Mailpit
            instead of sent to the internet.
          </p>
          <form onSubmit={login}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <div className="actions">
              <button disabled={busy}>Sign in</button>
              <button
                className="secondary"
                type="button"
                onClick={signup}
                disabled={busy || !email || password.length < 8}
              >
                Create account
              </button>
            </div>
          </form>
        </section>
      ) : (
        <>
          <div className="account">
            <span>Signed in as {user.email}</span>
            <button className="secondary" onClick={logout} disabled={busy}>
              Sign out
            </button>
          </div>
          <div className="grid">
            <section>
              <h2>Create a note</h2>
              <form onSubmit={save}>
                <label htmlFor="title">Title</label>
                <input
                  id="title"
                  maxLength={120}
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <label htmlFor="body">Content</label>
                <textarea
                  id="body"
                  rows={6}
                  maxLength={4000}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
                <div className="actions">
                  <button disabled={busy}>Save note</button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={analyze}
                    disabled={busy}
                  >
                    Run Edge Function
                  </button>
                </div>
                {analysis && (
                  <p className="result">
                    {analysis.words} words · {analysis.characters} characters
                  </p>
                )}
              </form>
            </section>
            <section>
              <h2>
                Your notes <span className="badge">{realtime}</span>
              </h2>
              <p className="hint">
                The database enforces ownership. Realtime updates arrive through
                the same public entry point.
              </p>
              {notes.length ? (
                notes.map((note) => (
                  <article key={note.id}>
                    <strong>{note.title}</strong>
                    <p>{note.body}</p>
                    <button
                      className="text"
                      onClick={() => remove(note.id)}
                      disabled={busy}
                    >
                      Delete note
                    </button>
                  </article>
                ))
              ) : (
                <p>No notes yet.</p>
              )}
            </section>
            <section className="wide">
              <h2>Private uploads</h2>
              <p className="hint">
                Text, JSON, PNG or JPEG, up to 2 MB. Access is restricted to
                your user folder.
              </p>
              <label htmlFor="upload">Choose a file</label>
              <input
                id="upload"
                type="file"
                accept="text/plain,application/json,image/png,image/jpeg"
                disabled={busy}
                onChange={upload}
              />
              {files.map((file) => (
                <div className="file" key={file.name}>
                  <span>{file.name}</span>
                  <button
                    className="text"
                    onClick={() => download(file.name)}
                    disabled={busy}
                  >
                    Download
                  </button>
                </div>
              ))}
            </section>
          </div>
        </>
      )}
      <footer>
        Development reference. Synthetic data only. External connectors and
        cloud deployment require their own configuration and validation.
      </footer>
    </main>
  );
}
