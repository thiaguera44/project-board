import type { Task } from './types';

export type DeadlineAlert={task:Task;days:number;kind:'overdue'|'today'|'soon'};

function dayNumber(value:string){
  const [year,month,day]=value.split('-').map(Number);
  return Date.UTC(year,month-1,day)/86400000;
}

export function getDeadlineAlerts(tasks:Task[],today:string,windowDays=3):DeadlineAlert[]{
  const todayNumber=dayNumber(today);
  return tasks
    .filter(task=>task.due_date&&task.status!=='done')
    .map(task=>({task,days:dayNumber(task.due_date)-todayNumber}))
    .filter(item=>Number.isFinite(item.days)&&item.days<=windowDays)
    .map(item=>({...item,kind:item.days<0?'overdue':item.days===0?'today':'soon'} as DeadlineAlert))
    .sort((a,b)=>a.days-b.days||a.task.title.localeCompare(b.task.title,'pt-BR'));
}
