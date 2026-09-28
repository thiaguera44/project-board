export type ReportEntry={id:number;task_id:number;task_title:string;hours:number;note:string;created_at:string};
export type ReportTask={id:number;project_id:number;title?:string;status?:string;due_date?:string;estimated_hours?:number};
export type ReportProject={id:number;name:string};

export function entryProjectId(entry:ReportEntry,tasks:ReportTask[]):number|null {
  return tasks.find(task=>task.id===entry.task_id)?.project_id??null;
}

export function filterReportEntries(
  entries:ReportEntry[],
  tasks:ReportTask[],
  from:string,
  to:string,
  project:string,
):ReportEntry[] {
  return entries.filter(entry=>{
    const day=entry.created_at.slice(0,10);
    const projectId=entryProjectId(entry,tasks);
    return (!from||day>=from)&&(!to||day<=to)&&(!project||String(projectId)===project);
  });
}

const csvCell=(value:unknown)=>`"${String(value??'').replace(/"/g,'""')}"`;

export function reportCsv(entries:ReportEntry[],tasks:ReportTask[],projects:ReportProject[]):string {
  const lines=[['Data','Projeto','Tarefa','Horas','Observação']];
  for(const entry of entries){
    const projectId=entryProjectId(entry,tasks);
    const project=projects.find(item=>item.id===projectId)?.name||'Projeto ou tarefa removida';
    lines.push([
      new Date(entry.created_at).toLocaleDateString('pt-BR'),
      project,
      entry.task_title,
      entry.hours.toFixed(2).replace('.',','),
      entry.note,
    ]);
  }
  return lines.map(line=>line.map(csvCell).join(';')).join('\r\n');
}

export type TaskComparison={id:number;title:string;project:string;estimated:number;actual:number;difference:number};

export function reportComparisons(entries:ReportEntry[],tasks:ReportTask[],projects:ReportProject[],from:string,to:string,project:string):TaskComparison[]{
  const filtered=filterReportEntries(entries,tasks,from,to,project);
  const workedIds=new Set(filtered.map(entry=>entry.task_id));
  return tasks.filter(task=>(!project||String(task.project_id)===project)&&(!from&&!to||workedIds.has(task.id))).map(task=>{
    const actual=filtered.filter(entry=>entry.task_id===task.id).reduce((sum,entry)=>sum+entry.hours,0);
    const estimated=task.estimated_hours||0;
    return {id:task.id,title:task.title||'Tarefa',project:projects.find(item=>item.id===task.project_id)?.name||'Removido',estimated,actual,difference:actual-estimated};
  }).filter(item=>item.estimated>0||item.actual>0).sort((a,b)=>Math.abs(b.difference)-Math.abs(a.difference));
}

export function reportOverdueTasks(tasks:ReportTask[],projects:ReportProject[],today:string,from:string,to:string,project:string){
  return tasks.filter(task=>task.status!=='done'&&!!task.due_date&&task.due_date<today&&(!project||String(task.project_id)===project)&&(!from||task.due_date!<from)&&(!to||task.due_date!>to)).map(task=>({id:task.id,title:task.title||'Tarefa',project:projects.find(item=>item.id===task.project_id)?.name||'Removido',due_date:task.due_date!,days:Math.max(1,Math.floor((new Date(today+'T00:00:00').getTime()-new Date(task.due_date!+'T00:00:00').getTime())/86400000))})).sort((a,b)=>a.due_date.localeCompare(b.due_date));
}

export function reportDailyHours(entries:ReportEntry[]){
  const totals=new Map<string,number>();
  entries.forEach(entry=>{const day=entry.created_at.slice(0,10);totals.set(day,(totals.get(day)||0)+entry.hours)});
  return [...totals].sort(([a],[b])=>a.localeCompare(b)).map(([day,hours])=>({day,hours}));
}
