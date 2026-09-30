import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Register() {
  const { project = "voices" } = useParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [registrationKey, setRegistrationKey] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setUser(await api.register(project, username, password, registrationKey));
      navigate(`/p/${project}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <main className="card">
      <h1>Create an account</h1>
      <form onSubmit={onSubmit}>
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></label>
        <label>Registration key<input value={registrationKey} onChange={(event) => setRegistrationKey(event.target.value)} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Register</button>
      </form>
      <p><Link to={`/p/${project}/login`}>Already have an account</Link></p>
    </main>
  );
}
