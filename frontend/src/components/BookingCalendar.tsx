import dayGridPlugin from '@fullcalendar/react/daygrid';
import interactionPlugin from '@fullcalendar/react/interaction';
import esLocale from '@fullcalendar/react/locales/es';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import classicThemePlugin from '@fullcalendar/react/themes/classic';
import FullCalendar from '@fullcalendar/react';
import type { DateSelectInfo } from '@fullcalendar/react';
import type { CourtColor } from '../lib/courtColors';
import { CALENDAR_TZ, minutesInAsuncion, sameCalendarDayInAsuncion } from '../lib/timezone';

export type CalendarBookingEvent = {
  id: number;
  court_id: number;
  court_name: string;
  starts_at: string;
  ends_at: string;
  label: string;
};

type Props = {
  bookingEvents: CalendarBookingEvent[];
  courtColors: Record<number, CourtColor>;
  selectableFrom: string;
  selectableTo: string;
  slotMinTime: string;
  slotMaxTime: string;
  initialDate?: string;
  onSelectRange: (start: Date, end: Date) => void;
};

export function BookingCalendar({
  bookingEvents,
  courtColors,
  selectableFrom,
  selectableTo,
  slotMinTime,
  slotMaxTime,
  initialDate,
  onSelectRange,
}: Props) {
  const events = bookingEvents.map((ev) => {
    const color = courtColors[ev.court_id];
    return {
      id: String(ev.id),
      start: ev.starts_at,
      end: ev.ends_at,
      title: ev.label,
      backgroundColor: color?.bg ?? '#cbd5e1',
      borderColor: color?.border ?? '#64748b',
      textColor: color?.text ?? '#0f172a',
      classNames: [`court-event-${ev.court_id}`],
      extendedProps: { courtId: ev.court_id },
    };
  });

  function inWindow(start: Date, end: Date) {
    const [fh, fm] = selectableFrom.split(':').map(Number);
    const [th, tm] = selectableTo.split(':').map(Number);
    const fromMin = fh * 60 + (fm || 0);
    const toMin = th * 60 + (tm || 0);
    const startMin = minutesInAsuncion(start);
    const endMin = minutesInAsuncion(end);
    if (!sameCalendarDayInAsuncion(start, end)) return false;
    return startMin >= fromMin && endMin <= toMin && end > start;
  }

  function handleSelect(arg: DateSelectInfo) {
    if (!inWindow(arg.start, arg.end)) {
      arg.view.calendar.unselect();
      return;
    }
    onSelectRange(arg.start, arg.end);
    arg.view.calendar.unselect();
  }

  return (
    <div className="fc-wrap fc-courts-calendar">
      <FullCalendar
        key={initialDate ?? 'default-week'}
        plugins={[classicThemePlugin, dayGridPlugin, timeGridPlugin, interactionPlugin]}
        locale={esLocale}
        timeZone={CALENDAR_TZ}
        initialView="timeGridWeek"
        {...(initialDate ? { initialDate } : {})}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek',
        }}
        slotMinTime={slotMinTime}
        slotMaxTime={slotMaxTime}
        slotDuration="00:30:00"
        snapDuration="00:30:00"
        allDaySlot={true}
        height={640}
        expandRows={true}
        slotEventOverlap={true}
        eventOverlap={true}
        selectable
        selectMirror
        selectOverlap={false}
        selectConstraint="businessHours"
        selectAllow={(info) => inWindow(info.start, info.end)}
        select={handleSelect}
        businessHours={{
          daysOfWeek: [0, 1, 2, 3, 4, 5, 6],
          startTime: selectableFrom,
          endTime: selectableTo,
        }}
        events={events}
        nowIndicator
      />
    </div>
  );
}
