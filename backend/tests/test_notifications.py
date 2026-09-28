import unittest
from datetime import date

from app.notifications import mark_notified, notification_events


class NotificationRulesTest(unittest.TestCase):
    def task(self, task_id, title, due_date='', status='todo', dependency_ids=None):
        return {'id': task_id, 'title': title, 'due_date': due_date, 'status': status,
                'is_archived': False, 'dependency_ids': dependency_ids or []}

    def test_deadlines_are_classified_and_not_repeated(self):
        board = {'tasks': [
            self.task(1, 'Atrasada', '2026-09-20'), self.task(2, 'Hoje', '2026-09-28'),
            self.task(3, 'Em breve', '2026-10-01'), self.task(4, 'Depois', '2026-10-02'),
            self.task(5, 'Concluída', '2026-09-20', 'done'),
        ]}
        events, state = notification_events(board, {}, date(2026, 9, 28))
        self.assertEqual([event['title'] for event in events], ['Tarefa atrasada', 'Prazo para hoje', 'Prazo se aproximando'])
        for event in events:
            mark_notified(state, event['key'])
        repeated, _ = notification_events(board, state, date(2026, 9, 28))
        self.assertEqual(repeated, [])

    def test_unlock_is_reported_only_after_initial_snapshot(self):
        blocked = {'tasks': [self.task(1, 'Pré-requisito'), self.task(2, 'Entrega', dependency_ids=[1])]}
        events, state = notification_events(blocked, {}, date(2026, 9, 28))
        self.assertFalse(any(event['title'] == 'Tarefa desbloqueada' for event in events))
        blocked['tasks'][0]['status'] = 'done'
        events, _ = notification_events(blocked, state, date(2026, 9, 28))
        self.assertEqual([(event['title'], event['task_id']) for event in events], [('Tarefa desbloqueada', 2)])
