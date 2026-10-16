import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

export function AdminLogin() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [error, setError] = useState('');

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const { access_token } = await api.login(username, password);
      localStorage.setItem('admin_token', access_token);
      navigate('/admin/reservas');
    } catch {
      setError('Usuario o contraseña incorrectos');
    }
  }

  return (
    <main className="page narrow">
      <div className="card">
        <h1>Panel de administración</h1>
        <form onSubmit={onSubmit} className="form-grid">
          <label>
            Usuario
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            Contraseña
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="btn primary" type="submit">Ingresar</button>
        </form>
      </div>
    </main>
  );
}
