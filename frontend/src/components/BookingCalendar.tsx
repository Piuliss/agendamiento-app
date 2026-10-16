import dayGridPlugin from '@fullcalendar/react/daygrid';
import interactionPlugin from '@fullcalendar/react/interaction';
import esLocale from '@fullcalendar/react/locales/es';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import classicThemePlugin from '@fullcalendar/react/themes/classic';
import FullCalendar from '@fullcalendar/react';
import type { DateSelectInfo } from '@fullcalendar/react';

export type BusyBlock = { starts_at: string; ends_at: string };

type Props = {
  busy: BusyBlock[];
  selectableFrom: string;
  selectableTo: string;
  slotMinTime: string;
  slotMaxTime: string;
  onSelectRange: (start: Date, end: Date) => void;
};

export function BookingCalendar({
  busy,
  selectableFrom,
  selectableTo,
  slotMinTime,
  slotMaxTime,
  onSelectRange,
}: Props) {
  const events = busy.map((b, i) => ({
    id: `busy-${i}`,
    start: b.starts_at,
    end: b.ends_at,
    display: 'background',
    backgroundColor: '#cbd5e1',
  }));

  function inWindow(start: Date, end: Date) {
    const [fh, fm] = selectableFrom.split(':').map(Number);
    const [th, tm] = selectableTo.split(':').map(Number);
    const startMin = start.getHours() * 60 + start.getMinutes();
    const endMin = end.getHours() * 60 + end.getMinutes();
    const fromMin = fh * 60 + (fm || 0);
    const toMin = th * 60 + (tm || 0);
    if (start.toDateString() !== end.toDateString()) return false;
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
    <div className="fc-wrap">
      <FullCalendar
        plugins={[classicThemePlugin, dayGridPlugin, timeGridPlugin, interactionPlugin]}
        locale={esLocale}
        initialView="timeGridWeek"
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
