/** The API stores decimal hours; the interface uses whole minutes. */
export function splitDuration(value: number) {
  const totalMinutes = Math.round(value * 60);
  return { hours: Math.floor(totalMinutes / 60), minutes: totalMinutes % 60 };
}

export function formatDuration(value: number): string {
  const { hours, minutes } = splitDuration(value);
  if (!hours) return `${minutes}min`;
  return minutes ? `${hours}h ${minutes}min` : `${hours}h`;
}

export function durationFromParts(hours: number, minutes: number, maxHours: number, positive = false): number {
  if (!Number.isInteger(hours) || !Number.isInteger(minutes) || hours < 0 || minutes < 0 || minutes > 59) {
    throw new Error('Informe horas inteiras e minutos entre 0 e 59.');
  }
  const totalMinutes = hours * 60 + minutes;
  if (positive && totalMinutes === 0) throw new Error('Informe pelo menos 1 minuto de trabalho.');
  if (totalMinutes > maxHours * 60) throw new Error(`O tempo não pode ultrapassar ${maxHours} horas.`);
  return totalMinutes / 60;
}
