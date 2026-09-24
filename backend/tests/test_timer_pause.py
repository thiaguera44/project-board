import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import main


class TimerPauseTest(unittest.TestCase):
    def test_migrates_old_timer_and_excludes_paused_time(self):
        engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        started = datetime.now(timezone.utc) - timedelta(seconds=120)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                'CREATE TABLE active_timer (id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, started_at VARCHAR NOT NULL)'
            )
            connection.exec_driver_sql(
                'INSERT INTO active_timer (id, task_id, started_at) VALUES (1, 10, ?)',
                (started.isoformat(),),
            )
            connection.exec_driver_sql(
                'CREATE TABLE workspace_settings (id INTEGER PRIMARY KEY, board_name VARCHAR NOT NULL, theme VARCHAR NOT NULL)'
            )
            connection.exec_driver_sql(
                "INSERT INTO workspace_settings (id, board_name, theme) VALUES (1, 'Quadro legado', 'azul')"
            )

        async def run():
            async with main.lifespan(main.app):
                self.assertEqual(main.get_settings(), {'board_name': 'Quadro legado', 'theme': 'azul', 'appearance': 'light'})
                saved_settings = main.update_settings(
                    main.SettingsInput(board_name='  Quadro da equipe  ', theme='roxo', appearance='dark')
                )
                self.assertEqual(saved_settings['board_name'], 'Quadro da equipe')
                self.assertEqual(saved_settings['theme'], 'roxo')
                self.assertEqual(saved_settings['appearance'], 'dark')
                self.assertEqual(main.get_settings(), {'board_name': 'Quadro da equipe', 'theme': 'roxo', 'appearance': 'dark'})
                with Session(engine) as session:
                    session.add_all([
                        main.Task(id=10, title='Antiga', project_id=1, status='todo', priority='medium',
                                  assignee='Pessoa', due_date='', estimated_hours=0),
                        main.Task(id=11, title='Paralela', project_id=1, status='todo', priority='medium',
                                  assignee='Pessoa', due_date='', estimated_hours=0),
                    ])
                    session.commit()

                paused = main.pause_timer(10)
                self.assertAlmostEqual(paused['elapsed_seconds'], 120, delta=2)
                self.assertIsNotNone(paused['paused_at'])
                self.assertAlmostEqual(
                    main.timer_elapsed_seconds(
                        main.ActiveTimer(**paused), datetime.now(timezone.utc) + timedelta(hours=1)
                    ),
                    paused['elapsed_seconds'],
                    delta=0.01,
                )
                with self.assertRaises(HTTPException) as duplicate:
                    main.pause_timer(10)
                self.assertEqual(duplicate.exception.status_code, 409)

                parallel = main.start_timer(main.TimerInput(task_id=11))
                self.assertIsNone(parallel['paused_at'])
                resumed = main.resume_timer(10)
                self.assertIsNone(resumed['paused_at'])
                with self.assertRaises(HTTPException) as duplicate:
                    main.resume_timer(10)
                self.assertEqual(duplicate.exception.status_code, 409)

                with Session(engine) as session:
                    timer = session.scalar(select(main.ActiveTimer).where(main.ActiveTimer.task_id == 10))
                    timer.started_at = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
                    session.commit()
                entry = main.stop_timer(10)
                self.assertAlmostEqual(entry['hours'], 3 / 60)
                self.assertEqual(entry['task_title'], 'Antiga')
                self.assertEqual(len(main.board()['active_timers']), 1)
                self.assertEqual(main.board()['active_timers'][0]['task_id'], 11)

        try:
            with patch.object(main, 'engine', engine):
                asyncio.run(run())
        finally:
            engine.dispose()


if __name__ == '__main__':
    unittest.main()
