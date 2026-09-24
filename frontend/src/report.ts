export type ReportEntry={id:number;task_id:number;task_title:string;hours:number;note:string;created_at:string};
export type ReportTask={id:number;project_id:number};
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
