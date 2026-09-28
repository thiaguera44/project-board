import type { Board, Settings } from './types';

export const statuses:Record<string,string>={todo:'A fazer',doing:'Fazendo',waiting:'Em aguardo',done:'Concluído'};
export const priorities:Record<string,string>={critical:'Crítica',high:'Alta',medium:'Média',low:'Baixa'};
export const recurrences:Record<string,string>={none:'Não repetir',daily:'Todos os dias',weekly:'Toda semana',monthly:'Todo mês'};
export const chartColors=['#e47b72','#e4b45d','#7399cd','#8db5a0'];
export const emptyBoard:Board={projects:[],tasks:[],archived_projects:[],archived_tasks:[],checklist_items:[],comments:[],attachments:[],labels:[],entries:[],history:[],active_timers:[]};
export const defaultSettings:Settings={board_name:'project-board',theme:'azul',appearance:'light',notifications_enabled:true};
export const themes:Record<Settings['theme'],{name:string;color:string}>={azul:{name:'Azul',color:'#375d79'},verde:{name:'Verde',color:'#47705a'},roxo:{name:'Roxo',color:'#665482'},terracota:{name:'Terracota',color:'#965f4e'},grafite:{name:'Grafite',color:'#4f5965'}};

export const formatDate=(value:string)=>value?new Date(value+'T12:00:00').toLocaleDateString('pt-BR',{day:'2-digit',month:'short'}):'Sem prazo';
export const deadlineLabel=(days:number)=>days<0?`${Math.abs(days)} ${Math.abs(days)===1?'dia':'dias'} em atraso`:days===0?'Vence hoje':days===1?'Vence amanhã':`Vence em ${days} dias`;
export const initials=(name:string)=>name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0].toLocaleUpperCase('pt-BR')).join('')||'?';
export const clockTime=(seconds:number)=>[Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(value=>String(value).padStart(2,'0')).join(':');
