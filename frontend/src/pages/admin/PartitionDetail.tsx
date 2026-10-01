import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type PartitionAdmin } from "../../api";

export default function PartitionDetail() {
  const { project = "voices", partitionId = "" } = useParams();
  const [detail, setDetail] = useState<PartitionAdmin | null>(null);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"everyone" | "selected">("everyone");
  const [picked, setPicked] = useState<string[]>([]);

  useEffect(() => {
    let cancel = false;
    api.adminPartition(project, partitionId).then((payload) => {
      if (cancel) return;
      setDetail(payload);
      setMode(payload.assignment);
      setPicked(payload.assignees);
    }).catch((err: Error) => {
      if (!cancel) setError(err.message);
    });
    return () => {
      cancel = true;
    };
  }, [project, partitionId]);

  async function reload() {
    const payload = await api.adminPartition(project, partitionId);
    setDetail(payload);
    setMode(payload.assignment);
    setPicked(payload.assignees);
  }

  async function saveAssignment() {
    if (!detail) return;
    setError("");
    try {
      await api.setAssignment(project, detail.id, mode, mode === "selected" ? picked : []);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function archive(archived: boolean) {
    if (!detail) return;
    setError("");
    try {
      await api.setArchived(project, detail.id, archived);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  function toggle(id: string) {
    setPicked((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  if (!detail) {
    return <section>{error ? <p className="error">{error}</p> : <p>Loading…</p>}</section>;
  }

  return (
    <section>
      <p><Link to={`/p/${project}/admin`}>Partitions</Link></p>
      <h1>{detail.task_name} — {detail.name}</h1>
      <p className="muted">
        {detail.item_count === 1 ? "1 item" : `${detail.item_count} items`}
        {detail.archived_at ? " · archived" : ""}
      </p>
      <p className="bar">
        <Link to={`/p/${project}/partition/${detail.id}`}>Open</Link>
        <button type="button" onClick={() => void archive(!detail.archived_at)}>
          {detail.archived_at ? "Restore" : "Archive"}
        </button>
      </p>
      {error && <p className="error">{error}</p>}

      <h2>Assignment</h2>
      <p className="muted">
        A selected list does not add people who register later. People left off the list still see this partition under Not assigned, and they can still open it.
      </p>
      <label>
        Mode
        <select value={mode} onChange={(event) => setMode(event.target.value as "everyone" | "selected")}>
          <option value="everyone">Everyone</option>
          <option value="selected">Selected people</option>
        </select>
      </label>
      {mode === "selected" && (
        <ul className="check-list">
          {detail.users.map((person) => (
            <li key={person.id}>
              <label>
                <input
                  type="checkbox"
                  checked={picked.includes(person.id)}
                  onChange={() => toggle(person.id)}
                />
                {person.username}
                <span className="muted">{person.answered_count} answered</span>
              </label>
            </li>
          ))}
        </ul>
      )}
      <button type="button" onClick={() => void saveAssignment()}>Save assignment</button>

      <h2>Progress</h2>
      <table>
        <thead>
          <tr><th>Person</th><th>Assigned</th><th>Answered</th><th>Status</th></tr>
        </thead>
        <tbody>
          {detail.users.map((person) => {
            const assigned = detail.assignment === "everyone" || person.is_assignee;
            return (
              <tr key={person.id}>
                <td>{person.username}</td>
                <td>{assigned ? "Yes" : "No"}</td>
                <td>{person.answered_count} / {detail.item_count}</td>
                <td>{person.status ?? "—"}{person.done_via ? ` (${person.done_via})` : ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Answers</h2>
      {detail.answers.length === 0 && <p className="muted">No answers yet.</p>}
      {detail.answers.length > 0 && (
        <table>
          <thead>
            <tr><th>Choice</th><th>Count</th></tr>
          </thead>
          <tbody>
            {detail.answers.map((row) => (
              <tr key={`${row.choice ?? "none"}:${row.label}`}>
                <td>{row.label}</td>
                <td>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
