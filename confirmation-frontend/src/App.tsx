import { Routes, Route, Navigate } from "react-router-dom";
import ConfirmPage from "./pages/ConfirmPage";

export default function App() {
  return (
    <Routes>
      <Route path="/confirm/:token" element={<ConfirmPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
