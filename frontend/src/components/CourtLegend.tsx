import type { CourtColor } from '../lib/courtColors';

type Item = { courtId: number; name: string; color: CourtColor };

export function CourtLegend({ items }: { items: Item[] }) {
  if (items.length === 0) return null;
  return (
    <div className="court-legend" aria-label="Leyenda de canchas">
      {items.map((it) => (
        <span key={it.courtId} className="court-legend-item">
          <span className="swatch" style={{ backgroundColor: it.color.swatch }} />
          {it.name}
        </span>
      ))}
      <span className="court-legend-item now-hint">
        <span className="swatch now" />
        Hora actual (Asunción)
      </span>
    </div>
  );
}
