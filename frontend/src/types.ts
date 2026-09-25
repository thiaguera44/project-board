export type Project={id:number;name:string;description:string;is_archived:boolean};
export type Task={id:number;title:string;project_id:number;status:string;priority:string;assignee:string;due_date:string;estimated_hours:number;is_archived:boolean};
export type Entry={id:number;task_id:number;task_title:string;hours:number;note:string;created_at:string};
export type Movement={id:number;task_title:string;old_status:string;new_status:string;created_at:string};
export type ActiveTimer={task_id:number;started_at:string;elapsed_seconds:number;paused_at:string|null};
export type ChecklistItem={id:number;task_id:number;title:string;is_done:boolean;created_at:string};
export type Board={projects:Project[];tasks:Task[];archived_projects:Project[];archived_tasks:Task[];checklist_items:ChecklistItem[];entries:Entry[];history:Movement[];active_timers:ActiveTimer[]};
export type Settings={board_name:string;theme:'azul'|'verde'|'roxo'|'terracota'|'grafite';appearance:'light'|'dark'};
