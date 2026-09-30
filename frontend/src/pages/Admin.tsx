import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type AdminPartition, type AdminPayload } from "../api";
import { useAuth } from "../auth";

export default function Admin() {
  const { project = "voices" } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [payload, setPayload] = useState<AdminPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate(`/p/${project}/login`);
      return;
    }
    if (!user.is_admin) {
      navigate(`/p/${project}`);
      return;
    }
    api.admin(project).then(setPayload).catch((err: Error) => setError(err.message));
  }, [loading, user, project, navigate]);

  async function saveAssignment(partition: AdminPartition, mode: "everyone" | "selected", userIds: string[]) {
    setError("");
    try {
      await api.setAssignment(project, partition.id, mode, userIds);
      setPayload(await api.admin(project));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function archive(partition: AdminPartition, archived: boolean) {
    await api.setArchived(project, partition.id, archived);
    setPayload(await api.admin(project));
  }

  if (!user?.is_admin || !payload) {
    return <main>{error ? <p className="error">{error}</p> : <p>Loading…</p>}</main>;
  }

  return (
    <main>
      <header className="bar">
        <Link to={`/p/${project}`}>Home</Link>
        <strong>Admin</strong>
      </header>
      {error && <p className="error">{error}</p>}
      {payload.partitions.map((partition) => (
        <AssignmentCard
          key={partition.id}
          partition={partition}
          users={payload.users}
          onSave={saveAssignment}
          onArchive={archive}
        />
      ))}
    </main>
  );
}

function AssignmentCard({
  partition,
  users,
  onSave,
  onArchive,
}: {
  partition: AdminPartition;
  users: { id: string; username: string }[];
  onSave: (partition: AdminPartition, mode: "everyone" | "selected", userIds: string[]) => Promise<void>;
  onArchive: (partition: AdminPartition, archived: boolean) => Promise<void>;
}) {
  const [mode, setMode] = useState(partition.assignment);
  const [picked, setPicked] = useState<string[]>(partition.assignees);

  function toggle(id: string) {
    setPicked((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <section className="card">
      <h2>{partition.task_name} — {partition.name}</h2>
      <p className="muted">
        {partition.item_count} items
        {partition.archived_at ? " · archived" : ""}
      </p>
      <label>
        Assignment
        <select value={mode} onChange={(event) => setMode(event.target.value as "everyone" | "selected")}>
          <option value="everyone">Everyone</option>
          <option value="selected">Selected people</option>
        </select>
      </label>
      {mode === "selected" && (
        <ul>
          {users.map((person) => (
            <li key={person.id}>
              <label>
                <input
                  type="checkbox"
                  checked={picked.includes(person.id)}
                  onChange={() => toggle(person.id)}
                />
                {person.username}
              </label>
            </li>
          ))}
        </ul>
      )}
      <button type="button" onClick={() => void onSave(partition, mode, picked)}>Save assignment</button>
      <button type="button" onClick={() => void onArchive(partition, !partition.archived_at)}>
        {partition.archived_at ? "Restore" : "Archive"}
      </button>
      <table>
        <thead>
          <tr><th>Person</th><th>Answered</th><th>Status</th></tr>
        </thead>
        <tbody>
          {partition.users.map((person) => (
            <tr key={person.id}>
              <td>{person.username}</td>
              <td>{person.answered_count}</td>
              <td>{person.status ?? "—"}{person.done_via ? ` (${person.done_via})` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
