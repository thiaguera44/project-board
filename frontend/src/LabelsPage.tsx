import { Pencil, Plus, Tags, Trash2 } from 'lucide-react';
import type { BoardLabel, Task } from './types';

type Props={
 labels:BoardLabel[];
 tasks:Task[];
 onCreate:()=>void;
 onEdit:(label:BoardLabel)=>void;
 onDelete:(label:BoardLabel)=>void;
};

export default function LabelsPage({labels,tasks,onCreate,onEdit,onDelete}:Props){
 return <section className="panel labels-panel">
  <div className="section-heading"><div><h3>Etiquetas do quadro</h3><p className="subtle">Crie categorias visuais e use o filtro rápido para localizar tarefas.</p></div><Tags size={18}/></div>
  {labels.length?<div className="label-list">{labels.map(label=><div className="label-row" key={label.id}>
   <span className="label-dot" style={{background:label.color}}/><strong>{label.name}</strong><small>{tasks.filter(task=>task.label_ids.includes(label.id)).length} tarefas</small>
   <button className="icon-button" aria-label={'Editar '+label.name} onClick={()=>onEdit(label)}><Pencil size={14}/></button>
   <button className="icon-button danger-icon" aria-label={'Excluir '+label.name} onClick={()=>onDelete(label)}><Trash2 size={14}/></button>
  </div>)}</div>:<div className="empty"><Tags size={28}/><h3>Nenhuma etiqueta criada</h3><p>Crie etiquetas para organizar tarefas por assunto, cliente ou contexto.</p><button className="primary" onClick={onCreate}><Plus size={15}/> Criar etiqueta</button></div>}
 </section>;
}
