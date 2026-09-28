export async function apiRequest(path:string,method='GET',body?:unknown){
 let response:Response;
 try{response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})}
 catch{throw new Error('Sem conexão com o aplicativo. Verifique se ele está aberto e tente novamente.')}
 if(!response.ok){const error=await response.json().catch(()=>null);throw new Error(typeof error?.detail==='string'?error.detail:'Não foi possível salvar. Verifique os campos.')}
 return response.json();
}
