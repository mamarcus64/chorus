import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type SummaryPartition } from "../../api";

function assignmentLabel(row: SummaryPartition): string {
  if (row.assignment === "everyone") return "Everyone";
  return row.assignee_count === 1 ? "1 person" : `${row.assignee_count} people`;
}

function workingLabel(row: SummaryPartition): string {
  if (row.assignment === "selected") {
    return `${row.assigned_started} / ${row.assignee_count} assigned`;
  }
  return row.annotator_count === 1 ? "1 person" : `${row.annotator_count} people`;
}

export default function PartitionList() {
  const { project = "voices" } = useParams();
  const [rows, setRows] = useState<SummaryPartition[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState<"active" | "archived" | "all">("active");
  const [mode, setMode] = useState<"all" | "everyone" | "selected">("all");

  useEffect(() => {
    api.adminSummary(project).then((payload) => setRows(payload.partitions)).catch((err: Error) => setError(err.message));
  }, [project]);

  const needle = query.trim().toLowerCase();
  const shown = (rows ?? []).filter((row) => {
    if (archived === "active" && row.archived_at) return false;
    if (archived === "archived" && !row.archived_at) return false;
    if (mode !== "all" && row.assignment !== mode) return false;
    if (!needle) return true;
    return `${row.task_name} ${row.name}`.toLowerCase().includes(needle);
  });

  return (
    <section>
      <h1>Partitions</h1>
      {error && <p className="error">{error}</p>}
      <div className="filters">
        <label>
          Search
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Task or partition" />
        </label>
        <label>
          Status
          <select value={archived} onChange={(event) => setArchived(event.target.value as "active" | "archived" | "all")}>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </select>
        </label>
        <label>
          Assignment
          <select value={mode} onChange={(event) => setMode(event.target.value as "all" | "everyone" | "selected")}>
            <option value="all">Any assignment</option>
            <option value="everyone">Everyone</option>
            <option value="selected">Selected people</option>
          </select>
        </label>
      </div>
      {rows && shown.length === 0 && <p className="muted">No partitions match.</p>}
      {shown.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Partition</th>
              <th>Items</th>
              <th>Assignment</th>
              <th>Working</th>
              <th>Done</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row) => (
              <tr key={row.id}>
                <td>{row.task_name}</td>
                <td>
                  <Link to={`/p/${project}/admin/partition/${row.id}`}>{row.name}</Link>
                  {row.archived_at ? <span className="muted"> · archived</span> : null}
                </td>
                <td>{row.item_count}</td>
                <td>{assignmentLabel(row)}</td>
                <td>{workingLabel(row)}</td>
                <td>{row.done_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
