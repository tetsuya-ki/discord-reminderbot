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
    STATUS_PROGRESS = 'Progress'
    STATUS_ERROR = 'Error'
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
        self.saved_dm_guild = None

    async def prepare(self, guild):
        '''
        sqlite3のdbを準備する
        '''
        self.saved_dm_guild = guild
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
            file_name = self.aes.ENC_FILE if setting.KEEP_DECRYPTED_FILE else self.DATABASE
            LOG.debug('Heroku mode.start get_discord_attachment_file.')
            # ファイルをチェックし、存在しなければ最初と見做す
            file_path_first_time = join(dirname(__file__), 'files' + os.sep + 'first_time')
            if (setting.IS_HEROKU and not os.path.exists(file_path_first_time)) or setting.IS_REPLIT:
                if setting.IS_HEROKU:
                    with open(file_path_first_time, 'w') as f:
                        now = datetime.datetime.now(self.JST)
                        f.write(now.strftime('%Y/%m/%d(%a) %H:%M:%S'))
                        LOG.debug(f'{file_path_first_time}が存在しないので、作成を試みます')
                attachment_file_date = None

                # BotがログインしているGuildごとに繰り返す
                for guild in self.bot.guilds:
                    # チャンネルのチェック
                    LOG.debug(f'{guild}: チャンネル読み込み')
                    get_control_channel = discord.utils.get(guild.text_channels, name=self.REMIND_CONTROL_CHANNEL)
                    if get_control_channel is not None:
                        try:
                            messages = await get_control_channel.history(limit=20).flatten()
                        except discord.errors.Forbidden:
                            msg = f'＊＊＊{guild}のチャンネル({self.REMIND_CONTROL_CHANNEL})読み込みに失敗しました！＊＊＊'
                            LOG.error(msg)
                            continue

                        for message in messages:
                            # 添付ファイルの読み込みを自分の投稿のみに制限する(環境変数で指定された場合のみ)
                            if setting.RESTRICT_ATTACHMENT_FILE and  message.author != guild.me:
                                continue
                            LOG.debug(f'con: {message.content}, attchSize:{len(message.attachments)}')
                            # message_created_at_jst = datetime.datetime(message.created_at, tzinfo=self.JST)
                            message_created_at = message.created_at.replace(tzinfo=timezone.utc)
                            message_created_at_jst = message_created_at.astimezone(self.JST)

                            if attachment_file_date is not None:
                                LOG.debug(f'date: {attachment_file_date} <<<<<<< {message_created_at_jst}, {attachment_file_date < message_created_at_jst}')
                            # file_nameが本文である場合、ファイルを取得する
                            if message.content == file_name:
                                if len(message.attachments) > 0:
                                    # 日付が新しい場合、ファイルを取得
                                    if attachment_file_date is None or attachment_file_date < message_created_at_jst:
                                        attachment_file_date = message_created_at_jst
                                        file_path = join(dirname(__file__), 'files' + os.sep + file_name)
                                        await message.attachments[0].save(file_path)
                                        LOG.info(f'channel_file_save:{guild.name} / datetime:{attachment_file_date.strftime("%Y/%m/%d(%a) %H:%M:%S")}')
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
            file_name = self.aes.ENC_FILE if setting.KEEP_DECRYPTED_FILE else self.DATABASE
            LOG.debug('Heroku mode.start set_discord_attachment_file.')

            # チャンネルをチェック(チャンネルが存在しない場合は勝手に作成する)
            if guild == None: # ありえないと思うけれど、guildがないならDMと同じ対応する
                guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
            get_control_channel = discord.utils.get(guild.text_channels, name=self.REMIND_CONTROL_CHANNEL)
            if get_control_channel is None:
                permissions = []
                target = []
                permissions.append(discord.PermissionOverwrite(read_messages=False,read_message_history=False))
                target.append(guild.default_role)
                permissions.append(discord.PermissionOverwrite(read_messages=True,read_message_history=True))
                target.append(self.bot.user)
                overwrites = dict(zip(target, permissions))

                try:
                    get_control_channel = await guild.create_text_channel(name=self.REMIND_CONTROL_CHANNEL, overwrites=overwrites)
                    LOG.info(f'＊＊＊{self.REMIND_CONTROL_CHANNEL}を作成しました！＊＊＊')
                except discord.errors.Forbidden:
                    msg = f'＊＊＊{self.REMIND_CONTROL_CHANNEL}の作成に失敗しました！＊＊＊'
                    LOG.error(msg)
                    raise

                if get_control_channel is None:
                    LOG.error(f'なんらかのエラーが発生しました')
                    return

            # チャンネルの最後のメッセージを確認し、所定のメッセージなら削除する
            try:
                last_message = await get_control_channel.history(limit=1).flatten()
            except discord.errors.Forbidden:
                # エラーが発生したら、適当に対応
                msg = f'＊＊＊{guild}のチャンネル({self.REMIND_CONTROL_CHANNEL})読み込みに失敗しました！＊＊＊'
                LOG.error(msg)
                guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
                get_control_channel = discord.utils.get(guild.text_channels, name=self.REMIND_CONTROL_CHANNEL)
                last_message = await get_control_channel.history(limit=1).flatten()
            if len(last_message) != 0:
                if last_message[0].content == file_name:
                    await get_control_channel.purge(limit=1)

            # チャンネルにファイルを添付する
            file_path = join(dirname(__file__), 'files' + os.sep + file_name)
            await get_control_channel.send(file_name, file=discord.File(file_path))
            LOG.info(f'＊＊＊{guild.name}の{get_control_channel.name}へファイルを添付しました！＊＊＊')

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
            select_sql = f'''select * from reminder_table where status = '{self.STATUS_PROGRESS}' order by remind_datetime'''
            LOG.debug(select_sql)
            cur.execute(select_sql)
            self.remind_rows = cur.fetchmany(100)
            LOG.info('＊＊＊＊＊＊読み込みが完了しました＊＊＊＊＊＊')
            LOG.debug(self.remind_rows)

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
            LOG.debug(insert_sql)

            # get id
            get_id_sql = 'select id from reminder_table where rowid = last_insert_rowid()'
            cur.execute(get_id_sql)
            id = cur.fetchone()[0]
            LOG.debug(f'id:{id}を追加しました')
            conn.commit()
            self.read()
        self.encode()

        # 添付対象のギルドの決定
        if guild_id is None:
            guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
        else:
            guild = discord.utils.get(self.bot.guilds, id=guild_id)

        # Herokuの時のみ、チャンネルにファイルを添付する
        try:
            await self.set_discord_attachment_file(guild)
        except discord.errors.Forbidden:
            msg = f'＊＊＊{guild.name}へのチャンネル作成に失敗したため、dm_guildへ添付します＊＊＊'
            LOG.info(msg)
            guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
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
            LOG.debug(update_sql)
            conn.execute(update_sql, remind_param)
            LOG.info(f'id:{remind_id}を{status}にしました')
        self.read()
        self.encode()

        # 添付対象のギルドの決定
        if guild_id is None:
            guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
        else:
            guild = discord.utils.get(self.bot.guilds, id=guild_id)

        # Herokuの時のみ、チャンネルにファイルを添付する
        try:
            await self.set_discord_attachment_file(guild)
        except discord.errors.Forbidden:
            msg = f'＊＊＊{guild.name}へのチャンネル作成に失敗したため、dm_guildへ添付します＊＊＊'
            LOG.info(msg)
            guild = discord.utils.get(self.bot.guilds, id=self.saved_dm_guild)
            await self.set_discord_attachment_file(guild)

    def list(self, ctx: commands.Context, status: str = 'Progress'):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            if ctx.guild is None:
                select_sql = f'''select * from reminder_table where status = '{status}' and member = '{ctx.author.id}' '''
            else:
                select_sql = f'''select * from reminder_table where status = '{status}' and guild = '{ctx.guild.id}' and member = '{ctx.author.id}' '''

            if status == self.STATUS_PROGRESS:
                select_sql += '''order by remind_datetime'''
            else:
                select_sql += '''order by updated_at desc'''

            LOG.debug(select_sql)
            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = self.create_message(rows)
            escaped_mention_text = '(データがありません)' if len(message) == 0 else discord.utils.escape_mentions(message)
            LOG.debug(escaped_mention_text)
        self.encode()
        chopped_escaped_mention_text = escaped_mention_text[:1900] + ('...(省略)...' if escaped_mention_text[1900:] else '')
        return chopped_escaped_mention_text

    def list_all_guild(self, ctx: commands.Context, status: str = None):
        return self._list_all_func(ctx, True, status)

    def list_all(self, ctx: commands.Context, status: str = None):
        return self._list_all_func(ctx, False, status)

    def _list_all_func(self, ctx: commands.Context, is_guild: bool, status: str = None):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()

            select_sql = 'select * from reminder_table '
            if is_guild:
                select_sql += f'''where guild = '{ctx.guild.id}' '''
            if status:
                if is_guild:
                    select_sql += f'''and status = '{status}' '''
                else:
                    select_sql += f'''where status = '{status}' '''

            if status is not None and status == self.STATUS_PROGRESS:
                select_sql += '''order by remind_datetime'''
            else:
                select_sql += '''order by updated_at desc'''

            LOG.debug(select_sql)

            cur.execute(select_sql)
            rows = cur.fetchmany(100)
            message = self.create_message(rows)
            escaped_mention_text = '(データがありません)' if len(message) == 0 else discord.utils.escape_mentions(message)
            LOG.debug(escaped_mention_text)
        self.encode()
        chopped_escaped_mention_text = escaped_mention_text[:1900] + ('...(省略)...' if escaped_mention_text[1900:] else '')
        return chopped_escaped_mention_text

    def create_message(self, rows):
        message = ''
        for row in rows:
            channel = f'<#{row[4]}>' if row[4] is not None else 'DM'
            repeat_max = str(row[8]) if row[8] is not None else '設定なし(解除するまで)'
            repeat_interval_message = f'間隔: {row[10]}, ' if row[10] is not None else ''
            repeat_message = f'繰り返す({repeat_interval_message}最大回数: {repeat_max})' if row[9] == '1' else '繰り返さない'
            message += f'No. {row[0]} ' + discord.utils.escape_markdown('Remind_datetime: ') + f'{row[1]}\n'
            message += f'Message: {row[5]}\n'
            message += f'Status: {row[6]} {repeat_message} 通知先: {channel}\n--\n'
        return message

    def get(self, ctx: commands.Context, id: int):
        self.decode()
        conn = sqlite3.connect(self.FILE_PATH)
        with conn:
            cur = conn.cursor()
            select_sql = f'''select * from reminder_table where status = '{self.STATUS_PROGRESS}' and member = '{ctx.author.id}' and id = '{id}' '''
            LOG.debug(select_sql)
            cur.execute(select_sql)
            row = cur.fetchone()
            escaped_mention_text = '(データがありません)' if row is None else discord.utils.escape_mentions(str(row))
            LOG.debug(escaped_mention_text)
        self.encode()
        return row