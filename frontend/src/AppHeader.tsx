import { Bell, BellRing, ChevronRight, PanelLeftClose, Search } from 'lucide-react';

type Props={page:string;query:string;profileName:string;alertCount:number;collapsed:boolean;initials:(value:string)=>string;onQuery:(value:string)=>void;onToggle:()=>void;onNotifications:()=>void;onProfile:()=>void};

export default function AppHeader(props:Props){
 return <header><div className="breadcrumb"><button className="icon-button" aria-label="Alternar menu" onClick={props.onToggle}><PanelLeftClose size={19}/></button><span>Workspace</span><ChevronRight size={13}/><strong>{props.page}</strong></div><div className="header-right"><div className="search"><Search size={16}/><input placeholder="Buscar projetos, tarefas..." aria-label="Buscar projetos e tarefas" value={props.query} onChange={e=>props.onQuery(e.target.value)}/><kbd>/</kbd></div><button className="notification-button" aria-label={props.alertCount?`${props.alertCount} avisos de prazo`:'Sem avisos de prazo'} title="Avisos de prazo" onClick={props.onNotifications}>{props.alertCount?<BellRing size={17}/>:<Bell size={17}/>} {props.alertCount>0&&<span>{props.alertCount}</span>}</button><button className="avatar small-avatar avatar-button" aria-label="Editar meu perfil" title={props.profileName||'Meu perfil'} onClick={props.onProfile}>{props.initials(props.profileName)}</button></div></header>;
}
