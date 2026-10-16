import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ComplexAdmin } from '../api';

export function AdminConfig() {
  const token = localStorage.getItem('admin_token')!;
  const [complex, setComplex] = useState<ComplexAdmin | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.adminComplex(token).then(setComplex);
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!complex) return;
    const updated = await api.updateComplex(token, {
      name: complex.name,
      whatsapp_number: complex.whatsapp_number,
      contact_email: complex.contact_email,
      hours_start: complex.hours_start,
      hours_end: complex.hours_end,
    });
    setComplex(updated);
    setSaved(true);
  }

  if (!complex) return <p>Cargando…</p>;

  return (
    <div>
      <h1>Configuración del complejo</h1>
      <p>Link público: <code>/r/{complex.slug}</code></p>
      <form className="card form-grid" onSubmit={save}>
        <label>
          Nombre
          <input value={complex.name} onChange={(e) => setComplex({ ...complex, name: e.target.value })} />
        </label>
        <label>
          WhatsApp (con código país)
          <input
            value={complex.whatsapp_number}
            onChange={(e) => setComplex({ ...complex, whatsapp_number: e.target.value })}
          />
        </label>
        <label>
          Email de contacto
          <input
            value={complex.contact_email}
            onChange={(e) => setComplex({ ...complex, contact_email: e.target.value })}
          />
        </label>
        <label>
          Hora inicio
          <input
            type="time"
            value={complex.hours_start.slice(0, 5)}
            onChange={(e) => setComplex({ ...complex, hours_start: e.target.value + ':00' })}
          />
        </label>
        <label>
          Hora fin
          <input
            type="time"
            value={complex.hours_end.slice(0, 5)}
            onChange={(e) => setComplex({ ...complex, hours_end: e.target.value + ':00' })}
          />
        </label>
        <h3 className="full">Canchas</h3>
        <ul className="full court-list">
          {complex.courts.map((c) => (
            <li key={c.id}>{c.name} {c.active ? '' : '(inactiva)'}</li>
          ))}
        </ul>
        <button className="btn primary" type="submit">Guardar</button>
        {saved && <p className="ok">Guardado.</p>}
      </form>
    </div>
  );
}
