import { Link2 } from 'lucide-react';
import type { Task } from './types';

export default function RunrunBadge({task,compact=false}:{task:Task;compact?:boolean}){
 if(!task.runrunit_id)return null;
 const linked=task.runrunit_origin==='linked';
 const label=linked?'Vinculada ao Runrun.it':'Importada do Runrun.it';
 return <span className={`runrun-origin-badge ${linked?'linked':'imported'}${compact?' compact':''}`} title={label} aria-label={label}>
  <i aria-hidden="true">R</i>{linked&&<Link2 size={10}/>} {!compact&&<span>{linked?'Vinculada':'Runrun.it'}</span>}
 </span>;
}
