import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';

export function AdminIntegraciones() {
  const token = localStorage.getItem('admin_token')!;
  const [google, setGoogle] = useState<{
    configured: boolean;
    connected: boolean;
    missing_env: string[];
    calendar_mode: string;
  } | null>(null);
  const [params] = useSearchParams();

  useEffect(() => {
    api.integrations(token).then((r) => setGoogle(r.google));
  }, []);

  const flash = params.get('google');

  return (
    <div>
      <h1>Integraciones</h1>
      {flash === 'ok' && <p className="ok">Google conectado.</p>}
      {flash === 'error' && <p className="error">No se pudo conectar Google.</p>}

      {google && (
        <section className="card">
          <h2>Google Calendar</h2>
          <p>Modo actual: <strong>{google.calendar_mode}</strong></p>
          {!google.configured && (
            <p>
              OAuth no configurado. Definí <code>GOOGLE_CLIENT_ID</code> y{' '}
              <code>GOOGLE_CLIENT_SECRET</code> en el backend. Sin eso, el calendario local guarda eventos tentativos.
            </p>
          )}
          {google.configured && !google.connected && (
            <p>
              <a className="btn primary" href={`http://localhost:8000/api/auth/google/start?complex_id=1`}>
                Conectar Google Calendar
              </a>
            </p>
          )}
          {google.connected && <p className="ok">Cuenta de Google vinculada.</p>}
          {google.missing_env.length > 0 && (
            <p>Faltan variables: {google.missing_env.join(', ')}</p>
          )}
        </section>
      )}

      <section className="card">
        <h2>Lumi (ERP)</h2>
        <p>Adaptador preparado con <code>LUMI_API_URL</code> y <code>LUMI_API_TOKEN</code>. Sin spec no se envían datos.</p>
      </section>
    </div>
  );
}
