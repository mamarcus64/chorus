import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type PersonAdmin } from "../../api";

export default function PersonDetail() {
  const { project = "voices", userId = "" } = useParams();
  const [detail, setDetail] = useState<PersonAdmin | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancel = false;
    api.adminUser(project, userId).then((payload) => {
      if (cancel) return;
      setDetail(payload);
      setPicked(payload.partitions.filter((row) => row.assignment === "selected" && row.is_assignee).map((row) => row.id));
    }).catch((err: Error) => {
      if (!cancel) setError(err.message);
    });
    return () => {
      cancel = true;
    };
  }, [project, userId]);

  function toggle(id: string) {
    setPicked((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  async function save() {
    setError("");
    try {
      await api.setUserAssignments(project, userId, picked);
      const payload = await api.adminUser(project, userId);
      setDetail(payload);
      setPicked(payload.partitions.filter((row) => row.assignment === "selected" && row.is_assignee).map((row) => row.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  if (!detail) {
    return <section>{error ? <p className="error">{error}</p> : <p>Loading…</p>}</section>;
  }

  return (
    <section>
      <p><Link to={`/p/${project}/admin/people`}>People</Link></p>
      <h1>{detail.user.username}</h1>
      {detail.user.is_admin && <p className="muted">Admin</p>}
      <p className="muted">
        Checked rows are the selected lists this person is on. Saving replaces that set. Everyone-mode partitions are unchanged.
      </p>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>On list</th>
            <th>Task</th>
            <th>Partition</th>
            <th>Assignment</th>
            <th>Answered</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {detail.partitions.map((row) => (
            <tr key={row.id}>
              <td>
                {row.assignment === "selected" ? (
                  <input
                    type="checkbox"
                    checked={picked.includes(row.id)}
                    onChange={() => toggle(row.id)}
                    aria-label={`${row.task_name} ${row.name}`}
                  />
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>{row.task_name}</td>
              <td>
                <Link to={`/p/${project}/admin/partition/${row.id}`}>{row.name}</Link>
                {row.archived_at ? <span className="muted"> · archived</span> : null}
              </td>
              <td>{row.assignment === "everyone" ? "Everyone" : "Selected"}</td>
              <td>{row.answered_count} / {row.item_count}</td>
              <td>{row.status ?? "—"}{row.done_via ? ` (${row.done_via})` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button type="button" onClick={() => void save()}>Save assignments</button>
    </section>
  );
}
