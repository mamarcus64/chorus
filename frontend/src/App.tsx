import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { AuthProvider } from "./auth";
import Admin from "./pages/Admin";
import Annotate from "./pages/Annotate";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";

function ProjectRoutes() {
  const { project = "voices" } = useParams();
  return (
    <AuthProvider project={project}>
      <Routes>
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route index element={<Home />} />
        <Route path="partition/:partitionId" element={<Annotate />} />
        <Route path="admin" element={<Admin />} />
      </Routes>
    </AuthProvider>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/p/voices" replace />} />
      <Route path="/p/:project/*" element={<ProjectRoutes />} />
    </Routes>
  );
}
