import { useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, CircleCheck, Plus } from 'lucide-react';
import { calendarDays, dateKey, monthKey, monthTitle, shiftDays, shiftMonth, weekDays, weekTitle } from './calendar';
import { priorities, statuses } from './boardConfig';
import type { Project, Task } from './types';

type Props = { tasks: Task[]; projects: Project[]; onEdit: (task: Task) => void; onCreate: (date?: string) => void };
const weekdays = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM'];

export default function CalendarPage({ tasks, projects, onEdit, onCreate }: Props) {
  const today = new Date().toLocaleDateString('en-CA');
  const [view, setView] = useState<'month'|'week'>('month');
  const [cursor, setCursor] = useState(dateKey(new Date()));
  const month = monthKey(new Date(Number(cursor.slice(0,4)), Number(cursor.slice(5,7))-1, 1));
  const days = view === 'month' ? calendarDays(month) : weekDays(cursor);
  const projectName = (id: number) => projects.find(project => project.id === id)?.name || 'Projeto';
  const dated = tasks.filter(task => task.due_date);
  const withoutDate = tasks.filter(task => !task.due_date);

  return <>
    <section className="panel calendar-panel">
      <div className="calendar-toolbar">
        <div className="title-with-icon"><CalendarDays size={19}/><div><h3>Calendário de prazos</h3><p className="subtle">{dated.length} {dated.length === 1 ? 'tarefa planejada' : 'tarefas planejadas'}</p></div></div>
        <div className="calendar-controls"><div className="calendar-view-toggle" role="group" aria-label="Tipo de calendário"><button className={view==='month'?'active':''} onClick={()=>setView('month')}>Mês</button><button className={view==='week'?'active':''} onClick={()=>setView('week')}>Semana</button></div><div className="calendar-navigation"><button className="icon-button" aria-label={view==='month'?'Mês anterior':'Semana anterior'} onClick={() => setCursor(view==='month'?`${shiftMonth(month,-1)}-01`:shiftDays(cursor,-7))}><ChevronLeft size={18}/></button><strong>{view==='month'?monthTitle(month):weekTitle(cursor)}</strong><button className="icon-button" aria-label={view==='month'?'Próximo mês':'Próxima semana'} onClick={() => setCursor(view==='month'?`${shiftMonth(month,1)}-01`:shiftDays(cursor,7))}><ChevronRight size={18}/></button><button onClick={() => setCursor(dateKey(new Date()))}>Hoje</button></div></div>
      </div>
      <div className="calendar-weekdays">{weekdays.map(day => <span key={day}>{day}</span>)}</div>
      <div className={view==='week'?'calendar-grid week-view':'calendar-grid'}>{days.map(day => {
        const dayTasks = dated.filter(task => task.due_date === day.date);
        return <div className={`calendar-day${day.inMonth ? '' : ' outside'}${day.date === today ? ' today' : ''}`} key={day.date}>
          <div className="calendar-day-heading"><span>{day.day}</span><button className="icon-button calendar-add" aria-label={`Criar tarefa para ${day.date}`} onClick={() => onCreate(day.date)}><Plus size={13}/></button></div>
          <div className="calendar-events">{dayTasks.slice(0, view==='week'?dayTasks.length:3).map(task => <button className={`calendar-event ${task.priority} ${task.status === 'done' ? 'completed' : ''}`} key={task.id} onClick={() => onEdit(task)} title={`${task.title} · ${projectName(task.project_id)} · ${statuses[task.status]}`}><span className="calendar-event-dot"/><span>{task.title}</span>{task.status === 'done' && <CircleCheck size={12}/>}</button>)}{view==='month'&&dayTasks.length > 3 && <button className="calendar-more" onClick={() => onEdit(dayTasks[3])}>+{dayTasks.length - 3} mais</button>}</div>
        </div>;
      })}</div>
    </section>
    {withoutDate.length > 0 && <section className="panel unscheduled-panel"><div className="section-heading"><div><h3>Tarefas sem prazo</h3><p className="subtle">Defina uma data para que apareçam no calendário.</p></div><span>{withoutDate.length}</span></div><div className="unscheduled-list">{withoutDate.map(task => <button key={task.id} onClick={() => onEdit(task)}><span className={`badge ${task.priority}`}>{priorities[task.priority]}</span><span><strong>{task.title}</strong><small>{projectName(task.project_id)} · {statuses[task.status]}</small></span><ChevronRight size={15}/></button>)}</div></section>}
  </>;
}
