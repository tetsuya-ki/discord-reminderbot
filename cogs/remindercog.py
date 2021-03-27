from datetime import timedelta, timezone
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from discord.ext import tasks, commands
from discord.ext.commands import context
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
                if remind[9] == '1':
                    # remind[10](repeat_interval)に従って、次のリマインドを作成
                    # remind_datetimeは次の日付に変換（ちょっと難しいところ）
                    count = 0
                    next_remind_datetime = self.calc_next_reminder_date(remind_datetime, remind[10])
                    while(next_remind_datetime <= now):
                        next_remind_datetime = self.calc_next_reminder_date(next_remind_datetime, remind[10])
                        count += 1
                        # countが100を超えた場合は異常なので、処理を中断
                        if count > 100:
                            LOG.warning(f'No.{remind[0]}の{remind[10]}を100回実行しても、現実時間に追いつかないため、None扱いとします。')
                            next_remind_datetime = None
                            break

                    # 計算できなかったら、飛ばす
                    if next_remind_datetime is None:
                        LOG.warning(f'No.{remind[0]}の{remind[10]}が計算できなかったため、飛ばしました。')
                        continue

                    status = 'Progress'

                    # 繰り返し回数のチェック
                    repeat_count = remind[7] + 1
                    if remind[8] is None or repeat_count < remind[8]:
                        repeat_flg = '1'
                    elif repeat_count > remind[8]:
                        LOG.warning(f'No.{remind[0]}のrepeat_max_count({remind[8]})を超えているため、追加をしません。')
                        continue
                    else:
                        repeat_flg = '0'

                    # 繰り返し時のメッセージを変更
                    last_remind_message = re.sub('\(\d+\)','', remind[5])
                    remind_message = f'{last_remind_message}({repeat_count})' if repeat_count > 1 else remind[5]

                    self.remind.make(remind[2], remind[3], next_remind_datetime, remind_message, remind[4], status, repeat_flg,
                        remind[10], repeat_count, remind[8])

            else:
                break

    @cog_ext.cog_slash(
        name="remind-make",
        guild_ids=guilds,
        description='remindを作成する',
        options=[
            manage_commands.create_option(name='date',
                                        description='日付(mm/dd形式)、もしくは、何日後かの数字1桁(0-9)。年がある場合はyyyy/mm/dd形式(yyyy-mm-ddも形式も可)',
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
            manage_commands.create_option(name='repeat_interval',
                                        description='繰り返し間隔(数字に右の英字を付与：分(mi)/時間(h)/日(d)/週(w)/月(m)/年(y)か、特殊(平日/休日/月初/月末/曜日の文字列(「月水」のような)))',
                                        option_type=3,
                                        required=False),
            manage_commands.create_option(name='repeat_max_count',
                                        description='繰り返し最大数(設定がない場合、ずっと繰り返されます)',
                                        option_type=3,
                                        required=False),
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
                        repeat_interval: str = None,
                        repeat_max_count: str = None,
                        channel: str = None):
        LOG.info('remindをmakeするぜ！')
        await ctx.respond()

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

        today = datetime.date.today()
        # 4桁の数字がない場合、先頭に付けてみる
        nothing_year = re.search('\d{4}', date) is None
        if '-' in date and  nothing_year:
            date = f'{today.year}-{date}'
        elif '/' in date and  nothing_year:
            date = f'{today.year}/{date}'

        # エイリアス(特定の文字列の場合、日付に変換)
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
            error_message = '不正な日時のため、リマインドを登録できませんでした'
            LOG.info(error_message)
            LOG.info(e)
            await ctx.send(error_message, hidden = True)
            return

        status = 'Progress'

        # 繰り返し間隔の設定
        repeat_flg = '0'
        if repeat_interval:
            repeat_flg  = '1'

        repeat_count = 1

        # 実際の処理(remind.pyでやる)
        self.remind.make(ctx.guild.id, ctx.author.id, remind_datetime, message, channel_id, status, repeat_flg,
                        repeat_interval, repeat_count, repeat_max_count)
        await ctx.send('リマインドを登録しました', hidden = True)

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

    def calc_next_reminder_date(self, remind_datetime, repeat_interval):
        re_minutes = r'([0-9]+)mi$'
        next_remind_datetime = self.re_reminder_date(re_minutes, repeat_interval, remind_datetime, 'minutes')
        if next_remind_datetime:
            return next_remind_datetime

        re_hours = r'([0-9]+)h$'
        next_remind_datetime = self.re_reminder_date(re_hours, repeat_interval, remind_datetime, 'hours')
        if next_remind_datetime:
            return next_remind_datetime

        re_days = r'([0-9]+)d$'
        next_remind_datetime = self.re_reminder_date(re_days, repeat_interval, remind_datetime, 'days')
        if next_remind_datetime:
            return next_remind_datetime

        re_weeks = r'([0-9]+)w$'
        next_remind_datetime = self.re_reminder_date(re_weeks, repeat_interval, remind_datetime, 'weeks')
        if next_remind_datetime:
            return next_remind_datetime

        re_months = r'([0-9]+)m$'
        next_remind_datetime = self.re_reminder_date(re_months, repeat_interval, remind_datetime, 'months')
        if next_remind_datetime:
            return next_remind_datetime

        re_years = r'([0-9])y$'
        next_remind_datetime = self.re_reminder_date(re_years, repeat_interval, remind_datetime, 'years')
        if next_remind_datetime:
            return next_remind_datetime

        # それ以外のパターンはNoneとする
        return None

    def re_reminder_date(self, re_str, repeat_interval, datetime, time_param_name):
        m = re.match(re_str, repeat_interval)
        if m:
            param = {time_param_name:+int(m.group(1))}
            return datetime + relativedelta(**param)

# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    LOG.info('DiscordReminderBotを読み込む！')
    bot.add_cog(ReminderCog(bot))  # ReminderCogにBotを渡してインスタンス化し、Botにコグとして登録する。
