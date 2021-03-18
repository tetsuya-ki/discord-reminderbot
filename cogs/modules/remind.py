from datetime import datetime, timedelta, timezone
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
             remind_message: str, status: str, repeat_flg: str,
             repeat_interval: str):
        '''remindを作成'''

        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()

            # raw_channel_mentionsか実行したチャンネル
            # channel = ctx.channel.id

            # TODO:一旦は無効にする！
            # if len(ctx.message.raw_channel_mentions) > 0:
            #     channel = ctx.message.raw_channel_mentions[0]
            # raw_mentions, raw_role_mentions, mention_everyone(@here, @everyone)のやつ
            mention = None

            # TODO:一旦は無効にする！
            # if ctx.message.mention_everyone:
            #     mention = '@here'
            # elif len(ctx.message.raw_role_mentions) > 0:
            #     mention = str(ctx.message.raw_role_mentions[0])
            # elif len(ctx.message.raw_mentions) > 0:
            #     mention = str(ctx.message.raw_mentions[0])
            JST = timezone(timedelta(hours=+9), 'JST')
            now = datetime.datetime.now(JST)

            insert_sql = 'INSERT INTO reminder_table (remind_datetime,guild,member,channel,remind_message,status,mention,repeat_flg,repeat_interval,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
            remind_param = (remind_datetime, ctx.guild.id, ctx.author.id,
                            ctx.channel.id, remind_message, status, mention,
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
            logger.info(rows)
            return rows

    def list_all(self, ctx: commands.Context):
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = 'select * from reminder_table order by remind_datetime'
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            logger.info(rows)
            return rows
