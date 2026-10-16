import { NavLink, Outlet, useNavigate } from 'react-router-dom';

export function AdminLayout() {
  const navigate = useNavigate();
  const token = localStorage.getItem('admin_token');
  if (!token) {
    navigate('/admin/login');
    return null;
  }

  return (
    <div className="admin-shell">
      <aside>
        <h2>Back office</h2>
        <nav>
          <NavLink to="/admin/reservas">Reservas y contactos</NavLink>
          <NavLink to="/admin/configuracion">Configuración</NavLink>
          <NavLink to="/admin/integraciones">Integraciones</NavLink>
        </nav>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
