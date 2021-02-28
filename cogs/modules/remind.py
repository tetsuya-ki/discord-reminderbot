from discord.ext import commands
from os.path import join, dirname
from logging import getLogger

import datetime, discord, sqlite3, os
logger = getLogger(__name__)

class Remind:
    DATABASE = 'reminder.db'
    FILE_PATH = join(dirname(__file__), 'files' + os.sep + DATABASE)

    def __init__(self):
        self.remind_date = None # リマインドする日付
        self.remind_time = None # リマインドする時刻
        self.remind_message = '' # リマインドするメッセージ
        self.remind_mention = None # リマインド時のメンション
        self.repeat = False # 繰り返しするかどうか
        self.repeat_interval = None


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
        logger.info('準備完了')

    def make(self, ctx:commands.Context, remind_datetime:datetime, remind_message:str, status:str, repeat_flg:str, repeat_interval:str):
        '''remindを作成'''

        conn = sqlite3.connect(self.FILE_PATH)
        cur = conn.cursor()

        # raw_channel_mentionsか実行したチャンネル
        channel = ctx.channel.id
        if len(ctx.message.raw_channel_mentions) > 0:
            channel = ctx.message.raw_channel_mentions[0]
        # raw_mentions, raw_role_mentions, mention_everyone(@here, @everyone)のやつ
        mention = None
        if ctx.message.mention_everyone:
            mention = '@here'
        elif len(ctx.message.raw_role_mentions) > 0:
            mention = str(ctx.message.raw_role_mentions[0])
        elif len(ctx.message.raw_mentions) > 0:
            mention = str(ctx.message.raw_mentions[0])
        now = datetime.datetime.now()

        insert_sql = 'INSERT INTO reminder_table (remind_datetime,guild,member,channel,remind_message,status,mention,repeat_flg,repeat_interval,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
        remind_param = (remind_datetime, ctx.guild.id,ctx.author.id, ctx.channel.id, remind_message, status, mention, repeat_flg, repeat_interval, now, now)

        # Insert a row of data
        cur.execute(insert_sql, remind_param)
        conn.commit()

    def list(self, ctx:commands.Context):
        conn = sqlite3.connect(self.FILE_PATH)
        cur = conn.cursor()
        select_sql = f'''select * from reminder_table where guild = '{ctx.guild.id}' and member = '{ctx.author.id}' order by remind_datetime'''
        cur.execute(select_sql)
        rows = cur.fetchmany(100)
        logger.info(rows)
