import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, type CalendarBookingEvent, type CartItem, type ComplexPublic, type CourtAvailability } from '../api';
import { BookingCalendar } from '../components/BookingCalendar';
import { CourtLegend } from '../components/CourtLegend';
import { TouchStepper } from '../components/TouchStepper';
import { colorForCourtIndex } from '../lib/courtColors';
import { getBookingSessionId } from '../lib/bookingSession';
import { minutesInAsuncion, timePartsInAsuncion } from '../lib/timezone';

const DEFAULT_DURATION_MINUTES = 120;
const TIME_STEP_MINUTES = 30;
const DURATION_PRESETS = [60, 90, 120, 150, 180, 210, 240];

type ModalState = {
  start: Date;
  durationMinutes: number;
};

function toAsuncionIso(d: Date): string {
  const p = timePartsInAsuncion(d);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${p.dateKey}T${pad(p.hours)}:${pad(p.minutes)}:00`;
}

function roundDuration(minutes: number): number {
  return Math.max(TIME_STEP_MINUTES, Math.round(minutes / TIME_STEP_MINUTES) * TIME_STEP_MINUTES);
}

function endFromModal(modal: ModalState): Date {
  return new Date(modal.start.getTime() + modal.durationMinutes * 60_000);
}

function fmtTime(d: Date) {
  const p = timePartsInAsuncion(d);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(p.hours)}:${pad(p.minutes)}`;
}

