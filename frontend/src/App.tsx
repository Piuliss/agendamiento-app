import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import { AdminLayout } from './pages/AdminLayout';
import { AdminLogin } from './pages/AdminLogin';
import { AdminReservas } from './pages/AdminReservas';
import { AdminConfig } from './pages/AdminConfig';
import { AdminIntegraciones } from './pages/AdminIntegraciones';
import { PublicBooking } from './pages/PublicBooking';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/r/demo" replace />} />
        <Route path="/r/:slug" element={<PublicBooking />} />
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="reservas" replace />} />
          <Route path="reservas" element={<AdminReservas />} />
          <Route path="configuracion" element={<AdminConfig />} />
          <Route path="integraciones" element={<AdminIntegraciones />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
