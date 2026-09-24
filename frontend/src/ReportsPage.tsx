import { formatDuration } from './duration';
import { entryProjectId, filterReportEntries } from './report';
import type { Entry, Project, Task } from './types';

type Props={
 entries:Entry[];
 tasks:Task[];
 projects:Project[];
 from:string;
 to:string;
 project:string;
 onFrom:(value:string)=>void;
 onTo:(value:string)=>void;
 onProject:(value:string)=>void;
};

export default function ReportsPage(props:Props){
 const {entries,tasks,projects,from,to,project,onFrom,onTo,onProject}=props;
 const filtered=filterReportEntries(entries,tasks,from,to,project);
 const total=filtered.reduce((sum,entry)=>sum+entry.hours,0);
 const projectTotals=projects.map(item=>({
  id:item.id,
  name:item.name,
  hours:filtered.filter(entry=>entryProjectId(entry,tasks)===item.id).reduce((sum,entry)=>sum+entry.hours,0),
 })).filter(item=>item.hours>0);
 const removed=filtered.filter(entry=>entryProjectId(entry,tasks)===null).reduce((sum,entry)=>sum+entry.hours,0);
 return <>
  <section className="panel report-filters">
   <div className="section-heading"><div><h3>Período e projeto</h3><p className="subtle">Os filtros também serão aplicados ao arquivo CSV.</p></div><button onClick={()=>{onFrom('');onTo('');onProject('')}}>Limpar filtros</button></div>
   <div className="report-filter-grid"><label>De<input type="date" value={from} onChange={e=>onFrom(e.target.value)}/></label><label>Até<input type="date" value={to} onChange={e=>onTo(e.target.value)}/></label><label>Projeto<select value={project} onChange={e=>onProject(e.target.value)}><option value="">Todos os projetos</option>{projects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
  </section>
  <div className="report-stats">
   <section className="stat"><span>Horas no período</span><strong>{formatDuration(total)}</strong><small>Soma dos lançamentos filtrados</small></section>
   <section className="stat"><span>Lançamentos</span><strong>{filtered.length}</strong><small>Registros encontrados</small></section>
   <section className="stat"><span>Tarefas trabalhadas</span><strong>{new Set(filtered.map(entry=>entry.task_id)).size}</strong><small>Tarefas com horas registradas</small></section>
  </div>
  <div className="report-grid">
   <section className="panel"><div className="section-heading"><h3>Horas por projeto</h3><span>{formatDuration(total)}</span></div><div className="report-projects">{projectTotals.map(item=><div key={item.id}><span>{item.name}</span><strong>{formatDuration(item.hours)}</strong><div><i style={{width:(total?item.hours/total*100:0)+'%'}}/></div></div>)}{!!removed&&<div><span>Projeto ou tarefa removida</span><strong>{formatDuration(removed)}</strong></div>}{!filtered.length&&<p className="empty">Nenhum lançamento encontrado para os filtros escolhidos.</p>}</div></section>
   <section className="panel report-details"><div className="section-heading"><h3>Detalhamento</h3><span>{filtered.length} registros</span></div><div className="table-scroll"><table><thead><tr><th>Data</th><th>Projeto</th><th>Tarefa</th><th>Observação</th><th>Horas</th></tr></thead><tbody>{filtered.slice().reverse().map(entry=><tr key={entry.id}><td>{new Date(entry.created_at).toLocaleDateString('pt-BR')}</td><td>{projects.find(item=>item.id===entryProjectId(entry,tasks))?.name||'Removido'}</td><td>{entry.task_title}</td><td>{entry.note||'Sem observação'}</td><td><strong>{formatDuration(entry.hours)}</strong></td></tr>)}</tbody></table></div></section>
  </div>
 </>;
}
