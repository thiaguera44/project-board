import { formatDuration, durationFromParts } from './duration';
import AppSidebar from './AppSidebar';
import AppHeader from './AppHeader';
import DurationFields from './DurationFields';
import { apiRequest } from './api';
import { ProfileModal, SettingsModal, type UpdateInfo } from './WorkspaceModals';
import { filterReportEntries, reportComparisons, reportCsv, reportDailyHours, reportOverdueTasks } from './report';
import { getDeadlineAlerts } from './deadlines';
import ReportsPage from './ReportsPage';
import LabelsPage from './LabelsPage';
import KanbanTaskCard from './KanbanTaskCard';
import CalendarPage from './CalendarPage';
import RunrunIntegrationPage from './RunrunIntegrationPage';
import RunrunTaskLink from './RunrunTaskLink';
import RunrunBadge from './RunrunBadge';
import DependencyPicker from './DependencyPicker';
import { chartColors as colors, clockTime, deadlineLabel, defaultSettings, emptyBoard as empty, formatDate as fmt, initials, priorities, recurrences, statuses } from './boardConfig';
import type { ActiveTimer, Attachment as TaskAttachment, Board, BoardLabel, ChecklistItem, Entry, Project, Settings, Task, TaskComment } from './types';
import { useEffect, useState, type FormEvent } from 'react';
import { FolderKanban, Columns3, ListTodo, Clock3, History, Plus, ArrowUpRight, ChevronRight, X, Trash2, Pencil, Check, CircleCheck, Play, PlayCircle, Pause, Square, AlertTriangle, Download, Upload, Archive, ArchiveRestore, BellRing, MessageSquare, Paperclip, ExternalLink } from 'lucide-react';
type NativeApi={save_csv?:(name:string,content:string)=>Promise<boolean>;save_pdf?:(name:string,content:string)=>Promise<boolean>;show_timer?:()=>Promise<boolean>;save_backup?:(name:string,content:string)=>Promise<boolean>;load_backup?:()=>Promise<string|null>;open_attachment?:(storedName:string)=>Promise<boolean>;check_update?:()=>Promise<UpdateInfo>;install_update?:(url:string,version:string,digest:string)=>Promise<UpdateInfo>};
const nativeApi=()=>(window as Window & {pywebview?:{api?:NativeApi}}).pywebview?.api;
export default function App(){
 const [board,setBoard]=useState<Board>(empty),[page,setPage]=useState('Dashboard'),[query,setQuery]=useState(''),[project,setProject]=useState(''),[priority,setPriority]=useState(''),[status,setStatus]=useState(''),[labelFilter,setLabelFilter]=useState(''),[modal,setModal]=useState<{kind:string;task?:Task;project?:Project;entry?:Entry;label?:BoardLabel;status?:string}|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[collapsed,setCollapsed]=useState(false);
 const [profileName,setProfileName]=useState(''),[profileOpen,setProfileOpen]=useState(false),[profileBusy,setProfileBusy]=useState(false),[profileError,setProfileError]=useState('');
 const [settings,setSettings]=useState<Settings>(defaultSettings),[settingsOpen,setSettingsOpen]=useState(false),[settingsBusy,setSettingsBusy]=useState(false),[settingsError,setSettingsError]=useState('');
 const [reportFrom,setReportFrom]=useState(''),[reportTo,setReportTo]=useState(''),[reportProject,setReportProject]=useState('');
 const [checklistDraft,setChecklistDraft]=useState('');
 const [commentDraft,setCommentDraft]=useState('');
 const [notificationsOpen,setNotificationsOpen]=useState(false);
 const [newTaskDate,setNewTaskDate]=useState('');
 const [nowMs,setNowMs]=useState(Date.now());
 const [updateInfo,setUpdateInfo]=useState<UpdateInfo>({status:'idle'});
 async function refresh(){try{const [nextBoard,profile,nextSettings]=await Promise.all([apiRequest('/board'),apiRequest('/profile'),apiRequest('/settings')]);setBoard(nextBoard);setProfileName(profile.display_name);setSettings(nextSettings);document.title=nextSettings.board_name;if(!profile.display_name)setProfileOpen(true);setError('')}catch{setError('Não foi possível conectar à API. Inicie o backend e tente novamente.')}finally{setLoading(false)}}
 useEffect(()=>{void refresh()},[]);
 useEffect(()=>{void checkForUpdate(false)},[]);
 useEffect(()=>{const interval=window.setInterval(()=>{void apiRequest('/board').then(setBoard).catch(()=>{})},5000);return()=>window.clearInterval(interval)},[]);
 useEffect(()=>{if(!board.active_timers.length)return;setNowMs(Date.now());const interval=window.setInterval(()=>setNowMs(Date.now()),1000);return()=>window.clearInterval(interval)},[board.active_timers]);
 useEffect(()=>{setChecklistDraft('');setCommentDraft('')},[modal?.task?.id]);
 async function saveProfile(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  const display_name=String(new FormData(e.currentTarget).get('display_name')||'').trim();
  if(!display_name){setProfileError('Informe seu nome.');return;}
  setProfileBusy(true);setProfileError('');
  try{const profile=await apiRequest('/profile','PUT',{display_name});setProfileName(profile.display_name);setProfileOpen(false)}
  catch(e){setProfileError((e as Error).message)}finally{setProfileBusy(false)}
 }
 async function saveSettings(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  const data=new FormData(e.currentTarget);
  const board_name=String(data.get('board_name')||'').trim();
  const theme=String(data.get('theme')) as Settings['theme'];
  const appearance=String(data.get('appearance')) as Settings['appearance'];
  const notifications_enabled=data.get('notifications_enabled')==='on';
  if(!board_name){setSettingsError('Informe o nome do quadro.');return;}
  setSettingsBusy(true);setSettingsError('');
  try{const saved=await apiRequest('/settings','PUT',{board_name,theme,appearance,notifications_enabled});setSettings(saved);document.title=saved.board_name;setSettingsOpen(false)}
  catch(e){setSettingsError((e as Error).message)}finally{setSettingsBusy(false)}
 }
 async function mutate(path:string,method:string,body?:unknown){setBusy(true);try{await apiRequest(path,method,body);await refresh();setModal(null)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 const tasks=board.tasks.filter(t=>(!project||t.project_id===Number(project))&&(!priority||t.priority===priority)&&(!status||t.status===status)&&(!labelFilter||t.label_ids.includes(Number(labelFilter)))&&[t.title,t.assignee,board.projects.find(p=>p.id===t.project_id)?.name,...t.label_ids.map(id=>board.labels.find(label=>label.id===id)?.name)].join(' ').toLowerCase().includes(query.toLowerCase()));
 const taskHours=(id:number)=>board.entries.filter(e=>e.task_id===id).reduce((s,e)=>s+e.hours,0);
 const totalHours=tasks.reduce((s,t)=>s+taskHours(t.id),0);
 const today=new Date().toLocaleDateString('en-CA');
 const deadlineAlerts=getDeadlineAlerts(board.tasks,today);
 const overdue=tasks.filter(t=>t.due_date&&t.due_date<today&&t.status!=='done').length;
 const done=tasks.filter(t=>t.status==='done').length;
 const projectName=(id:number)=>board.projects.find(p=>p.id===id)?.name||'Projeto';
 const timerForTask=(taskId:number)=>board.active_timers.find(timer=>timer.task_id===taskId);
 const checklistForTask=(taskId:number)=>board.checklist_items.filter(item=>item.task_id===taskId);
 const commentsForTask=(taskId:number)=>board.comments.filter(item=>item.task_id===taskId);
 const attachmentsForTask=(taskId:number)=>board.attachments.filter(item=>item.task_id===taskId);
 const pendingDependencies=(task:Task)=>task.dependency_ids.map(id=>board.tasks.find(item=>item.id===id)).filter(item=>item&&item.status!=='done') as Task[];
 const timerSeconds=(timer:ActiveTimer)=>Math.max(0,Math.floor(timer.elapsed_seconds+(timer.paused_at?0:Math.max(0,(nowMs-new Date(timer.started_at).getTime())/1000))));
 function newTask(s='todo',dueDate=''){if(!board.projects.length){setModal({kind:'project'});return}setNewTaskDate(dueDate);setModal({kind:'task',status:s})}
 function move(t:Task,s:string){if(t.status!==s)void mutate('/tasks/'+t.id,'PUT',{...t,status:s,due_date:t.due_date||null})}
 function startTimer(t:Task){void mutate('/timer/start','POST',{task_id:t.id})}
 function pauseTimer(taskId:number){void mutate('/timer/'+taskId+'/pause','POST')}
 function resumeTimer(taskId:number){void mutate('/timer/'+taskId+'/resume','POST')}
 function stopTimer(taskId:number){void mutate('/timer/'+taskId+'/stop','POST')}
 function discardTimer(taskId:number){if(confirm('Descartar o tempo deste cronômetro sem registrar horas?'))void mutate('/timer/'+taskId,'DELETE')}
 const reportEntries=filterReportEntries(board.entries,board.tasks,reportFrom,reportTo,reportProject);
 async function exportReport(){
  const content=reportCsv(reportEntries,board.tasks,board.projects);
  const filename=`relatorio-${new Date().toLocaleDateString('en-CA')}.csv`;
  const native=nativeApi();
  if(native?.save_csv){try{await native.save_csv(filename,content)}catch{setError('Não foi possível salvar o relatório.')}return;}
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8'}));link.download=filename;link.click();URL.revokeObjectURL(link.href);
 }
 async function openFloatingTimer(){
  const native=nativeApi();
  if(native?.show_timer){try{await native.show_timer()}catch{setError('Não foi possível abrir a janela flutuante.')}return;}
  window.open('/timer','project-board-timers','width=390,height=340');
 }
 async function checkForUpdate(manual=true){
  const native=nativeApi();if(!native?.check_update){if(manual)setUpdateInfo({status:'error',message:'A verificação está disponível no aplicativo para Windows.'});return}
  setUpdateInfo(previous=>({status:'checking',current_version:previous.current_version}));
  try{setUpdateInfo(await native.check_update())}catch{setUpdateInfo({status:'error',message:'Não foi possível consultar novas versões agora.'})}
 }
 async function installUpdate(){
  const native=nativeApi();if(!native?.install_update||!updateInfo.asset_url||!updateInfo.latest_version)return;
  setUpdateInfo(previous=>({...previous,status:'installing'}));
  try{const result=await native.install_update(updateInfo.asset_url,updateInfo.latest_version,updateInfo.asset_digest||'');if(result.status==='error')setUpdateInfo(previous=>({...previous,...result}))}
  catch{setUpdateInfo(previous=>({...previous,status:'error',message:'Não foi possível baixar a atualização.'}))}
 }
 async function exportPdfReport(){
  const comparisons=reportComparisons(board.entries,board.tasks,board.projects,reportFrom,reportTo,reportProject);
  const overdueTasks=reportOverdueTasks(board.tasks,board.projects,today,reportFrom,reportTo,reportProject);
  const daily=reportDailyHours(reportEntries);
  const total=reportEntries.reduce((sum,entry)=>sum+entry.hours,0),estimated=comparisons.reduce((sum,item)=>sum+item.estimated,0);
  const signed=(value:number)=>`${value>0?'+':value<0?'-':''}${formatDuration(Math.abs(value))}`;
  const payload={title:`${settings.board_name} · Relatório`,generated_at:new Date().toLocaleString('pt-BR'),filters:{period:`${reportFrom||'Início'} até ${reportTo||'Hoje'}`,project:board.projects.find(item=>String(item.id)===reportProject)?.name||'Todos os projetos'},summary:[['Tempo realizado',formatDuration(total)],['Tempo estimado',formatDuration(estimated)],['Diferença',signed(total-estimated)],['Tarefas atrasadas',String(overdueTasks.length)]],comparisons:comparisons.map(item=>[item.title,item.project,formatDuration(item.estimated),formatDuration(item.actual),signed(item.difference)]),overdue:overdueTasks.map(item=>[item.title,item.project,new Date(item.due_date+'T12:00:00').toLocaleDateString('pt-BR'),String(item.days)]),productivity:daily.map(item=>[new Date(item.day+'T12:00:00').toLocaleDateString('pt-BR'),formatDuration(item.hours)]),entries:reportEntries.map(entry=>[new Date(entry.created_at).toLocaleDateString('pt-BR'),board.projects.find(item=>item.id===board.tasks.find(task=>task.id===entry.task_id)?.project_id)?.name||'Removido',entry.task_title,entry.note||'',formatDuration(entry.hours)])};
  const native=nativeApi();if(native?.save_pdf){try{await native.save_pdf(`relatorio-${new Date().toLocaleDateString('en-CA')}.pdf`,JSON.stringify(payload))}catch{setError('Não foi possível salvar o relatório em PDF.')}return}window.print();
 }
 async function exportBackup(){
  setSettingsBusy(true);setSettingsError('');
  try{
   const backup=await apiRequest('/backup');
   const content=JSON.stringify(backup,null,2);
   const filename=`project-board-backup-${new Date().toLocaleDateString('en-CA')}.json`;
   const native=nativeApi();
   if(native?.save_backup){await native.save_backup(filename,content);return;}
   const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([content],{type:'application/json'}));link.download=filename;link.click();URL.revokeObjectURL(link.href);
  }catch(e){setSettingsError((e as Error).message||'Não foi possível criar o backup.')}finally{setSettingsBusy(false)}
 }
 async function applyBackup(content:string){
  let backup:unknown;
  try{backup=JSON.parse(content)}catch{throw new Error('O arquivo selecionado não contém um backup JSON válido.')}
  if(!confirm('Restaurar este backup? Os dados atuais serão substituídos pelos dados do arquivo.'))return;
  await apiRequest('/backup/restore','POST',backup);await refresh();setSettingsOpen(false);
 }
 async function importBackup(){
  setSettingsBusy(true);setSettingsError('');
  try{
   const native=nativeApi();
   if(native?.load_backup){const content=await native.load_backup();if(content)await applyBackup(content);return;}
   const input=document.createElement('input');input.type='file';input.accept='.json,application/json';
   const content=await new Promise<string|null>(resolve=>{let settled=false;const finish=(value:string|null)=>{if(settled)return;settled=true;resolve(value)};input.onchange=()=>{const file=input.files?.[0];if(!file){finish(null);return}file.text().then(finish).catch(()=>finish(null))};window.addEventListener('focus',()=>window.setTimeout(()=>finish(null),300),{once:true});input.click()});
   if(content)await applyBackup(content);
  }catch(e){setSettingsError((e as Error).message||'Não foi possível restaurar o backup.')}finally{setSettingsBusy(false)}
 }
 async function addChecklistItem(taskId:number){
  const title=checklistDraft.trim();if(!title)return;
  setBusy(true);setError('');try{await apiRequest('/tasks/'+taskId+'/checklist','POST',{title});setChecklistDraft('');await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function updateChecklistItem(item:ChecklistItem,is_done=item.is_done){
  setBusy(true);setError('');try{await apiRequest('/checklist/'+item.id,'PUT',{title:item.title,is_done});await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function removeChecklistItem(itemId:number){
  setBusy(true);setError('');try{await apiRequest('/checklist/'+itemId,'DELETE');await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function addComment(taskId:number){
  const content=commentDraft.trim();if(!content)return;
  setBusy(true);setError('');try{await apiRequest('/tasks/'+taskId+'/comments','POST',{author:profileName||'Usuário',content});setCommentDraft('');await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function removeComment(comment:TaskComment){
  if(!confirm('Excluir esta anotação?'))return;
  setBusy(true);setError('');try{await apiRequest('/comments/'+comment.id,'DELETE');await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function addAttachment(taskId:number,file:File){
  if(file.size>20*1024*1024){setError('O anexo ultrapassa o limite de 20 MB.');return}
  setBusy(true);setError('');
  try{const dataUrl=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(new Error('Não foi possível ler o arquivo.'));reader.readAsDataURL(file)});await apiRequest('/tasks/'+taskId+'/attachments','POST',{original_name:file.name,content_base64:dataUrl.split(',')[1]||''});await refresh()}
  catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function openAttachment(attachment:TaskAttachment){
  const native=nativeApi();if(native?.open_attachment){if(!await native.open_attachment(attachment.stored_name))setError('Não foi possível abrir o anexo.');return}
  window.open('/api/attachments/'+attachment.id,'_blank');
 }
 async function removeAttachment(attachment:TaskAttachment){
  if(!confirm('Remover este anexo?'))return;setBusy(true);setError('');try{await apiRequest('/attachments/'+attachment.id,'DELETE');await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault();
  const d=Object.fromEntries(new FormData(e.currentTarget));
  if(modal?.kind==='project'){
   await mutate('/projects'+(modal.project?'/'+modal.project.id:''),modal.project?'PUT':'POST',d);
   return;
  }
  if(modal?.kind==='label'){
   await mutate('/labels'+(modal.label?'/'+modal.label.id:''),modal.label?'PUT':'POST',{name:d.name,color:d.color});
   return;
  }
  const {duration_hours,duration_minutes,...fields}=d;
  let duration:number;
  try{duration=durationFromParts(Number(duration_hours),Number(duration_minutes),modal?.kind==='hours'?24:100000,modal?.kind==='hours');}
  catch(e){setError((e as Error).message);return;}
  if(modal?.kind==='hours')await mutate('/entries'+(modal.entry?'/'+modal.entry.id:''),modal.entry?'PUT':'POST',{...fields,task_id:Number(d.task_id),hours:duration});
  else {const form=new FormData(e.currentTarget);await mutate('/tasks'+(modal?.task?'/'+modal.task.id:''),modal?.task?'PUT':'POST',{...fields,project_id:Number(d.project_id),estimated_hours:duration,due_date:d.due_date||null,recurrence_end:d.recurrence_end||null,label_ids:form.getAll('label_ids').map(Number),dependency_ids:form.getAll('dependency_ids').map(Number)});}
 }

 const selectProject=<select aria-label="Filtrar por projeto" value={project} onChange={e=>setProject(e.target.value)}><option value="">Todos os projetos</option>{board.projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select>;
 const taskTable=<div className="table-scroll"><table><thead><tr>{['Tarefa','Projeto','Prioridade','Status','Prazo','Estimadas','Registradas',''].map((s,i)=><th key={i}>{s}</th>)}</tr></thead><tbody>{tasks.map(t=><tr key={t.id}><td><div className="table-task-title"><button className="text-button task-title" onClick={()=>setModal({kind:'task',task:t})}>{t.title}</button><RunrunBadge task={t} compact/></div><small>{t.assignee}{t.recurrence!=='none'?` · ${recurrences[t.recurrence]}`:''}</small></td><td>{projectName(t.project_id)}</td><td><span className={'badge '+t.priority}>{priorities[t.priority]}</span></td><td><span className={'badge '+t.status}>{statuses[t.status]}</span></td><td>{fmt(t.due_date)}</td><td>{formatDuration(t.estimated_hours)}</td><td>{formatDuration(taskHours(t.id))}</td><td><button className="icon-button" aria-label={'Editar '+t.title} onClick={()=>setModal({kind:'task',task:t})}><Pencil size={14}/></button></td></tr>)}</tbody></table>{!tasks.length&&<div className="empty">Nenhuma tarefa encontrada. Crie uma tarefa ou ajuste os filtros.</div>}</div>;
 return <div className={collapsed?'app collapsed':'app'} data-theme={settings.theme} data-mode={settings.appearance}><AppSidebar page={page} boardName={settings.board_name} profileName={profileName} taskCount={board.tasks.length} labels={board.labels} priority={priority} status={status} labelFilter={labelFilter} onPage={setPage} onCustomize={()=>{setSettingsError('');setSettingsOpen(true)}} onProfile={()=>{setProfileError('');setProfileOpen(true)}} onPriority={setPriority} onStatus={setStatus} onLabel={setLabelFilter} onClear={()=>{setPriority('');setStatus('');setProject('');setLabelFilter('');setQuery('')}} initials={initials}/><div className="main"><AppHeader page={page} query={query} profileName={profileName} alertCount={deadlineAlerts.length} collapsed={collapsed} initials={initials} onQuery={setQuery} onToggle={()=>setCollapsed(!collapsed)} onNotifications={()=>setNotificationsOpen(true)} onProfile={()=>{setProfileError('');setProfileOpen(true)}}/><main><div className="page-heading"><div><div className="eyebrow">VISÃO GERAL DO WORKSPACE</div><h1>{page==='Dashboard'?'Tudo sob controle.':page}</h1><p>{page==='Dashboard'?'Seus projetos, prioridades e próximos passos em um só lugar.':page==='Arquivados'?'Itens guardados, preservados e prontos para restaurar.':page==='Integrações'?'Conecte seu quadro a outros serviços.':'Organize seu trabalho e acompanhe cada etapa.'}</p></div>{page!=='Arquivados'&&page!=='Relatórios'&&page!=='Integrações'&&<button className="primary" onClick={()=>page==='Projetos'?setModal({kind:'project'}):page==='Horas registradas'?setModal({kind:'hours'}):page==='Relatórios'?void exportReport():page==='Etiquetas'?setModal({kind:'label'}):newTask()} disabled={loading || (page==='Horas registradas'&&!board.tasks.length) || (page==='Relatórios'&&!reportEntries.length)}>{page==='Relatórios'?<Download size={16}/>:<Plus size={16}/>} {page==='Projetos'?'Novo projeto':page==='Horas registradas'?'Registrar horas':page==='Relatórios'?'Exportar CSV':page==='Etiquetas'?'Nova etiqueta':'Nova tarefa'}</button>}</div>{updateInfo.status==='ok'&&updateInfo.available&&<div className="update-banner"><div><strong>Nova versão {updateInfo.latest_version} disponível</strong><span>Atualize o aplicativo para receber as melhorias mais recentes.</span></div>{updateInfo.download_ready?<button className="primary" onClick={()=>void installUpdate()}><Download size={15}/> Baixar e instalar</button>:updateInfo.release_url&&<button onClick={()=>window.open(updateInfo.release_url,'_blank')}><ExternalLink size={15}/> Abrir no GitHub</button>}</div>}{error&&<div role="alert" className="error">{error}<button onClick={()=>void refresh()}>Tentar novamente</button></div>}{loading?<div className="empty">Carregando seu workspace…</div>:<>
 {(page==='Dashboard')&&<>{deadlineAlerts.length>0&&<button className="deadline-banner" onClick={()=>setNotificationsOpen(true)}><span className="deadline-banner-icon"><BellRing size={18}/></span><span><strong>{deadlineAlerts.length} {deadlineAlerts.length===1?'prazo precisa':'prazos precisam'} da sua atenção</strong><small>{deadlineAlerts.filter(item=>item.kind==='overdue').length?`${deadlineAlerts.filter(item=>item.kind==='overdue').length} em atraso · `:''}Clique para ver os detalhes.</small></span><ChevronRight size={17}/></button>}<div className="stats">{[
 ['Projetos ativos',new Set(tasks.filter(t=>t.status!=='done').map(t=>t.project_id)).size,FolderKanban,'blue','Com tarefas em aberto'],['Concluídas',done,CircleCheck,'green','Tarefas finalizadas'],['Em andamento',tasks.filter(t=>t.status==='doing').length,Play,'amber','Trabalho em progresso'],['Em aguardo',tasks.filter(t=>t.status==='waiting').length,Clock3,'purple','Aguardando próximo passo'],['Horas registradas',formatDuration(totalHours),Clock3,'blue','Total nas tarefas filtradas'],['Atrasadas',overdue,AlertTriangle,'red','Tarefas fora do prazo']
 ].map(([label,value,Icon,tone,caption])=>{const I=Icon as typeof Clock3;return <section className="stat" key={String(label)}><div className="stat-top"><span>{String(label)}</span><div className={'stat-icon '+tone}><I size={17}/></div></div><strong>{String(value)}</strong><small>{String(caption)}</small></section>})}</div><div className="charts"><section className="panel"><div className="section-heading"><h3>Tarefas por prioridade</h3><span className="subtle">Visão atual</span></div><div className="priority-chart"><div className="donut" style={{background:tasks.length?`conic-gradient(${Object.keys(priorities).map((p,i,arr)=>{const start=arr.slice(0,i).reduce((s,k)=>s+tasks.filter(t=>t.priority===k).length,0)/tasks.length*100;const end=start+tasks.filter(t=>t.priority===p).length/tasks.length*100;return `${colors[i]} ${start}% ${end}%`}).join(',')})`:'#eef1f4'}}><div><strong>{tasks.length}</strong><span>tarefas</span></div></div><div className="legend">{Object.entries(priorities).map(([k,v],i)=><div key={k}><span style={{background:colors[i]}}/>{v}<strong>{tasks.filter(t=>t.priority===k).length}</strong></div>)}</div></div></section><section className="panel"><div className="section-heading"><h3>Horas por projeto</h3><Clock3 size={16}/></div><div className="bars">{board.projects.filter(p=>(!project||p.id===Number(project))&&tasks.some(t=>t.project_id===p.id)).slice(0,5).map(p=>{const hours=tasks.filter(t=>t.project_id===p.id).reduce((s,t)=>s+taskHours(t.id),0);return <div className="bar-column" key={p.id}><span>{formatDuration(hours)}</span><div style={{height:Math.max(3,hours/Math.max(totalHours,1)*110)}}/><small title={p.name}>{p.name}</small></div>})}{!tasks.length&&<p className="subtle">Registre horas para acompanhar seus projetos.</p>}</div></section><section className="panel progress-panel"><div className="section-heading"><h3>Progresso do trabalho</h3><ArrowUpRight size={17}/></div><div className="progress-number">{tasks.length?Math.round(done/tasks.length*100):0}<span>%</span><small>das tarefas concluídas</small></div><div className="progress-track"><div style={{width:`${tasks.length?done/tasks.length*100:0}%`}}/></div><div className="progress-summary"><span><i/>{done} concluídas</span><span>{tasks.length-done} em aberto</span></div></section></div></>}
 {(page==='Dashboard'||page==='Quadro Kanban')&&<section className="panel kanban-panel">
  <div className="section-heading"><div className="title-with-icon"><Columns3 size={18}/><h3>Quadro Kanban</h3><span className="subtle">{tasks.length} tarefas</span></div><div className="kanban-header-actions"><button onClick={()=>void openFloatingTimer()}><Clock3 size={14}/> Janela flutuante</button>{selectProject}</div></div>
  {!!board.active_timers.length&&<div className="timer-list">
   <strong className="timer-list-title"><Clock3 size={16}/> Cronômetros ({board.active_timers.length})</strong>
   {board.active_timers.map(timer=><div className={'timer-banner'+(timer.paused_at?' paused':'')} key={timer.task_id}>
    <div><strong>{board.tasks.find(t=>t.id===timer.task_id)?.title||'Tarefa'}</strong><span>{clockTime(timerSeconds(timer))}{timer.paused_at?' · Pausado':''}</span></div>
    <div className="timer-actions">
     {timer.paused_at?<button disabled={busy} onClick={()=>resumeTimer(timer.task_id)}><PlayCircle size={13}/> Retomar</button>:<button disabled={busy} onClick={()=>pauseTimer(timer.task_id)}><Pause size={13}/> Pausar</button>}
     <button disabled={busy} onClick={()=>stopTimer(timer.task_id)}><Square size={13}/> Parar e registrar</button>
     <button disabled={busy} onClick={()=>discardTimer(timer.task_id)}>Descartar</button>
    </div>
   </div>)}
  </div>}
  <div className="kanban">{Object.entries(statuses).map(([k,v])=><div className={'column '+k} key={k} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();const t=board.tasks.find(t=>t.id===Number(e.dataTransfer.getData('text/plain')));if(t&&!busy)move(t,k)}}><div className="column-heading"><span className="status-dot"/>{v}<span className="count">{tasks.filter(t=>t.status===k).length}</span><button className="icon-button" aria-label={'Adicionar tarefa em '+v} onClick={()=>newTask(k)}><Plus size={14}/></button></div><div className="cards">{tasks.filter(t=>t.status===k).map(t=><KanbanTaskCard key={t.id} task={t} projectName={projectName(t.project_id)} labels={board.labels} checklist={checklistForTask(t.id)} commentCount={commentsForTask(t.id).length} pending={pendingDependencies(t)} timer={timerForTask(t.id)} timerSeconds={timerForTask(t.id)?timerSeconds(timerForTask(t.id)!):0} busy={busy} onEdit={()=>setModal({kind:'task',task:t})} onHours={()=>setModal({kind:'hours',task:t})} onStart={()=>startTimer(t)} onPause={()=>pauseTimer(t.id)} onResume={()=>resumeTimer(t.id)} onStop={()=>stopTimer(t.id)}/>)}{!tasks.some(t=>t.status===k)&&<div className="column-empty">Arraste uma tarefa para cá</div>}</div><button className="add-task" onClick={()=>newTask(k)}><Plus size={14}/> Adicionar tarefa</button></div>)}</div>
 </section>}
 {(page==='Dashboard'||page==='Tarefas')&&<section className="panel tasks-panel"><div className="section-heading"><div><h3>{page==='Dashboard'?'Tarefas e próximos prazos':'Todas as tarefas'}</h3><p className="subtle">Acompanhe o que precisa da sua atenção.</p></div>{page==='Dashboard'?<button className="text-button link" onClick={()=>setPage('Tarefas')}>Ver todas as tarefas <ArrowUpRight size={14}/></button>:selectProject}</div>{taskTable}</section>}
 {page==='Projetos'&&<div className="project-grid">{board.projects.filter(p=>p.name.toLowerCase().includes(query.toLowerCase())).map(p=><section className="panel project-card" key={p.id}><FolderKanban size={24}/><h2>{p.name}</h2><p>{p.description||'Sem descrição'}</p><small>{board.tasks.filter(t=>t.project_id===p.id).length} tarefas</small><div className="project-actions"><button onClick={()=>{setProject(String(p.id));setPage('Quadro Kanban')}}>Abrir quadro <ArrowUpRight size={14}/></button><button aria-label={'Arquivar '+p.name} title="Arquivar projeto" onClick={()=>{if(confirm('Arquivar este projeto e ocultar suas tarefas das telas principais?'))void mutate('/projects/'+p.id+'/archive','POST')}}><Archive size={15}/></button><button aria-label={'Editar '+p.name} onClick={()=>setModal({kind:'project',project:p})}><Pencil size={15}/></button><button aria-label={'Excluir '+p.name} onClick={()=>{if(confirm('Excluir este projeto?'))void mutate('/projects/'+p.id,'DELETE')}}><Trash2 size={15}/></button></div></section>)}{!board.projects.length&&<section className="panel empty"><FolderKanban size={30}/><h3>Seu próximo projeto começa aqui</h3><p>Crie um projeto para organizar suas primeiras tarefas.</p><button className="primary" onClick={()=>setModal({kind:'project'})}><Plus size={16}/> Criar primeiro projeto</button></section>}</div>}
 {page==='Calendário'&&<CalendarPage tasks={tasks} projects={board.projects} onEdit={task=>setModal({kind:'task',task})} onCreate={date=>newTask('todo',date)}/>}
 {page==='Etiquetas'&&<LabelsPage labels={board.labels} tasks={board.tasks} onCreate={()=>setModal({kind:'label'})} onEdit={label=>setModal({kind:'label',label})} onDelete={label=>{if(confirm('Excluir esta etiqueta? Ela será removida das tarefas.'))void mutate('/labels/'+label.id,'DELETE')}}/>}
 {page==='Horas registradas'&&<section className="panel"><div className="section-heading"><h3>Registro de horas</h3><span>{formatDuration(board.entries.reduce((s,e)=>s+e.hours,0))} no total</span></div>{board.entries.length?board.entries.slice().reverse().map(e=><div className="activity" key={e.id}><Clock3 size={18}/><div><strong>{e.task_title}</strong><p>{e.note||'Sem observação'} · {new Date(e.created_at).toLocaleDateString('pt-BR')}</p></div><b>{formatDuration(e.hours)}</b><div className="entry-actions"><button className="icon-button" aria-label={'Editar registro de '+e.task_title} onClick={()=>setModal({kind:'hours',entry:e})}><Pencil size={14}/></button><button className="icon-button danger-icon" aria-label={'Excluir registro de '+e.task_title} onClick={()=>{if(confirm('Excluir este registro de horas?'))void mutate('/entries/'+e.id,'DELETE')}}><Trash2 size={14}/></button></div></div>):<div className="empty">As horas registradas nas suas tarefas aparecerão aqui.</div>}</section>}
 {page==='Relatórios'&&<ReportsPage entries={board.entries} tasks={board.tasks} projects={board.projects} from={reportFrom} to={reportTo} project={reportProject} onFrom={setReportFrom} onTo={setReportTo} onProject={setReportProject} onExportCsv={()=>void exportReport()} onExportPdf={()=>void exportPdfReport()}/>}
 {page==='Histórico'&&<section className="panel"><div className="section-heading"><h3>Histórico de movimentações</h3><History size={18}/></div>{board.history.length?board.history.slice().reverse().map(h=><div className="activity" key={h.id}><Check size={18}/><div><strong>{h.task_title}</strong><p>{statuses[h.old_status]} → {statuses[h.new_status]}</p></div><small>{new Date(h.created_at).toLocaleString('pt-BR')}</small></div>):<div className="empty">Movimente tarefas no Kanban para começar seu histórico.</div>}</section>}
 {page==='Integrações'&&<RunrunIntegrationPage onImported={refresh}/>}
 {page==='Arquivados'&&<div className="archive-grid"><section className="panel"><div className="section-heading"><div><h3>Projetos arquivados</h3><p className="subtle">Restaure um projeto para devolver suas tarefas ao quadro.</p></div><Archive size={18}/></div>{board.archived_projects.length?board.archived_projects.map(p=><div className="archive-row" key={p.id}><FolderKanban size={18}/><div><strong>{p.name}</strong><p>{p.description||'Sem descrição'}</p></div><button disabled={busy} onClick={()=>void mutate('/projects/'+p.id+'/restore','POST')}><ArchiveRestore size={15}/> Restaurar</button></div>):<div className="empty">Nenhum projeto arquivado.</div>}</section><section className="panel"><div className="section-heading"><div><h3>Tarefas arquivadas</h3><p className="subtle">As horas e o histórico continuam preservados.</p></div><Archive size={18}/></div>{board.archived_tasks.length?board.archived_tasks.map(t=><div className="archive-row" key={t.id}><ListTodo size={18}/><div><strong>{t.title}</strong><p>{projectName(t.project_id)} · {priorities[t.priority]}</p></div><button disabled={busy} onClick={()=>void mutate('/tasks/'+t.id+'/restore','POST')}><ArchiveRestore size={15}/> Restaurar</button></div>):<div className="empty">Nenhuma tarefa arquivada.</div>}</section></div>} </>}<footer>Um passo de cada vez. Um projeto de cada vez.<span>{settings.board_name} © {new Date().getFullYear()}</span></footer></main></div>
 {modal&&<div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget&&!busy)setModal(null)}}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="section-heading"><h2 id="modal-title">{modal.kind==='project'?(modal.project?'Editar projeto':'Novo projeto'):modal.kind==='label'?(modal.label?'Editar etiqueta':'Nova etiqueta'):modal.kind==='hours'?(modal.entry?'Editar registro de horas':'Registrar horas'):modal.task?'Editar tarefa':'Nova tarefa'}</h2><button className="icon-button" aria-label="Fechar" disabled={busy} onClick={()=>setModal(null)}><X size={20}/></button></div><form onSubmit={submit}>{modal.kind==='project'?<><label>Nome do projeto<input autoFocus required maxLength={120} name="name" defaultValue={modal.project?.name} placeholder="Ex.: Website pessoal"/></label><label>Descrição<textarea name="description" maxLength={2000} defaultValue={modal.project?.description} placeholder="Qual é o objetivo deste projeto?"/></label></>:modal.kind==='label'?<><label>Nome da etiqueta<input autoFocus required maxLength={40} name="name" defaultValue={modal.label?.name} placeholder="Ex.: Cliente"/></label><label>Cor<input type="color" name="color" defaultValue={modal.label?.color||'#7399cd'}/></label></>:modal.kind==='hours'?<><label>Tarefa<select name="task_id" defaultValue={modal.entry?.task_id||modal.task?.id} required>{board.tasks.map(t=><option value={t.id} key={t.id}>{t.title}</option>)}</select></label><DurationFields label="Tempo trabalhado" value={modal.entry?.hours||0} maxHours={24}/><label>Data do trabalho<input type="date" name="work_date" required defaultValue={modal.entry?.created_at.slice(0,10)||today}/></label><label>Observação<textarea name="note" maxLength={1000} defaultValue={modal.entry?.note}/></label></>:<><label>Título<input autoFocus name="title" required maxLength={200} defaultValue={modal.task?.title} placeholder="O que precisa ser feito?"/></label><label>Projeto<select name="project_id" defaultValue={modal.task?.project_id||project||board.projects[0]?.id} required>{board.projects.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label><div className="form-grid"><label>Status<select name="status" defaultValue={modal.task?.status||modal.status}>{Object.entries(statuses).map(([k,v])=><option value={k} key={k}>{v}</option>)}</select></label><label>Prioridade<select name="priority" defaultValue={modal.task?.priority||'medium'}>{Object.entries(priorities).map(([k,v])=><option value={k} key={k}>{v}</option>)}</select></label><label>Prazo<input type="date" name="due_date" defaultValue={modal.task?.due_date||newTaskDate}/></label></div><fieldset className="recurrence-fields"><legend>Repetição</legend><div className="form-grid"><label>Frequência<select name="recurrence" defaultValue={modal.task?.recurrence||'none'}>{Object.entries(recurrences).map(([key,label])=><option value={key} key={key}>{label}</option>)}</select></label><label>Repetir até <span className="optional">(opcional)</span><input type="date" name="recurrence_end" defaultValue={modal.task?.recurrence_end}/></label></div><p>A próxima tarefa será criada em “A fazer” quando esta for concluída.</p></fieldset><DurationFields label="Tempo estimado" value={modal.task?.estimated_hours||0} maxHours={100000}/><label>Responsável<input name="assignee" required maxLength={80} defaultValue={modal.task?.assignee||profileName}/></label>{board.labels.length>0&&<fieldset className="task-label-picker"><legend>Etiquetas</legend>{board.labels.map(label=><label className="task-label-option" key={label.id}><input type="checkbox" name="label_ids" value={label.id} defaultChecked={modal.task?.label_ids.includes(label.id)}/><span className="label-dot" style={{background:label.color}}/>{label.name}</label>)}</fieldset>}{board.tasks.some(task=>task.id!==modal.task?.id)&&<DependencyPicker key={modal.task?.id||'new'} tasks={board.tasks} projects={board.projects} currentTask={modal.task}/>}</>}{modal.task&&<RunrunTaskLink task={modal.task} entries={board.entries} onChanged={async()=>{await refresh();setModal(null)}}/>}{modal.task&&<section className="checklist-editor"><div className="checklist-heading"><strong>Checklist</strong><span>{checklistForTask(modal.task.id).filter(item=>item.is_done).length} de {checklistForTask(modal.task.id).length} concluídos</span></div><div className="checklist-items">{checklistForTask(modal.task.id).map(item=><div className="checklist-item" key={item.id}><button type="button" className={item.is_done?'check-toggle done':'check-toggle'} aria-label={(item.is_done?'Reabrir ':'Concluir ')+item.title} disabled={busy} onClick={()=>void updateChecklistItem(item,!item.is_done)}><Check size={13}/></button><span className={item.is_done?'done':''}>{item.title}</span><button type="button" className="icon-button danger-icon" aria-label={'Excluir '+item.title} disabled={busy} onClick={()=>void removeChecklistItem(item.id)}><Trash2 size={13}/></button></div>)}</div><div className="checklist-add"><input value={checklistDraft} maxLength={200} placeholder="Adicionar item ao checklist" aria-label="Novo item do checklist" onChange={e=>setChecklistDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();void addChecklistItem(modal.task!.id)}}}/><button type="button" disabled={busy||!checklistDraft.trim()} onClick={()=>void addChecklistItem(modal.task!.id)}><Plus size={14}/> Adicionar</button></div></section>}{modal.task&&<section className="attachments-editor"><div className="checklist-heading"><strong><Paperclip size={14}/> Anexos</strong><span>{attachmentsForTask(modal.task.id).length}</span></div><div className="attachment-list">{attachmentsForTask(modal.task.id).map(attachment=><div className="attachment-item" key={attachment.id}><Paperclip size={14}/><button type="button" className="attachment-name" onClick={()=>void openAttachment(attachment)}><strong>{attachment.original_name}</strong><small>{attachment.size<1024?attachment.size+' B':attachment.size<1024*1024?(attachment.size/1024).toFixed(1)+' KB':(attachment.size/1024/1024).toFixed(1)+' MB'}</small></button><button type="button" className="icon-button" aria-label={'Abrir '+attachment.original_name} onClick={()=>void openAttachment(attachment)}><ExternalLink size={13}/></button><button type="button" className="icon-button danger-icon" aria-label={'Remover '+attachment.original_name} onClick={()=>void removeAttachment(attachment)}><Trash2 size={13}/></button></div>)}</div><label className="attachment-add"><Upload size={14}/><span>{busy?'Adicionando…':'Adicionar arquivo'}</span><input type="file" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void addAttachment(modal.task!.id,file);e.currentTarget.value=''}}/></label><small className="attachment-help">Documentos e imagens de até 20 MB.</small></section>}{modal.task&&<section className="comments-editor"><div className="checklist-heading"><strong><MessageSquare size={14}/> Anotações</strong><span>{commentsForTask(modal.task.id).length}</span></div><div className="comment-list">{commentsForTask(modal.task.id).slice().reverse().map(comment=><article className="comment-item" key={comment.id}><div><strong>{comment.author}</strong><time>{new Date(comment.created_at).toLocaleString('pt-BR')}</time><button type="button" className="icon-button danger-icon" aria-label="Excluir anotação" disabled={busy} onClick={()=>void removeComment(comment)}><Trash2 size={12}/></button></div><p>{comment.content}</p></article>)}</div><div className="comment-add"><textarea value={commentDraft} maxLength={4000} placeholder="Registre uma atualização, decisão ou observação..." aria-label="Nova anotação" onChange={e=>setCommentDraft(e.target.value)}/><button type="button" disabled={busy||!commentDraft.trim()} onClick={()=>void addComment(modal.task!.id)}><MessageSquare size={14}/> Adicionar anotação</button></div></section>}{error&&<p className="error" role="alert">{error}</p>}<div className="modal-actions">{modal.entry&&<button type="button" className="danger" disabled={busy} onClick={()=>{if(confirm('Excluir este registro de horas?'))void mutate('/entries/'+modal.entry!.id,'DELETE')}}><Trash2 size={15}/> Excluir registro</button>}{modal.task&&<button type="button" disabled={busy} onClick={()=>{if(confirm('Arquivar esta tarefa?'))void mutate('/tasks/'+modal.task!.id+'/archive','POST')}}><Archive size={15}/> Arquivar</button>}{modal.task&&<button type="button" className="danger" disabled={busy} onClick={()=>{if(confirm('Excluir esta tarefa? Os registros de horas serão preservados.'))void mutate('/tasks/'+modal.task!.id,'DELETE')}}><Trash2 size={15}/> Excluir</button>}<button type="button" disabled={busy} onClick={()=>setModal(null)}>Cancelar</button><button className="primary" disabled={busy||modal.kind==='hours'&&!board.tasks.length}>{busy?'Salvando…':'Salvar'}</button></div></form></section></div>}
 {notificationsOpen&&<div className="modal-backdrop" onClick={e=>{if(e.target===e.currentTarget)setNotificationsOpen(false)}}><section className="modal deadline-modal" role="dialog" aria-modal="true" aria-labelledby="notifications-title"><div className="section-heading"><div><h2 id="notifications-title">Avisos de prazo</h2><p className="subtle">Tarefas vencidas ou com prazo nos próximos três dias.</p></div><button className="icon-button" aria-label="Fechar" onClick={()=>setNotificationsOpen(false)}><X size={20}/></button></div>{deadlineAlerts.length?deadlineAlerts.map(alert=><button className={'deadline-row '+alert.kind} key={alert.task.id} onClick={()=>{setNotificationsOpen(false);setModal({kind:'task',task:alert.task})}}><span className="deadline-status"><AlertTriangle size={15}/></span><span><strong>{alert.task.title}</strong><small>{projectName(alert.task.project_id)} · {fmt(alert.task.due_date)}</small></span><b>{deadlineLabel(alert.days)}</b><ChevronRight size={15}/></button>):<div className="empty"><CircleCheck size={28}/><h3>Nenhum prazo próximo</h3><p>As tarefas concluídas e sem prazo não geram avisos.</p></div>}</section></div>} <ProfileModal open={profileOpen} name={profileName} busy={profileBusy} error={profileError} onClose={()=>setProfileOpen(false)} onSubmit={saveProfile}/>
 <SettingsModal open={settingsOpen} settings={settings} busy={settingsBusy} error={settingsError} update={updateInfo} onClose={()=>setSettingsOpen(false)} onSubmit={saveSettings} onBackup={()=>void exportBackup()} onRestore={()=>void importBackup()} onCheckUpdate={()=>void checkForUpdate()} onInstallUpdate={()=>void installUpdate()}/>
 </div>
}
