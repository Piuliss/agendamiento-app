import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, type CalendarBookingEvent } from '../api';
import { BookingCalendar } from '../components/BookingCalendar';
import { colorForCourtIndex } from '../lib/courtColors';
import { timePartsInAsuncion } from '../lib/timezone';

export function TeacherBooking() {
  const { slug = 'demo' } = useParams();
  const navigate = useNavigate();
  const tokenKey = `teacher_token_${slug}`;
  const [token, setToken] = useState(localStorage.getItem(tokenKey) || '');
  const [username, setUsername] = useState('profesor');
  const [password, setPassword] = useState('profesor');
  const [ctx, setCtx] = useState<Awaited<ReturnType<typeof api.teacherContext>> | null>(null);
  const [courtId, setCourtId] = useState<number | null>(null);
  const [bookingEvents, setBookingEvents] = useState<CalendarBookingEvent[]>([]);
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

  const fromIso = useMemo(() => timePartsInAsuncion(new Date()).dateKey, []);

  const courtColors = useMemo(() => {
    const map: Record<number, ReturnType<typeof colorForCourtIndex>> = {};
    ctx?.courts.forEach((c, i) => {
      map[c.id] = colorForCourtIndex(i);
    });
    return map;
  }, [ctx]);

  useEffect(() => {
    if (!slug) return;
    api.getCalendarEvents(slug, fromIso).then((r) => {
      setBookingEvents(
        courtId ? r.events.filter((e) => e.court_id === courtId) : r.events,
      );
    });
  }, [slug, courtId, fromIso]);

  async function confirm() {
    if (!modal || !courtId || !token) return;
    const pad = (n: number) => String(n).padStart(2, '0');
    const p = timePartsInAsuncion(modal.start);
    const pe = timePartsInAsuncion(modal.end);
    const res = await api.teacherBooking(token, {
      court_id: courtId,
      starts_at: `${p.dateKey}T${pad(p.hours)}:${pad(p.minutes)}:00`,
      ends_at: `${pe.dateKey}T${pad(pe.hours)}:${pad(pe.minutes)}:00`,
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
        bookingEvents={bookingEvents}
        courtColors={courtColors}
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
