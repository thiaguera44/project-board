import { splitDuration } from './duration';

export default function DurationFields({label,value=0,maxHours}:{label:string;value?:number;maxHours:number}){
 const parts=splitDuration(value);
 return <fieldset className="duration-fields"><legend>{label}</legend><div className="form-grid"><label>Horas<input type="number" name="duration_hours" required min="0" max={maxHours} step="1" defaultValue={parts.hours}/></label><label>Minutos<input type="number" name="duration_minutes" required min="0" max="59" step="1" defaultValue={parts.minutes}/></label></div></fieldset>;
}
