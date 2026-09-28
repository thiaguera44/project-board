from calendar import monthrange
from datetime import date, timedelta


def next_recurrence_date(current:date,recurrence:str):
    if recurrence=='daily': return current+timedelta(days=1)
    if recurrence=='weekly': return current+timedelta(days=7)
    if recurrence=='monthly':
        year,month=(current.year+1,1) if current.month==12 else (current.year,current.month+1)
        return date(year,month,min(current.day,monthrange(year,month)[1]))
    return None


def graph_has_cycle(graph:dict[int,list[int]]):
    def visit(node:int,path:set[int]):
        if node in path: return True
        return any(visit(next_id,path|{node}) for next_id in graph.get(node,[]))
    return any(visit(node,set()) for node in graph)


def dependency_change_creates_cycle(links:list[tuple[int,int]],task_id:int,dependency_ids:list[int]):
    graph:dict[int,list[int]]={}
    for source,target in links:
        if source!=task_id: graph.setdefault(source,[]).append(target)
    graph[task_id]=dependency_ids
    return graph_has_cycle(graph)
