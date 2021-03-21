from datetime import timedelta, timezone
from discord.ext import commands
from os.path import join, dirname
from logging import getLogger

import datetime, discord, sqlite3, os
logger = getLogger(__name__)

class Remind:
    DATABASE = 'reminder.db'
    FILE_PATH = join(dirname(__file__), 'files' + os.sep + DATABASE)

    def __init__(self):
        self.remind_date = None  # リマインドする日付
        self.remind_time = None  # リマインドする時刻
        self.remind_message = ''  # リマインドするメッセージ
        self.remind_mention = None  # リマインド時のメンション
        self.repeat = False  # 繰り返しするかどうか
        self.repeat_interval = None
        self.remind_rows = None  # リマインドの結果

    def prepare(self):
        '''
        sqlite3のdbを準備する
        '''
        conn = sqlite3.connect(self.FILE_PATH)
        cur = conn.cursor()

        create_table_sql = '''
                            create table if not exists reminder_table (
                                id integer primary key autoincrement,
                                remind_datetime datetime,
                                guild integer,
                                member integer,
                                channel integer,
                                remind_message text,
                                status text,
                                mention text,
                                repeat_flg text,
                                repeat_interval text,
                                created_at datetime,
                                updated_at datetime
                            )
                            '''
        cur.execute(create_table_sql)
        conn.commit()
        self.read()
        logger.info('準備完了')

    def read(self):
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = '''select * from reminder_table where status = 'Progress' order by remind_datetime'''
            cur.execute(select_sql)
            self.remind_rows = cur.fetchmany(100)
            logger.info(self.remind_rows)

    def make(self, ctx: commands.Context, remind_datetime: datetime,
            remind_message: str, channel: int, status: str, repeat_flg: str,
            repeat_interval: str):
        '''remindを作成'''

        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()

            mention = None
            JST = timezone(timedelta(hours=+9), 'JST')
            now = datetime.datetime.now(JST)

            insert_sql = 'INSERT INTO reminder_table (remind_datetime,guild,member,channel,remind_message,status,mention,repeat_flg,repeat_interval,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
            remind_param = (remind_datetime, ctx.guild.id, ctx.author.id,
                            channel, remind_message, status, mention,
                            repeat_flg, repeat_interval, now, now)

            # Insert a row of data
            cur.execute(insert_sql, remind_param)
            conn.commit()

            self.read()

    def delete(self, remind_id: int):
        '''remindを削除'''

        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            JST = timezone(timedelta(hours=+9), 'JST')
            now = datetime.datetime.now(JST)

            remind_param = ('Finished', now, remind_id)
            update_sql = 'update reminder_table set status=?, updated_at = ? where id = ?'
            conn.execute(update_sql, remind_param)
            conn.commit()
            self.read()

    def list(self, ctx: commands.Context):
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''select * from reminder_table where status = 'Progress' and guild = '{ctx.guild.id}' and member = '{ctx.author.id}' order by remind_datetime'''
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = ''
            for row in rows:
                repeat_message = '繰り返す' if row[8] == '1' else '繰り返さない'
                repeat_interval_message = f'({row[9]})' if row[9] is not None else ''
                message += f'No: {row[0]} Remind_datetime: {row[1]}\n'
                message += f'Message: {row[5]}\n'
                message += f'Status: {row[6]} {repeat_message}{repeat_interval_message}\n--\n'

            escaped_mention_text = discord.utils.escape_mentions(message)
            logger.info(escaped_mention_text)
            return escaped_mention_text

    def list_all(self, ctx: commands.Context):
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = 'select * from reminder_table order by remind_datetime'
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = ''
            for row in rows:
                repeat_message = '繰り返す' if row[8] == '1' else '繰り返さない'
                repeat_interval_message = f'({row[9]})' if row[9] is not None else ''
                message += f'No: {row[0]} Remind_datetime: {row[1]}\n'
                message += f'Message: {row[5]}\n'
                message += f'Status: {row[6]} {repeat_message}{repeat_interval_message}\n--\n'
            escaped_mention_text = discord.utils.escape_mentions(message)
            logger.info(escaped_mention_text)
            return escaped_mention_text
