import test from 'node:test';
import assert from 'node:assert/strict';

import { durationFromParts, formatDuration, splitDuration } from '../.test-build/duration.js';
import { filterReportEntries, reportCsv } from '../.test-build/report.js';
import { getDeadlineAlerts } from '../.test-build/deadlines.js';
import { calendarDays, shiftDays, shiftMonth, weekDays } from '../.test-build/calendar.js';

test('converte todos os minutos de 0 a 24 horas sem perder precisão', () => {
  for (let totalMinutes = 0; totalMinutes <= 24 * 60; totalMinutes += 1) {
    const value = totalMinutes / 60;
    const parts = splitDuration(value);
    assert.deepEqual(parts, {
      hours: Math.floor(totalMinutes / 60),
      minutes: totalMinutes % 60,
    });
    assert.equal(durationFromParts(parts.hours, parts.minutes, 24), value);
  }
});

test('formata durações para leitura', () => {
  assert.equal(formatDuration(0), '0min');
  assert.equal(formatDuration(0.5), '30min');
  assert.equal(formatDuration(1), '1h');
  assert.equal(formatDuration(1.25), '1h 15min');
});

test('rejeita minutos, horas e limites inválidos', () => {
  assert.throws(() => durationFromParts(0, 60, 24), /minutos entre 0 e 59/);
  assert.throws(() => durationFromParts(-1, 0, 24), /horas inteiras/);
  assert.throws(() => durationFromParts(1.5, 0, 24), /horas inteiras/);
  assert.throws(() => durationFromParts(0, 0, 24, true), /pelo menos 1 minuto/);
  assert.throws(() => durationFromParts(24, 1, 24, true), /não pode ultrapassar 24 horas/);
});

test('filtra relatórios e gera CSV compatível com Excel', () => {
  const entries=[
    {id:1,task_id:10,task_title:'Planejar',hours:1.5,note:'Texto com "aspas"',created_at:'2026-09-20T10:00:00-03:00'},
    {id:2,task_id:20,task_title:'Revisar',hours:.5,note:'',created_at:'2026-09-22T10:00:00-03:00'},
  ];
  const tasks=[{id:10,project_id:1},{id:20,project_id:2}];
  const projects=[{id:1,name:'Projeto A'},{id:2,name:'Projeto B'}];
  const filtered=filterReportEntries(entries,tasks,'2026-09-19','2026-09-21','1');
  assert.deepEqual(filtered.map(entry=>entry.id),[1]);
  const csv=reportCsv(filtered,tasks,projects);
  assert.match(csv,/Projeto A/);
  assert.match(csv,/"1,50"/);
  assert.match(csv,/"Texto com ""aspas"""/);
});

test('classifica apenas prazos vencidos ou próximos', () => {
  const task=(id,title,due_date,status='todo')=>({id,title,due_date,status,project_id:1,priority:'medium',assignee:'Ana',estimated_hours:0,is_archived:false});
  const alerts=getDeadlineAlerts([
    task(1,'Atrasada','2026-09-23'),
    task(2,'Hoje','2026-09-25'),
    task(3,'Próxima','2026-09-28'),
    task(4,'Distante','2026-09-29'),
    task(5,'Concluída','2026-09-20','done'),
  ],'2026-09-25');

  assert.deepEqual(alerts.map(alert=>[alert.task.id,alert.days,alert.kind]),[
    [1,-2,'overdue'],[2,0,'today'],[3,3,'soon'],
  ]);
});

test('monta o calendário de segunda a domingo e navega entre anos', () => {
  const days = calendarDays('2026-09');
  assert.equal(days.length, 42);
  assert.deepEqual(days[0], { date: '2026-08-31', day: 31, inMonth: false });
  assert.deepEqual(days[41], { date: '2026-10-11', day: 11, inMonth: false });
  assert.equal(days.filter(day => day.inMonth).length, 30);
  assert.equal(shiftMonth('2026-12', 1), '2027-01');
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
});

test('monta uma semana completa e navega entre semanas', () => {
  assert.deepEqual(weekDays('2026-09-30').map(day => day.date), [
    '2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02','2026-10-03','2026-10-04',
  ]);
  assert.equal(shiftDays('2026-12-28', 7), '2027-01-04');
  assert.equal(shiftDays('2026-01-05', -7), '2025-12-29');
});
