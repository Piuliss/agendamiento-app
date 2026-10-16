export const CALENDAR_TZ = 'America/Asuncion';

export function timePartsInAsuncion(date: Date): { hours: number; minutes: number; dateKey: string } {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: CALENDAR_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? '0';
  return {
    hours: Number(get('hour')),
    minutes: Number(get('minute')),
    dateKey: `${get('year')}-${get('month')}-${get('day')}`,
  };
}

export function minutesInAsuncion(date: Date): number {
  const { hours, minutes } = timePartsInAsuncion(date);
  return hours * 60 + minutes;
}

export function sameCalendarDayInAsuncion(a: Date, b: Date): boolean {
  return timePartsInAsuncion(a).dateKey === timePartsInAsuncion(b).dateKey;
}
