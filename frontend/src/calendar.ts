export type CalendarDay = { date: string; day: number; inMonth: boolean };

const pad = (value: number) => String(value).padStart(2, '0');

export function parseDateKey(value: string) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function dateKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function monthKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
}

export function monthTitle(value: string) {
  const [year, month] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' })
    .format(new Date(year, month - 1, 1)).replace(/^./, letter => letter.toUpperCase());
}

export function shiftMonth(value: string, amount: number) {
  const [year, month] = value.split('-').map(Number);
  return monthKey(new Date(year, month - 1 + amount, 1));
}

export function shiftDays(value: string, amount: number) {
  const date = parseDateKey(value);
  return dateKey(new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount));
}

export function weekDays(value: string): CalendarDay[] {
  const selected = parseDateKey(value);
  const mondayOffset = (selected.getDay() + 6) % 7;
  const monday = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate() - mondayOffset);
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + index);
    return { date: dateKey(date), day: date.getDate(), inMonth: true };
  });
}

export function weekTitle(value: string) {
  const days = weekDays(value);
  const first = parseDateKey(days[0].date);
  const last = parseDateKey(days[6].date);
  const short = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' });
  if (first.getFullYear() !== last.getFullYear()) return `${short.format(first)} ${first.getFullYear()} – ${short.format(last)} ${last.getFullYear()}`;
  return `${short.format(first)} – ${short.format(last)} ${last.getFullYear()}`;
}

export function calendarDays(value: string): CalendarDay[] {
  const [year, month] = value.split('-').map(Number);
  const first = new Date(year, month - 1, 1);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(year, month - 1, 1 - mondayOffset);
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index);
    return { date: dateKey(date), day: date.getDate(), inMonth: date.getMonth() === month - 1 };
  });
}
