import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { GeneralOverviewPage } from "./pages/GeneralOverview";
import { VelocityDeepDivePage } from "./pages/VelocityDeepDive";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<GeneralOverviewPage />} />
        <Route path="velocity" element={<VelocityDeepDivePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
