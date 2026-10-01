import { useEffect } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth";
import PartitionDetail from "./admin/PartitionDetail";
import PartitionList from "./admin/PartitionList";
import PeopleList from "./admin/PeopleList";
import PersonDetail from "./admin/PersonDetail";

export default function Admin() {
  const { project = "voices" } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate(`/p/${project}/login`);
      return;
    }
    if (!user.is_admin) navigate(`/p/${project}`);
  }, [loading, user, project, navigate]);

  if (!user?.is_admin) {
    return <main>{loading ? <p>Loading…</p> : null}</main>;
  }

  return (
    <main className="wide">
      <header className="bar">
        <Link to={`/p/${project}`}>Home</Link>
        <NavLink to={`/p/${project}/admin`} end>Partitions</NavLink>
        <NavLink to={`/p/${project}/admin/people`}>People</NavLink>
        <strong>Admin</strong>
        <span>{user.username}</span>
      </header>
      <Routes>
        <Route index element={<PartitionList />} />
        <Route path="partition/:partitionId" element={<PartitionDetail />} />
        <Route path="people" element={<PeopleList />} />
        <Route path="people/:userId" element={<PersonDetail />} />
      </Routes>
    </main>
  );
}
