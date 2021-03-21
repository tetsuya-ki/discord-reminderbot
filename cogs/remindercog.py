from datetime import timedelta, timezone
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from discord.ext import tasks, commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils import manage_commands  # Allows us to manage the command settings.
from logging import getLogger
from .modules.remind import Remind
from .modules import setting

import datetime, dateutil.parser, discord, re

LOG = getLogger(__name__)


# コグとして用いるクラスを定義。
class ReminderCog(commands.Cog):
    guilds = [] if setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST is None else list(
        map(int, setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST.split(';')))
    JST = timezone(timedelta(hours=9), 'JST')
    NUM_1keta = '^[0-9]$'

    # ReminderCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.remind = Remind()

    # 読み込まれた時の処理
    @commands.Cog.listener()
    async def on_ready(self):
        self.remind.prepare()  # dbを作成
        LOG.info('SQlite準備完了')
        LOG.info(self.guilds)
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=20.0)
    async def printer(self):
        now = datetime.datetime.now(self.JST)

        # LOG.info(discord.utils.get(self.bot.get_all_channels()))
        for remind in self.remind.remind_rows:
            remind_datetime = dateutil.parser.parse(f'{remind[1]} +0900 (JST)',
                                                    yearfirst=True)
            if remind_datetime <= now:
                # リマインドを発動
                channel = discord.utils.get(self.bot.get_all_channels(),
                                            guild__id=remind[2],
                                            id=remind[4])
                await channel.send(remind[5])
                # リマインドを削除
                self.remind.delete(remind[0])

                # リマインドを繰り返す場合の処理

            else:
                break

    @cog_ext.cog_slash(
        name="remind-make",
        guild_ids=guilds,
        description='remindを作成する',
        options=[
            manage_commands.create_option(name='date',
                                        description='日付(yyyy-mm-dd形式)、もしくは、何日後かの数字1桁',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='time',
                                        description='時間(hh24:mi形式)',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='message',
                                        description='メッセージ',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='channel',
                                        description='チャンネル',
                                        option_type=3,
                                        required=False)
        ])
    async def _remind_make(self,
                        ctx,
                        date: str = None,
                        time: str = None,
                        message: str = None,
                        channel: str = None):
        LOG.info('remindをmakeするぜ！')

        # チェック処理(存在しない場合、引数が不正な場合など)

        # チャンネルの設定(指定なしなら投稿されたチャンネル、指定があればそちらのチャンネルとする)
        channel_id = ctx.channel.id
        if channel is not None:
            temp_channel = discord.utils.get(ctx.guild.text_channels, name=channel)
            if temp_channel is None:
                temp_channel_id = re.sub(r'[<#>]', '', channel)
                if temp_channel_id.isdecimal() and '#' in channel:
                    channel_id = int(temp_channel_id)
            else:
                channel_id = temp_channel.id

        # エイリアス(特定の文字列の場合、日付に変換)
        today = datetime.date.today()
        if date.lower().startswith('t'):
            date = today
        elif re.match(self.NUM_1keta, date):
            date = today + relativedelta(days=+int(date))

        # リマインド日時への変換
        remind_datetime = None
        try:
            remind_datetime = dateutil.parser.parse(
                f'{date} {time} +0900 (JST)', yearfirst=True)
        except ValueError as e:
            LOG.info(f'このメッセージで不正な日時が提出されました：{ctx.message.clean_content}')
            LOG.info(e)

        status = 'Progress'
        repeat_flg = '0'
        repeat_interval = None

        # 実際の処理(remind.pyでやる)
        self.remind.make(ctx, remind_datetime, message, channel_id, status, repeat_flg,
                        repeat_interval)
        await ctx.respond()

    @commands.command()
    async def remind_delete(self,
                            ctx: commands.Context,
                            date: str = None,
                            time: str = None,
                            message: str = None):
        LOG.info('remindをdeleteするぜ！')

    @cog_ext.cog_slash(name="remind-list",
                        guild_ids=guilds,
                        description='remindを確認する')
    async def remind_list(self, ctx):
        LOG.info('remindをlistするぜ！')
        rows = self.remind.list(ctx)
        await ctx.respond()
        await ctx.send(content=rows)

    @cog_ext.cog_slash(name="remind-list-all",
                        guild_ids=guilds,
                        description='remindをぜんぶ確認する')
    async def _remind_list_all(self, ctx):
        LOG.info('remindをlistするぜ！')
        rows = self.remind.list_all(ctx)
        await ctx.respond()
        await ctx.send(content=rows)


# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    LOG.info('DiscordReminderBotを読み込む！')
    bot.add_cog(ReminderCog(bot))  # ReminderCogにBotを渡してインスタンス化し、Botにコグとして登録する。
