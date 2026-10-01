import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type PersonRow } from "../../api";

export default function PeopleList() {
  const { project = "voices" } = useParams();
  const [rows, setRows] = useState<PersonRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.adminUsers(project).then((payload) => setRows(payload.users)).catch((err: Error) => setError(err.message));
  }, [project]);

  return (
    <section>
      <h1>People</h1>
      <p className="muted">
        Open a person to put them on partitions that are already set to Selected. Partitions set to Everyone stay as they are.
      </p>
      {error && <p className="error">{error}</p>}
      {rows && rows.length === 0 && <p className="muted">No accounts yet.</p>}
      {rows && rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Person</th>
              <th>Selected partitions</th>
              <th>Items answered</th>
              <th>Partitions done</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((person) => (
              <tr key={person.id}>
                <td>
                  <Link to={`/p/${project}/admin/people/${person.id}`}>{person.username}</Link>
                  {person.is_admin ? <span className="muted"> · admin</span> : null}
                </td>
                <td>{person.selected_count}</td>
                <td>{person.answered_count}</td>
                <td>{person.done_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
