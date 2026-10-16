import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, type CartItem, type ComplexPublic } from '../api';
import { BookingCalendar } from '../components/BookingCalendar';

export function PublicBooking() {
  const { slug = 'demo' } = useParams();
  const [searchParams] = useSearchParams();
  const [complex, setComplex] = useState<ComplexPublic | null>(null);
  const [courtId, setCourtId] = useState<number | null>(null);
  const [busy, setBusy] = useState<{ starts_at: string; ends_at: string }[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [modal, setModal] = useState<{ start: Date; end: Date } | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<{ url: string; message: string } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getComplex(slug).then((c) => {
      setComplex(c);
      if (c.courts[0]) setCourtId(c.courts[0].id);
    }).catch(() => setError('Complejo no encontrado'));
  }, [slug]);

  useEffect(() => {
    const mode = searchParams.get('captura');
    if (!mode || !complex || !courtId) return;
    const start = new Date();
    start.setDate(start.getDate() + 2);
    start.setHours(18, 0, 0, 0);
    const end = new Date(start);
    end.setHours(19, 0, 0, 0);
    const court_name = complex.courts.find((c) => c.id === courtId)?.name ?? '';
    if (mode === 'modal' || mode === 'cart') {
      setModal({ start, end });
    }
    if (mode === 'cart') {
      setCart([
        {
          court_id: courtId,
          court_name,
          date: start.toISOString().slice(0, 10),
          starts_at: start.toISOString().slice(0, 19),
          ends_at: end.toISOString().slice(0, 19),
        },
      ]);
    }
  }, [searchParams, complex, courtId]);

  const fromIso = useMemo(() => new Date().toISOString().slice(0, 10), []);

  useEffect(() => {
    if (!courtId) return;
    api.getCalendar(slug, courtId, fromIso).then((days) => {
      const all = days.flatMap((d) =>
        d.busy.map((b) => ({ starts_at: b.starts_at, ends_at: b.ends_at })),
      );
      setBusy(all);
    });
  }, [slug, courtId, fromIso]);

  const courtName = useMemo(
    () => complex?.courts.find((c) => c.id === courtId)?.name ?? '',
    [complex, courtId],
  );

  function fmtTime(d: Date) {
    return d.toTimeString().slice(0, 5);
  }

  function durationHours(start: Date, end: Date) {
    return Math.max(0.5, (end.getTime() - start.getTime()) / 3600000);
  }

  function setDurationHours(hours: number) {
    if (!modal) return;
    const end = new Date(modal.start);
    end.setMinutes(end.getMinutes() + Math.round(hours * 60));
    setModal({ ...modal, end });
  }

  function addToCart() {
    if (!modal || !courtId) return;
    const date = modal.start.toISOString().slice(0, 10);
    const item: CartItem = {
      court_id: courtId,
      court_name: courtName,
      date,
      starts_at: modal.start.toISOString().slice(0, 19),
      ends_at: modal.end.toISOString().slice(0, 19),
    };
    setCart((c) => [...c, item]);
    setModal(null);
  }

  async function submitCart(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      const res = await api.submitCart(slug, {
        items: cart.map((it) => ({
          court_id: it.court_id,
          starts_at: it.starts_at,
          ends_at: it.ends_at,
        })),
        customer_name: name,
        customer_phone: phone,
        customer_email: email,
        customer_notes: notes,
      });
      setResult({ url: res.whatsapp_url, message: res.message });
      setCart([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar');
    }
  }

  if (result) {
    return (
      <main className="page">
        <div className="card success">
          <h1>Reservas pendientes</h1>
          <p>{result.message}</p>
          <a className="btn primary" href={result.url} target="_blank" rel="noreferrer">
            Enviar todo por WhatsApp
          </a>
        </div>
      </main>
    );
  }

  if (!complex) return <main className="page"><p>Cargando…</p></main>;

  const hs = complex.hours_start.slice(0, 5);
  const he = complex.hours_end.slice(0, 5);
  const ps = complex.public_hours_start.slice(0, 5);

  return (
    <main className="page wide">
      <header className="hero-header">
        <h1>{complex.name}</h1>
        <p>
          Calendario semanal/mensual (FullCalendar). Horario público desde {ps}; la franja anterior es solo profesores.
        </p>
        <Link to={`/profesor/${slug}`}>Acceso profesores</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <label>
        Cancha publicada
        <select value={courtId ?? ''} onChange={(e) => setCourtId(Number(e.target.value))}>
          {complex.courts.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </label>

      <BookingCalendar
        busy={busy}
        selectableFrom={ps}
        selectableTo={he}
        slotMinTime={`${hs}:00`}
        slotMaxTime={`${he}:00`}
        onSelectRange={(start, end) => setModal({ start, end })}
      />

      <aside className="cart card">
        <h2>Carrito ({cart.length})</h2>
        {cart.length === 0 && <p>Arrastrá en el calendario para agregar turnos.</p>}
        <ul>
          {cart.map((it, i) => (
            <li key={i}>
              {it.court_name} — {it.date} {it.starts_at.slice(11, 16)}–{it.ends_at.slice(11, 16)}
              <button type="button" className="link" onClick={() => setCart(cart.filter((_, j) => j !== i))}>Quitar</button>
            </li>
          ))}
        </ul>
        {cart.length > 0 && (
          <button type="button" className="btn primary" onClick={() => setContactOpen(true)}>
            Enviar reservas
          </button>
        )}
      </aside>

      {modal && (
        <div className="modal-backdrop">
          <div className="modal card form-grid">
            <h3>Confirmar rango</h3>
            <p>{modal.start.toLocaleDateString('es-PY')} {fmtTime(modal.start)} – {fmtTime(modal.end)}</p>
            <label>
              Inicio
              <input
                type="time"
                value={fmtTime(modal.start)}
                onChange={(e) => {
                  const [h, m] = e.target.value.split(':').map(Number);
                  const d = new Date(modal.start);
                  d.setHours(h, m, 0, 0);
                  setModal({ ...modal, start: d });
                }}
              />
            </label>
            <label>
              Fin
              <input
                type="time"
                value={fmtTime(modal.end)}
                onChange={(e) => {
                  const [h, m] = e.target.value.split(':').map(Number);
                  const d = new Date(modal.end);
                  d.setHours(h, m, 0, 0);
                  setModal({ ...modal, end: d });
                }}
              />
            </label>
            <label>
              Duración (horas)
              <input
                type="number"
                min={0.5}
                step={0.5}
                value={durationHours(modal.start, modal.end)}
                onChange={(e) => setDurationHours(Number(e.target.value))}
              />
            </label>
            <div className="modal-actions full">
              <button type="button" className="btn ghost" onClick={() => setModal(null)}>Cancelar</button>
              <button type="button" className="btn primary" onClick={addToCart}>Agregar al carrito</button>
            </div>
          </div>
        </div>
      )}

      {contactOpen && (
        <div className="modal-backdrop">
          <form className="modal card form-grid" onSubmit={submitCart}>
            <h3>Tus datos de contacto</h3>
            <label>Nombre<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
            <label>Teléfono<input required value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
            <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label className="full">Notas<textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
            <div className="modal-actions full">
              <button type="button" className="btn ghost" onClick={() => setContactOpen(false)}>Volver</button>
              <button type="submit" className="btn primary">Confirmar y abrir WhatsApp</button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
