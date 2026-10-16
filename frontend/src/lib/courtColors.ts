export type CourtColor = {
  bg: string;
  border: string;
  text: string;
  swatch: string;
};

/** Colores estables por índice de cancha (orden publicado). */
export const COURT_PALETTE: CourtColor[] = [
  { bg: 'rgba(234, 88, 12, 0.35)', border: '#ea580c', text: '#c2410c', swatch: '#ea580c' },
  { bg: 'rgba(56, 189, 248, 0.25)', border: '#38bdf8', text: '#0369a1', swatch: '#38bdf8' },
  { bg: 'rgba(34, 197, 94, 0.28)', border: '#22c55e', text: '#15803d', swatch: '#22c55e' },
  { bg: 'rgba(168, 85, 247, 0.28)', border: '#a855f7', text: '#6b21a8', swatch: '#a855f7' },
  { bg: 'rgba(244, 63, 94, 0.25)', border: '#f43f5e', text: '#be123c', swatch: '#f43f5e' },
];

export function colorForCourtIndex(index: number): CourtColor {
  return COURT_PALETTE[index % COURT_PALETTE.length];
}

export function colorForCourtId(courtId: number, courtIdsInOrder: number[]): CourtColor {
  const idx = courtIdsInOrder.indexOf(courtId);
  return colorForCourtIndex(idx >= 0 ? idx : courtId);
}
