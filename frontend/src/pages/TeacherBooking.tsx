import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { BookingCalendar } from '../components/BookingCalendar';

export function TeacherBooking() {
  const { slug = 'demo' } = useParams();
  const navigate = useNavigate();
  const tokenKey = `teacher_token_${slug}`;
  const [token, setToken] = useState(localStorage.getItem(tokenKey) || '');
  const [username, setUsername] = useState('profesor');
  const [password, setPassword] = useState('profesor');
  const [ctx, setCtx] = useState<Awaited<ReturnType<typeof api.teacherContext>> | null>(null);
  const [courtId, setCourtId] = useState<number | null>(null);
  const [busy, setBusy] = useState<{ starts_at: string; ends_at: string }[]>([]);
  const [modal, setModal] = useState<{ start: Date; end: Date } | null>(null);
  const [students, setStudents] = useState(4);
  const [msg, setMsg] = useState('');

  async function login(e: React.FormEvent) {
    e.preventDefault();
    const { access_token } = await api.teacherLogin(username, password);
    localStorage.setItem(tokenKey, access_token);
    setToken(access_token);
  }

  useEffect(() => {
    if (!token) return;
    api.teacherContext(token).then((c) => {
      setCtx(c);
      if (c.courts[0]) setCourtId(c.courts[0].id);
    }).catch(() => {
      localStorage.removeItem(tokenKey);
      setToken('');
    });
  }, [token, tokenKey]);

  const fromIso = new Date().toISOString().slice(0, 10);
  useEffect(() => {
    if (!courtId || !slug) return;
    api.getCalendar(slug, courtId, fromIso).then((days) => {
      setBusy(days.flatMap((d) => d.busy.map((b) => ({ starts_at: b.starts_at, ends_at: b.ends_at }))));
    });
  }, [slug, courtId, fromIso]);

  async function confirm() {
    if (!modal || !courtId || !token) return;
    const res = await api.teacherBooking(token, {
      court_id: courtId,
      starts_at: modal.start.toISOString().slice(0, 19),
      ends_at: modal.end.toISOString().slice(0, 19),
      student_count: students,
    });
    setMsg(res.message);
    setModal(null);
  }

  if (!token) {
    return (
      <main className="page narrow">
        <form className="card form-grid" onSubmit={login}>
          <h1>Profesores</h1>
          <label>Usuario<input value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label>Contraseña<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <button className="btn primary" type="submit">Ingresar</button>
          <button type="button" className="btn ghost" onClick={() => navigate(`/r/${slug}`)}>Volver al público</button>
        </form>
      </main>
    );
  }

  if (!ctx) return <main className="page"><p>Cargando…</p></main>;

  const c = ctx.complex;
  const hs = c.hours_start.slice(0, 5);
  const he = c.hours_end.slice(0, 5);
  const te = c.public_hours_start.slice(0, 5);

  return (
    <main className="page wide">
      <h1>Reserva profesor — {ctx.teacher.full_name}</h1>
      <p>Bloque exclusivo (FullCalendar): {hs} a {te}</p>
      {msg && <p className="ok">{msg}</p>}
      <select value={courtId ?? ''} onChange={(e) => setCourtId(Number(e.target.value))}>
        {ctx.courts.map((co) => <option key={co.id} value={co.id}>{co.name}</option>)}
      </select>
      <BookingCalendar
        busy={busy}
        selectableFrom={hs}
        selectableTo={te}
        slotMinTime={`${hs}:00`}
        slotMaxTime={`${he}:00`}
        onSelectRange={(start, end) => setModal({ start, end })}
      />
      {modal && (
        <div className="modal-backdrop">
          <div className="modal card form-grid">
            <h3>Confirmar clase</h3>
            <p>
              {modal.start.toLocaleDateString('es-PY')}{' '}
              {modal.start.toTimeString().slice(0, 5)}–{modal.end.toTimeString().slice(0, 5)}
            </p>
            <label>
              Cantidad de alumnos
              <input type="number" min={1} max={50} value={students} onChange={(e) => setStudents(Number(e.target.value))} />
            </label>
            <div className="modal-actions full">
              <button type="button" className="btn ghost" onClick={() => setModal(null)}>Cancelar</button>
              <button type="button" className="btn primary" onClick={confirm}>Confirmar reserva</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
