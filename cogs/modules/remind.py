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
    JST = timezone(timedelta(hours=+9), 'JST')
    REMIND_CONTROL_CHANNEL = 'remind_control_channel'

    def __init__(self, bot):
        self.bot = bot
        self.remind_date = None  # リマインドする日付
        self.remind_time = None  # リマインドする時刻
        self.remind_message = ''  # リマインドするメッセージ
        self.remind_mention = None  # リマインド時のメンション
        self.repeat = False  # 繰り返しするかどうか
        self.repeat_interval = None
        self.remind_rows = None  # リマインドの結果
        self.aes = Aes_angou(setting.DISCORD_TOKEN)

    async def prepare(self):
        '''
        sqlite3のdbを準備する
        '''
        # Herokuの時のみ、チャンネルからファイルを取得する
        await self.get_discord_attachment_file()

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

    async def get_discord_attachment_file(self):
        # HerokuかRepl.itの時のみ実施
        if setting.IS_HEROKU or setting.IS_REPLIT:
            # 環境変数によって、添付ファイルのファイル名を変更する
            file_name = self.DATABASE if setting.KEEP_DECRYPTED_FILE else self.aes.ENC_FILE
            LOG.debug('Heroku mode.start get_discord_attachment_file.')
            # ファイルをチェックし、存在しなければ最初と見做す
            file_path_first_time = join(dirname(__file__), 'files' + os.sep + 'first_time')
            if (setting.IS_HEROKU and not os.path.exists(file_path_first_time)) or setting.IS_REPLIT:
                with open(file_path_first_time, 'w') as f:
                    now = datetime.datetime.now()
                    f.write((now.astimezone(self.JST)).strftime('%Y/%m/%d(%a) %H:%M:%S'))
                    LOG.debug(f'{file_path_first_time}が存在しないので、作成を試みます')
                Attachment_file_date = None

                # BotがログインしているGuildごとに繰り返す
                for guild in self.bot.guilds:
                    # チャンネルのチェック
                    LOG.debug(f'{guild}: チャンネル読み込み')
                    get_control_channel = discord.utils.get(guild.text_channels, name=self.REMIND_CONTROL_CHANNEL)
                    if get_control_channel is not None:
                        messages = await get_control_channel.history(limit=20).flatten()

                        for message in messages:
                            if len(message) != 0:
                                LOG.debug(f'len: {len(message)}, con: {message[0].content}, attchSize:{len(message[0].attachments)}')
                                if Attachment_file_date is not None:
                                    LOG.debug(f'date: {Attachment_file_date} <<<<<<< {message[0].created_at}, {Attachment_file_date < message[0].created_at}')
                            # messageがない場合以外で、file_nameが本文である場合、ファイルを取得する
                            if len(message) != 0 and message[0].content == file_name:
                                if len(message[0].attachments) > 0:
                                    # 日付が新しい場合、ファイルを取得
                                    if Attachment_file_date is None or Attachment_file_date < message[0].created_at:
                                        Attachment_file_date = message[0].created_at
                                        file_path = join(dirname(__file__), 'files' + os.sep + file_name)
                                        await message[0].attachments[0].save(file_path)
                                        LOG.info(f'channel_file_save:{guild.name}')
                                        break
                    else:
                        LOG.warning(f'{guild}: に所定のチャンネルがありません')
            else:
                LOG.debug(f'{file_path_first_time}が存在します')

            LOG.debug('get_discord_attachment_file is over!')

    async def set_discord_attachment_file(self, guild):
        # HerokuかRepl.itの時のみ実施
        if setting.IS_HEROKU or setting.IS_REPLIT:
            # 環境変数によって、添付ファイルのファイル名を変更する
            file_name = self.DATABASE if setting.KEEP_DECRYPTED_FILE else self.aes.ENC_FILE
            LOG.debug('Heroku mode.start set_discord_attachment_file.')

            # チャンネルをチェック(チャンネルが存在しない場合は勝手に作成する)
            get_control_channel = discord.utils.get(guild.text_channels, name=self.REMIND_CONTROL_CHANNEL)
            if get_control_channel is None:
                permissions = []
                target = []
                permissions.append(discord.PermissionOverwrite(read_messages=False,read_message_history=False))
                target.append(guild.default_role)
                permissions.append(discord.PermissionOverwrite(read_messages=True,read_message_history=True))
                target.append(guild.owner)
                permissions.append(discord.PermissionOverwrite(read_messages=True,read_message_history=True))
                target.append(self.bot.user)
                overwrites = dict(zip(target, permissions))

                try:
                    get_control_channel = await guild.create_text_channel(name=self.REMIND_CONTROL_CHANNEL, overwrites=overwrites)
                    # get_control_channel = await guild.create_text_channel(name=self.REMIND_CONTROL_CHANNEL)
                    LOG.info(f'＊＊＊{self.REMIND_CONTROL_CHANNEL}を作成しました！＊＊＊')
                except discord.errors.Forbidden:
                    LOG.error(f'＊＊＊{self.REMIND_CONTROL_CHANNEL}の作成に失敗しました！＊＊＊')

                if get_control_channel is None:
                    LOG.error(f'なんらかのエラーが発生しました')

            # チャンネルの最後のメッセージを確認し、所定のメッセージなら削除する
            last_message = await get_control_channel.history(limit=1).flatten()
            if len(last_message) != 0:
                if last_message[0].content == file_name:
                    await get_control_channel.purge(limit=1)

            # チャンネルにファイルを添付する
            file_path = join(dirname(__file__), 'files' + os.sep + file_name)
            await get_control_channel.send(file_name, file=discord.File(file_path))
            LOG.info(f'＊＊＊{get_control_channel.name}へファイルを添付しました！＊＊＊')

            LOG.debug('set_discord_attachment_file is over!')

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

    async def make(self, guild_id, author_id, remind_datetime: datetime,
            remind_message: str, channel: int, status: str, repeat_flg: str,
            repeat_interval: str, repeat_count: int=1, repeat_max_count:int=None):
        '''remindを作成'''
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        id = None
        with conn:
            cur = conn.cursor()

            now = datetime.datetime.now(self.JST)

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
        # Herokuの時のみ、チャンネルにファイルを添付する
        # self.bot
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        await self.set_discord_attachment_file(guild)
        return id

    async def update_status(self, remind_id: int, guild_id: int, status: str=STATUS_FINISHED):
        '''remindのステータスを変更'''
        self.decode()

        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            now = datetime.datetime.now(self.JST)

            remind_param = (status, now, remind_id)
            update_sql = 'update reminder_table set status=?, updated_at = ? where id = ?'
            conn.execute(update_sql, remind_param)
            LOG.info(f'id:{remind_id}を{status}にしました')
        self.read()
        self.encode()
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        await self.set_discord_attachment_file(guild)

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