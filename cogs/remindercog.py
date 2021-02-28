from dateutil import rrule
from discord.ext import commands # Bot Commands Frameworkのインポート
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands # Allows us to manage the command settings.
from logging import getLogger
from .modules.remind import Remind
from .modules import setting

import datetime, dateutil.parser, discord

LOG = getLogger(__name__)

# コグとして用いるクラスを定義。
class ReminderCog(commands.Cog):
    guilds = [] if setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST is None else list(map(int, setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST.split(';')))

    # ReminderCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.remind = Remind()

    # 読み込まれた時の処理
    @commands.Cog.listener()
    async def on_ready(self):
        self.remind.prepare() # dbを作成
        LOG.info('SQlite準備完了')
        LOG.info(self.guilds)

    @commands.command()
    async def remind_make(self, ctx: commands.Context, date:str=None, time:str=None, message:str=None):
        LOG.info('remindをmakeするぜ！')

        # チェック処理(存在しない場合、引数が不正な場合など)

        # リマインド日時への変換
        remind_datetime = None
        try:
            remind_datetime = dateutil.parser.parse(f'{date} {time}', yearfirst=True)
        except ValueError as e:
            LOG.info(f'このメッセージで不正な日時が提出されました：{ctx.message.clean_content}')
            LOG.info(e)

        test = """
                    memo
                    id integer primary key autoincrement, # 勝手に裁判
                    remind_datetime datetime,
                    guild integer, #ctx
                    member integer, #ctx
                    channel integer, #ctx
                    remind_message text,
                    status text, #作るやつ
                    mention text, #ctx
                    repeat_flg str, # 作るやつ
                    repeat_interval str, # 作るやつ
                    created_at datetime, #不要
                    updated_at datetime, #不要
                """

        status = 'Progress'
        repeat_flg = '0'
        repeat_interval = None

        # 実際の処理(remind.pyでやる)
        self.remind.make(ctx, remind_datetime, message, status, repeat_flg, repeat_interval)

    @commands.command()
    async def remind_delete(self, ctx: commands.Context, date:str=None, time:str=None, message:str=None):
        LOG.info('remindをdeleteするぜ！')

    @commands.command()
    async def remind_list(self, ctx: commands.Context, date:str=None, time:str=None, message:str=None):
        LOG.info('remindをlistするぜ！')
        self.remind.list(ctx)

    @cog_ext.cog_slash(name="rem_test", description='test', guild_ids=guilds)
    async def _rem_test(self, ctx: SlashContext):
        embed = discord.Embed(title="embed test")
        await ctx.send(content="test", embeds=[embed])

# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    LOG.info('DiscordReminderBotを読み込む！')
    bot.add_cog(ReminderCog(bot)) # ReminderCogにBotを渡してインスタンス化し、Botにコグとして登録する。