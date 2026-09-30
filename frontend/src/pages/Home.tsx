import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type PartitionEntry } from "../api";
import { useAuth } from "../auth";

const SECTIONS: { key: "todo" | "not_assigned" | "done"; title: string }[] = [
  { key: "todo", title: "To-do" },
  { key: "not_assigned", title: "Not assigned" },
  { key: "done", title: "Done" },
];

export default function Home() {
  const { project = "voices" } = useParams();
  const { user, loading, setUser } = useAuth();
  const navigate = useNavigate();
  const [lists, setLists] = useState<Record<string, PartitionEntry[]> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate(`/p/${project}/login`);
      return;
    }
    api.home(project).then(setLists).catch((err: Error) => setError(err.message));
  }, [loading, user, project, navigate]);

  async function logout() {
    await api.logout(project);
    setUser(null);
    navigate(`/p/${project}/login`);
  }

  if (!user) return null;

  return (
    <main>
      <header className="bar">
        <strong>Chorus / {project}</strong>
        <span>{user.username}</span>
        {user.is_admin && <Link to={`/p/${project}/admin`}>Admin</Link>}
        <button type="button" onClick={() => void logout()}>Log out</button>
      </header>
      {error && <p className="error">{error}</p>}
      {SECTIONS.map((section) => (
        <section key={section.key}>
          <h2>{section.title}</h2>
          {(lists?.[section.key] ?? []).length === 0 && <p className="muted">Nothing here.</p>}
          <ul className="partition-list">
            {(lists?.[section.key] ?? []).map((partition) => (
              <li key={partition.id}>
                <div>
                  <strong>{partition.task_name}</strong>
                  <div>{partition.name}</div>
                  <div className="muted">
                    {partition.answered_count} / {partition.item_count}
                    {partition.done_via ? ` · ${partition.done_via}` : ""}
                  </div>
                  <progress value={partition.answered_count} max={Math.max(partition.item_count, 1)} />
                </div>
                <Link to={`/p/${project}/partition/${partition.id}`}>Open</Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
