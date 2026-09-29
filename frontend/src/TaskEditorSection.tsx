import type { ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';

type Props={
 title:string;
 description?:string;
 count?:string|number;
 icon?:ReactNode;
 defaultOpen?:boolean;
 children:ReactNode;
 className?:string;
};

export default function TaskEditorSection({title,description,count,icon,defaultOpen=false,children,className=''}:Props){
 return <details className={`task-editor-section ${className}`.trim()} open={defaultOpen}>
  <summary>
   <span className="task-section-icon">{icon}</span>
   <span className="task-section-copy"><strong>{title}</strong>{description&&<small>{description}</small>}</span>
   {count!==undefined&&<span className="task-section-count">{count}</span>}
   <ChevronDown className="task-section-chevron" size={16}/>
  </summary>
  <div className="task-section-content">{children}</div>
 </details>;
}
