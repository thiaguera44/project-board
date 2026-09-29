import type { CSSProperties } from 'react';
import { CalendarDays, CircleCheck, Clock3, LockKeyhole, MessageSquare, MoreHorizontal, Pause, Play, PlayCircle, Repeat2, Square } from 'lucide-react';
import { clockTime, formatDate, initials, priorities, recurrences } from './boardConfig';
import type { ActiveTimer, BoardLabel, ChecklistItem, Task } from './types';
import RunrunBadge from './RunrunBadge';

type Props={task:Task;projectName:string;labels:BoardLabel[];checklist:ChecklistItem[];commentCount:number;pending:Task[];timer?:ActiveTimer;timerSeconds:number;busy:boolean;onEdit:()=>void;onHours:()=>void;onStart:()=>void;onPause:()=>void;onResume:()=>void;onStop:()=>void};

export default function KanbanTaskCard({task,projectName,labels,checklist,commentCount,pending,timer,timerSeconds,busy,onEdit,onHours,onStart,onPause,onResume,onStop}:Props){
 const done=checklist.filter(item=>item.is_done).length;
 return <article className="task-card" draggable={!busy} onDragStart={event=>event.dataTransfer.setData('text/plain',String(task.id))}>
  <div className="card-project"><span>{projectName}</span><span className="card-project-actions"><RunrunBadge task={task}/><button className="icon-button" aria-label={'Editar '+task.title} onClick={onEdit}><MoreHorizontal size={17}/></button></span></div>
  <button className="text-button card-title" onClick={onEdit}>{task.title}</button>
  <span className={'badge '+task.priority}>{priorities[task.priority]}</span>
  {task.recurrence!=='none'&&<span className="recurrence-badge" title="A próxima tarefa será criada ao concluir esta"><Repeat2 size={11}/>{recurrences[task.recurrence]}</span>}
  {pending.length>0&&<span className="blocked-badge" title={pending.map(item=>item.title).join(', ')}><LockKeyhole size={11}/>Bloqueada por {pending.length}</span>}
  {task.label_ids.length>0&&<div className="task-labels">{task.label_ids.map(id=>{const label=labels.find(item=>item.id===id);return label?<span key={id} style={{'--label-color':label.color} as CSSProperties}>{label.name}</span>:null})}</div>}
  {checklist.length>0&&<div className="checklist-progress"><span><CircleCheck size={12}/>{done}/{checklist.length}</span><div><i style={{width:`${done/checklist.length*100}%`}}/></div></div>}
  {commentCount>0&&<span className="comment-count"><MessageSquare size={11}/>{commentCount}</span>}
  <div className="card-bottom"><span><CalendarDays size={12}/>{formatDate(task.due_date)}</span><span className="mini-avatar" title={task.assignee}>{initials(task.assignee)}</span></div>
  <div className="card-time"><button disabled={busy} onClick={onHours}><Clock3 size={13}/> Registrar horas</button>{timer?<><button disabled={busy} onClick={timer.paused_at?onResume:onPause}>{timer.paused_at?<PlayCircle size={13}/>:<Pause size={13}/>} {timer.paused_at?'Retomar':'Pausar'}</button><button disabled={busy} onClick={onStop}><Square size={13}/> Parar {clockTime(timerSeconds)}</button></>:<button disabled={busy} onClick={onStart} title="Iniciar cronômetro"><Play size={13}/> Iniciar</button>}</div>
 </article>;
}
