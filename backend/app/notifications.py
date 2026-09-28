from __future__ import annotations

from datetime import date


def notification_events(board: dict, state: dict, today: date) -> tuple[list[dict], dict]:
    tasks = [task for task in board.get('tasks', []) if not task.get('is_archived')]
    tasks_by_id = {task['id']: task for task in tasks}
    current_blocked = {
        task['id'] for task in tasks
        if task.get('status') != 'done' and any(
            tasks_by_id.get(dependency_id, {}).get('status') != 'done'
            for dependency_id in task.get('dependency_ids', [])
        )
    }
    notified = set(state.get('notified', []))
    events: list[dict] = []

    for task in tasks:
        if task.get('status') == 'done' or not task.get('due_date'):
            continue
        try:
            due = date.fromisoformat(task['due_date'])
        except (TypeError, ValueError):
            continue
        days = (due - today).days
        if days < 0:
            kind, title, message = 'overdue', 'Tarefa atrasada', f"{task['title']} venceu em {due.strftime('%d/%m/%Y')}."
        elif days == 0:
            kind, title, message = 'today', 'Prazo para hoje', f"{task['title']} vence hoje."
        elif days <= 3:
            kind, title, message = 'soon', 'Prazo se aproximando', f"{task['title']} vence em {days} {'dia' if days == 1 else 'dias'}."
        else:
            continue
        key = f"deadline:{task['id']}:{task['due_date']}:{kind}"
        if key not in notified:
            events.append({'key': key, 'title': title, 'message': message, 'task_id': task['id']})

    if state.get('initialized'):
        for task_id in set(state.get('blocked_task_ids', [])) - current_blocked:
            task = tasks_by_id.get(task_id)
            if not task or task.get('status') == 'done':
                continue
            key = f"unlocked:{task_id}:{today.isoformat()}"
            if key not in notified:
                events.append({'key': key, 'title': 'Tarefa desbloqueada', 'message': f"{task['title']} já pode ser concluída.", 'task_id': task_id})

    next_state = {
        'initialized': True,
        'blocked_task_ids': sorted(current_blocked),
        'notified': list(state.get('notified', []))[-1999:],
    }
    return events, next_state


def mark_notified(state: dict, key: str) -> dict:
    notified = [item for item in state.get('notified', []) if item != key]
    state['notified'] = (notified + [key])[-2000:]
    return state
