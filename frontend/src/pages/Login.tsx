import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Login() {
  const { project = "voices" } = useParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setUser(await api.login(project, username, password, adminKey));
      navigate(`/p/${project}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <main className="card">
      <h1>Chorus</h1>
      <p>Sign in to {project}.</p>
      <form onSubmit={onSubmit}>
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
        <label>
          Admin key
          <input type="password" value={adminKey} onChange={(event) => setAdminKey(event.target.value)} autoComplete="off" />
          <span className="muted">Optional. The first time it matches, this account becomes an admin.</span>
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Sign in</button>
      </form>
      <p><Link to={`/p/${project}/register`}>Create an account</Link></p>
    </main>
  );
}
