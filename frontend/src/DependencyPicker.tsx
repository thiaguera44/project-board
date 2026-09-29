import { useMemo, useState } from 'react';
import { LockKeyhole, Search, X } from 'lucide-react';
import { statuses } from './boardConfig';
import type { Project, Task } from './types';

type Props={tasks:Task[];projects:Project[];currentTask?:Task};

export default function DependencyPicker({tasks,projects,currentTask}:Props){
 const available=tasks.filter(task=>task.id!==currentTask?.id);
 const [query,setQuery]=useState('');
 const [selected,setSelected]=useState(()=>new Set(currentTask?.dependency_ids||[]));
 const visible=useMemo(()=>{
  const term=query.trim().toLocaleLowerCase('pt-BR');
  return available.filter(task=>!term||`${task.title} ${projects.find(project=>project.id===task.project_id)?.name||''} ${statuses[task.status]||''}`.toLocaleLowerCase('pt-BR').includes(term)).sort((a,b)=>a.title.localeCompare(b.title,'pt-BR'));
 },[available,projects,query,selected]);
 function toggle(id:number){setSelected(previous=>{const next=new Set(previous);if(next.has(id))next.delete(id);else next.add(id);return next})}
 return <fieldset className="dependency-picker"><legend><LockKeyhole size={13}/> Depende de</legend><div className="dependency-summary"><p>Escolha as tarefas que precisam ser concluídas primeiro.</p><span>{selected.size} selecionada{selected.size===1?'':'s'}</span></div><label className="dependency-search"><Search size={14}/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Buscar por tarefa ou projeto" aria-label="Buscar dependência"/>{query&&<button type="button" className="icon-button" onClick={()=>setQuery('')} aria-label="Limpar busca"><X size={13}/></button>}</label><div className="dependency-list">{visible.map(task=><label className="dependency-option" key={task.id}><input type="checkbox" name="dependency_ids" value={task.id} checked={selected.has(task.id)} onChange={()=>toggle(task.id)}/><span><strong>{task.title}</strong><small>{projects.find(project=>project.id===task.project_id)?.name||'Projeto'} · {statuses[task.status]}</small></span></label>)}{!visible.length&&<div className="dependency-empty">Nenhuma tarefa encontrada.</div>}</div></fieldset>;
}
