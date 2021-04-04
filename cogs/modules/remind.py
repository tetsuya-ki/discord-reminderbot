from datetime import timedelta, timezone
from discord.ext import commands
from os.path import join, dirname
from logging import getLogger
from .aes_angou import Aes_angou
from . import setting

import datetime, discord, sqlite3, os
LOG = getLogger('reminderbot')

class Remind:
    DATABASE = 'reminder.db'
    FILE_PATH = join(dirname(__file__), 'files' + os.sep + DATABASE)
    STATUS_FINISHED = 'Finished'
    STATUS_CANCELED = 'Canceled'

    def __init__(self):
        self.remind_date = None  # リマインドする日付
        self.remind_time = None  # リマインドする時刻
        self.remind_message = ''  # リマインドするメッセージ
        self.remind_mention = None  # リマインド時のメンション
        self.repeat = False  # 繰り返しするかどうか
        self.repeat_interval = None
        self.remind_rows = None  # リマインドの結果
        self.aes = Aes_angou(setting.DISCORD_TOKEN)

    def prepare(self):
        '''
        sqlite3のdbを準備する
        '''
        if not os.path.exists(self.aes.ENC_FILE_PATH):
            conn = sqlite3.connect(self.FILE_PATH)
            with conn:
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
                                        repeat_count integer,
                                        repeat_max_count integer,
                                        repeat_flg text,
                                        repeat_interval text,
                                        created_at datetime,
                                        updated_at datetime
                                    )
                                    '''
                cur.execute(create_table_sql)
        else:
            self.decode()
        self.read()
        self.encode()
        LOG.info('準備完了')

    def decode(self):
        if os.path.exists(self.aes.ENC_FILE_PATH):
            self.aes.decode()
            os.remove(self.aes.ENC_FILE_PATH)

    def encode(self):
        if os.path.exists(self.aes.DEC_FILE_PATH):
            self.aes.encode()
            if setting.KEEP_DECRYPTED_FILE:
                os.remove(self.aes.DEC_FILE_PATH)

    def read(self):
        # readはdecodeしない
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = '''select * from reminder_table where status = 'Progress' order by remind_datetime'''
            cur.execute(select_sql)
            self.remind_rows = cur.fetchmany(100)
            LOG.info(f'＊＊＊＊＊＊読み込みが完了しました＊＊＊＊＊＊\n{self.remind_rows}')

    def make(self, guild_id, author_id, remind_datetime: datetime,
            remind_message: str, channel: int, status: str, repeat_flg: str,
            repeat_interval: str, repeat_count: int=1, repeat_max_count:int=None):
        '''remindを作成'''
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        id = None
        with conn:
            cur = conn.cursor()

            JST = timezone(timedelta(hours=+9), 'JST')
            now = datetime.datetime.now(JST)

            insert_sql = 'INSERT INTO reminder_table (remind_datetime,guild,member,channel,remind_message,status,repeat_count,repeat_max_count,repeat_flg,repeat_interval,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)'
            remind_param = (remind_datetime, guild_id, author_id,
                            channel, remind_message, status, repeat_count, repeat_max_count,
                            repeat_flg, repeat_interval, now, now)

            # Insert a row of data
            cur.execute(insert_sql, remind_param)

            # get id
            get_id_sql = 'select id from reminder_table where rowid = last_insert_rowid()'
            cur.execute(get_id_sql)
            id = cur.fetchone()[0]
            LOG.debug(f'id:{id}を追加しました')
            conn.commit()
            self.read()
        self.encode()
        return id

    def update_status(self, remind_id: int, status: str=STATUS_FINISHED):
        '''remindのステータスを変更'''
        self.decode()

        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            JST = timezone(timedelta(hours=+9), 'JST')
            now = datetime.datetime.now(JST)

            remind_param = (status, now, remind_id)
            update_sql = 'update reminder_table set status=?, updated_at = ? where id = ?'
            conn.execute(update_sql, remind_param)
            LOG.info(f'id:{remind_id}を{status}にしました')
        self.read()
        self.encode()

    def list(self, ctx: commands.Context):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''select * from reminder_table where status = 'Progress' and guild = '{ctx.guild.id}' and member = '{ctx.author.id}' order by remind_datetime'''
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = ''
            for row in rows:
                repeat_message = '繰り返す' if row[9] == '1' else '繰り返さない'
                repeat_interval_message = f'({row[10]})' if row[10] is not None else ''
                message += f'No: {row[0]} Remind_datetime: {row[1]}\n'
                message += f'Message: {row[5]}\n'
                message += f'Status: {row[6]} {repeat_message}{repeat_interval_message}\n--\n'

            escaped_mention_text = '(データがありません)' if len(message) == 0 else discord.utils.escape_mentions(message)
            LOG.info(escaped_mention_text)
        self.encode()
        return escaped_mention_text

    def list_all(self, ctx: commands.Context):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = 'select * from reminder_table order by updated_at desc'
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = ''
            for row in rows:
                repeat_message = '繰り返す' if row[9] == '1' else '繰り返さない'
                repeat_interval_message = f'({row[10]})' if row[10] is not None else ''
                message += f'No: {row[0]} Remind_datetime: {row[1]}\n'
                message += f'Message: {row[5]}\n'
                message += f'Status: {row[6]} {repeat_message}{repeat_interval_message}\n--\n'
            escaped_mention_text = '(データがありません)' if len(message) == 0 else discord.utils.escape_mentions(message)
            LOG.info(escaped_mention_text)
        self.encode()
        chopped_escaped_mention_text = escaped_mention_text[:1900] + ('...(省略)...' if escaped_mention_text[1900:] else '')
        return chopped_escaped_mention_text

    def get(self, ctx: commands.Context, id: int):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''select * from reminder_table where status = 'Progress' and member = '{ctx.author.id}' and id = '{id}' '''
            cur.execute(select_sql)
            row = cur.fetchone()
            escaped_mention_text = '(データがありません)' if row is None else discord.utils.escape_mentions(str(row))
            LOG.info(escaped_mention_text)
        self.encode()
        return row