function formatDurationLabel(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function PublicBooking() {
  const { slug = 'demo' } = useParams();
  const [searchParams] = useSearchParams();
  const sessionId = useMemo(() => getBookingSessionId(), []);
  const [complex, setComplex] = useState<ComplexPublic | null>(null);
  const [bookingEvents, setBookingEvents] = useState<CalendarBookingEvent[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [modal, setModal] = useState<ModalState | null>(null);
  const [courtOptions, setCourtOptions] = useState<CourtAvailability[]>([]);
  const [loadingCourts, setLoadingCourts] = useState(false);
  const [selectedCourtId, setSelectedCourtId] = useState<number | null>(null);
  const [holdError, setHoldError] = useState('');
  const [contactOpen, setContactOpen] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<{ url: string; message: string } | null>(null);
  const [error, setError] = useState('');
  const holdTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const publicWindow = useMemo(() => {
    if (!complex) return { fromMin: 0, toMin: 24 * 60 };
    const parse = (t: string) => {
      const [h, m] = t.slice(0, 5).split(':').map(Number);
      return h * 60 + (m || 0);
    };
    return {
      fromMin: parse(complex.public_hours_start),
      toMin: parse(complex.hours_end),
    };
  }, [complex]);

  useEffect(() => {
    api.getComplex(slug).then(setComplex).catch(() => setError('Complejo no encontrado'));
  }, [slug]);

  const fromIso = useMemo(() => timePartsInAsuncion(new Date()).dateKey, []);

  const courtColors = useMemo(() => {
    const map: Record<number, ReturnType<typeof colorForCourtIndex>> = {};
    complex?.courts.forEach((c, i) => {
      map[c.id] = colorForCourtIndex(i);
    });
    return map;
  }, [complex]);

  useEffect(() => {
    api.getCalendarEvents(slug, fromIso).then((r) => setBookingEvents(r.events));
  }, [slug, fromIso]);

  useEffect(() => {
    const mode = searchParams.get('captura');
    if (!mode || !complex) return;
    const start = new Date(2026, 9, 20, 18, 0, 0, 0);
    if (mode === 'modal' || mode === 'cart') {
      setModal({ start, durationMinutes: DEFAULT_DURATION_MINUTES });
    }
    if (mode === 'cart' && complex.courts[0]) {
      const end = endFromModal({ start, durationMinutes: DEFAULT_DURATION_MINUTES });
      setCart([
        {
          court_id: complex.courts[0].id,
          court_name: complex.courts[0].name,
          date: timePartsInAsuncion(start).dateKey,
          starts_at: toAsuncionIso(start),
          ends_at: toAsuncionIso(end),
        },
      ]);
    }
  }, [searchParams, complex]);

  const modalEnd = modal ? endFromModal(modal) : null;

  const loadCourts = useCallback(() => {
    if (!modal) return;
    setLoadingCourts(true);
    setHoldError('');
    const starts = toAsuncionIso(modal.start);
    const ends = toAsuncionIso(endFromModal(modal));
    api
      .getCourtsAvailability(slug, starts, ends, sessionId)
      .then((rows) => {
        setCourtOptions(rows);
        setSelectedCourtId((prev) => {
          if (prev && rows.find((r) => r.court_id === prev && r.available)) return prev;
          return rows.find((r) => r.available)?.court_id ?? null;
        });
      })
      .catch(() => setHoldError('No se pudo consultar disponibilidad'))
      .finally(() => setLoadingCourts(false));
  }, [modal, slug, sessionId]);

  useEffect(() => {
    if (!modal) {
      setCourtOptions([]);
      setSelectedCourtId(null);
      setHoldError('');
      return;
    }
    loadCourts();
  }, [modal, loadCourts]);

  const renewHold = useCallback(async () => {
    if (!modal || !selectedCourtId) return;
    const starts = toAsuncionIso(modal.start);
    const ends = toAsuncionIso(endFromModal(modal));
    try {
      await api.acquireHold(slug, {
        court_id: selectedCourtId,
        starts_at: starts,
        ends_at: ends,
        session_id: sessionId,
      });
      setHoldError('');
    } catch (err) {
      setHoldError(err instanceof Error ? err.message : 'Turno no disponible');
      loadCourts();
    }
  }, [modal, selectedCourtId, slug, sessionId, loadCourts]);

  useEffect(() => {
    if (!modal || !selectedCourtId) return;
    renewHold();
    if (holdTimerRef.current) clearInterval(holdTimerRef.current);
    holdTimerRef.current = setInterval(() => {
      renewHold();
    }, 45_000);
    return () => {
      if (holdTimerRef.current) clearInterval(holdTimerRef.current);
    };
  }, [modal, selectedCourtId, modal?.start, modal?.durationMinutes, renewHold]);

  function openModalFromSelection(start: Date, dragEnd: Date) {
    const draggedMinutes = roundDuration((dragEnd.getTime() - start.getTime()) / 60_000);
    const durationMinutes =
      draggedMinutes > TIME_STEP_MINUTES ? draggedMinutes : DEFAULT_DURATION_MINUTES;
    setModal({ start, durationMinutes });
  }

  function shiftStart(deltaMinutes: number) {
    if (!modal) return;
    const next = new Date(modal.start.getTime() + deltaMinutes * 60_000);
    const startMin = minutesInAsuncion(next);
    const endMin = startMin + modal.durationMinutes;
    if (startMin < publicWindow.fromMin || endMin > publicWindow.toMin) return;
    setModal({ ...modal, start: next });
  }

  function changeDuration(deltaMinutes: number) {
    if (!modal) return;
    const next = roundDuration(modal.durationMinutes + deltaMinutes);
    const endMin = minutesInAsuncion(modal.start) + next;
    if (next < TIME_STEP_MINUTES || endMin > publicWindow.toMin) return;
    setModal({ ...modal, durationMinutes: next });
  }

  function setDurationPreset(minutes: number) {
    if (!modal) return;
    const endMin = minutesInAsuncion(modal.start) + minutes;
    if (endMin > publicWindow.toMin) return;
    setModal({ ...modal, durationMinutes: minutes });
  }

  async function closeModal() {
    if (modal && selectedCourtId && modalEnd) {
      await api.releaseHolds(slug, sessionId, {
        court_id: selectedCourtId,
        starts_at: toAsuncionIso(modal.start),
        ends_at: toAsuncionIso(modalEnd),
      });
    }
    setModal(null);
  }

  const availableCourts = courtOptions.filter((c) => c.available);

  async function addToCart() {
    if (!modal || !selectedCourtId || !modalEnd) return;
    const court = courtOptions.find((c) => c.court_id === selectedCourtId);
    if (!court?.available) return;
    try {
      await api.acquireHold(slug, {
        court_id: selectedCourtId,
        starts_at: toAsuncionIso(modal.start),
        ends_at: toAsuncionIso(modalEnd),
        session_id: sessionId,
      });
    } catch (err) {
      setHoldError(err instanceof Error ? err.message : 'Turno no disponible');
      return;
    }
    const item: CartItem = {
      court_id: selectedCourtId,
      court_name: court.name,
      date: timePartsInAsuncion(modal.start).dateKey,
      starts_at: toAsuncionIso(modal.start),
      ends_at: toAsuncionIso(modalEnd),
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
        session_id: sessionId,
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
  const startMin = modal ? minutesInAsuncion(modal.start) : 0;
  const endMin = modal ? startMin + modal.durationMinutes : 0;

  return (
    <main className="page wide">
      <header className="hero-header">
        <h1>{complex.name}</h1>
        <p>
          Elegí día y horario en el calendario. Cada turno dura 2 horas por defecto.
          Horario público desde {ps}.
        </p>
        <Link to={`/profesor/${slug}`}>Acceso profesores</Link>
      </header>
      {error && <p className="error">{error}</p>}

      <CourtLegend
        items={(complex.courts ?? []).map((c, i) => ({
          courtId: c.id,
          name: c.name,
          color: colorForCourtIndex(i),
        }))}
      />
      <BookingCalendar
        bookingEvents={bookingEvents}
        courtColors={courtColors}
        selectableFrom={ps}
        selectableTo={he}
        slotMinTime={`${hs}:00`}
        slotMaxTime={`${he}:00`}
        initialDate={searchParams.get('semana') ?? undefined}
        onSelectRange={openModalFromSelection}
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

      {modal && modalEnd && (
        <div className="modal-backdrop">
          <div className="modal card court-modal">
            <h3>Elegir cancha</h3>
            <p className="range-summary">
              {modal.start.toLocaleDateString('es-PY', { timeZone: 'America/Asuncion' })}
            </p>

            <TouchStepper
              label="Inicio"
              valueLabel={fmtTime(modal.start)}
              onMinus={() => shiftStart(-TIME_STEP_MINUTES)}
              onPlus={() => shiftStart(TIME_STEP_MINUTES)}
              minusDisabled={startMin <= publicWindow.fromMin}
              plusDisabled={endMin >= publicWindow.toMin}
            />

            <TouchStepper
              label="Duración"
              valueLabel={formatDurationLabel(modal.durationMinutes)}
              onMinus={() => changeDuration(-TIME_STEP_MINUTES)}
              onPlus={() => changeDuration(TIME_STEP_MINUTES)}
              minusDisabled={modal.durationMinutes <= TIME_STEP_MINUTES}
              plusDisabled={endMin >= publicWindow.toMin}
            />

            <div className="duration-presets">
              {DURATION_PRESETS.map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`preset-chip ${modal.durationMinutes === m ? 'active' : ''}`}
                  disabled={startMin + m > publicWindow.toMin}
                  onClick={() => setDurationPreset(m)}
                >
                  {formatDurationLabel(m)}
                </button>
              ))}
            </div>

            <p className="range-end">
              Fin: <strong>{fmtTime(modalEnd)}</strong>
            </p>

            {holdError && <p className="error">{holdError}</p>}

            <div className="court-pick">
              <h4>Canchas</h4>
              {loadingCourts && <p>Consultando disponibilidad…</p>}
              {!loadingCourts && availableCourts.length === 0 && (
                <p className="error">No hay canchas libres en este horario. Probá otro rango.</p>
              )}
              {!loadingCourts && courtOptions.map((c) => (
                <label key={c.court_id} className={`court-option ${c.available ? '' : 'disabled'}`}>
                  <input
                    type="radio"
                    name="court"
                    disabled={!c.available}
                    checked={selectedCourtId === c.court_id}
                    onChange={() => setSelectedCourtId(c.court_id)}
                  />
                  <span>{c.name} {c.available ? '(disponible)' : '(ocupada)'}</span>
                </label>
              ))}
            </div>

            <div className="modal-actions">
              <button type="button" className="btn ghost" onClick={() => closeModal()}>Cancelar</button>
              <button
                type="button"
                className="btn primary"
                disabled={!selectedCourtId || availableCourts.length === 0 || !!holdError}
                onClick={() => addToCart()}
              >
                Agregar al carrito
              </button>
            </div>
          </div>
        </div>
      )}

      {contactOpen && (
        <div className="modal-backdrop">
          <form className="modal card form-grid" onSubmit={submitCart}>
            <h3>Tus datos de contacto</h3>
            <label>Nombre<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
            <label>Teléfono<input required type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
            <label>Email<input type="email" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
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
