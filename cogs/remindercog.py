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

LOG = getLogger('reminderbot')


# コグとして用いるクラスを定義。
class ReminderCog(commands.Cog):
    guilds = [] if setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST is None else list(
        map(int, setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST.split(';')))
    JST = timezone(timedelta(hours=9), 'JST')
    NUM_1keta = '^[0-9]$'

    # ReminderCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.remind = Remind(bot)

    # 読み込まれた時の処理
    @commands.Cog.listener()
    async def on_ready(self):
        dm_guild = self.bot.guilds[0].id if len(self.bot.guilds) > 0 else None

        # PRIORITY_GUILDがある場合の上書き
        if setting.PRIORITY_GUILD and setting.PRIORITY_GUILD.isdecimal():
            pr_guild = [i for i in self.bot.guilds if i.id == int(setting.PRIORITY_GUILD)]
            if len(pr_guild) > 0:
                dm_guild = pr_guild[0].id
        await self.remind.prepare(dm_guild)  # dbを作成
        LOG.info('SQlite準備完了')
        LOG.debug(self.bot.guilds)
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=20.0)
    async def printer(self):
        now = datetime.datetime.now(self.JST)
        LOG.debug(f'printer is kicked.({now})')

        # LOG.info(discord.utils.get(self.bot.get_all_channels()))
        for remind in self.remind.remind_rows:
            remind_datetime = dateutil.parser.parse(f'{remind[1]} +0900 (JST)',
                                                    yearfirst=True)
            if remind_datetime <= now:
                # リマインドを発動
                # DMの対応
                if remind[2] is None:
                    remind_user = self.bot.get_user(remind[3])
                    text = remind_user or ''
                    LOG.debug('user id :' + str(remind[3]) + ', user:'+ text)
                    if remind_user is None:
                        remind_user = await self.bot.fetch_user(remind[3])
                        text = remind_user or ''
                    channel = await remind_user.create_dm()
                    await channel.send(remind[5])
                else:
                    channel = discord.utils.get(self.bot.get_all_channels(),
                                                guild__id=remind[2],
                                                id=remind[4])
                    if channel is not None:
                        try:
                            await channel.send(remind[5])
                        except discord.errors.Forbidden:
                            msg = f'＊＊＊{remind[2]}のチャンネルへの投稿に失敗しました！＊＊＊'
                            LOG.error(msg)
                            # リマインドを削除
                            await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_ERROR)
                            
                            try:
                                get_control_channel = discord.utils.get(self.bot.get_all_channels(),guild__id=remind[2],name=self.remind.REMIND_CONTROL_CHANNEL)
                                await get_control_channel.send(f'@here No.{remind[0]}は権限不足などの原因でリマインドできませんでした。リマインドしたい場合は、投稿先チャンネルの設定見直しをお願いします\n> {remind[5]}')
                            except:
                                msg = f'＊＊＊さらに、{remind[2]}のチャンネル({self.remind.REMIND_CONTROL_CHANNEL})への投稿に失敗しました！＊＊＊'
                                LOG.error(msg)
                                continue

                            continue

                # リマインドを削除
                await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_FINISHED)

                # リマインドを繰り返す場合の処理
                if remind[9] == '1':
                    try:
                        if remind[2]:
                            await self.bot.fetch_guild(remind[2])
                    except:
                        LOG.warning(f'No.{remind[0]}(guild:{remind[2]}が取得できなかったため、繰り返し対象外とします。')
                        continue

                    # remind[10](repeat_interval)に従って、次のリマインドを作成
                    # remind_datetimeは次の日付に変換（ちょっと難しいところ）
                    next_remind_datetime = self.check_next_reminder_date(remind_datetime, remind[10], now,remind[0])

                    # 計算できなかったら、飛ばす
                    if next_remind_datetime is None:
                        LOG.warning(f'No.{remind[0]}の{remind[10]}が計算できなかったため、飛ばしました。')
                        await channel.send(f'次回のリマインドに失敗しました(No.{remind[0]}の{remind[10]}が計算できなかったため)')
                        continue

                    status = self.remind.STATUS_PROGRESS

                    # 繰り返し回数のチェック
                    repeat_count = remind[7] + 1
                    if remind[8] is None or (remind[8].isdecimal() and repeat_count < remind[8]):
                        repeat_flg = '1'
                    elif remind[8].isdecimal() and repeat_count > remind[8]:
                        LOG.warning(f'No.{remind[0]}のrepeat_max_count({remind[8]})を超えているため、追加をしません。')
                        continue
                    else:
                        repeat_flg = '0'
                        if not remind[8].isdecimal():
                            LOG.warning(f'繰り返し上限に数字以外が登録されました。remind[8]は{str(remind[8])}')

                    # 繰り返し時のメッセージを変更
                    last_remind_message = re.sub('\(\d+\)','', remind[5])
                    remind_message = f'{last_remind_message}({repeat_count})' if repeat_count > 1 else remind[5]

                    id = await self.remind.make(remind[2], remind[3], next_remind_datetime, remind_message, remind[4], status, repeat_flg,
                        remind[10], repeat_count, remind[8])
                    if channel:
                        await channel.send(f'次回のリマインドを登録しました(No.{id})')
                    else:
                        LOG.error(f'channelがないので、メッセージ送れませんでした！(No.{id})')

            else:
                break

    @cog_ext.cog_slash(
        name='remind-make',
        # guild_ids=guilds,
        description='remindを作成する',
        options=[
            manage_commands.create_option(name='date',
                                        description='日付(mm/dd形式)、もしくは、何日後かの数字1桁(0-9)。年がある場合はyyyy/mm/dd形式(yyyy-mm-dd形式も可)',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='time',
                                        description='時間(hh24:mi形式)、もしくは、xxh(xxは数字(0-9)。xx時間後)、xxmi(xx分後)',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='message',
                                        description='メッセージ(メンションしたい場合、通常のメッセージのように @xxxx を書いてください)',
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
                                        description='リマインドを投稿するチャンネル(#general等。「DM」でBotとのDMへ登録されます。未指定の場合はリマインド登録したチャンネルに投稿)',
                                        option_type=3,
                                        required=False),
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def _remind_make(self,
                        ctx,
                        date: str = None,
                        time: str = None,
                        message: str = None,
                        repeat_interval: str = None,
                        repeat_max_count: str = None,
                        channel: str = None,
                        reply_is_hidden: str = 'True'):
        LOG.info('remindをmakeするぜ！')
        self.check_printer_is_running()

        # チェック処理(存在しない場合、引数が不正な場合など)
        if repeat_max_count is not None and not repeat_max_count.isdecimal():
            msg = '繰り返し最大数が数字ではありません。繰り返したい回数か、未設定としてください（未設定の場合はキャンセルするまでずっとリマインドします）。'
            await ctx.send(msg, hidden = True)
            LOG.info(msg)
            return

        # ギルドの設定
        if ctx.guild is not None:
            guild_id = ctx.guild.id
        else:
            if channel is not None and channel.upper() != 'DM':
                msg = 'DMでチャンネル指定はできません。チャンネルは未指定でリマインドを登録ください。'
                await ctx.send(msg, hidden = True)
                LOG.info(msg)
                return

            channel,guild_id = None,None

        # チャンネルの設定(指定なしなら投稿されたチャンネル、指定があればそちらのチャンネルとする)
        channel_id = None
        if channel is not None:
            temp_channel = discord.utils.get(ctx.guild.text_channels, name=channel)
            if channel.upper() == 'DM': # チャンネルが'DM'なら、ギルドとチャンネルをNoneとする
                guild_id = None
                if self.remind.saved_dm_guild is None:
                    msg = 'ギルドが何も登録されていない段階で、DMを登録することはできません。ギルドを登録してから再度リマインドの登録をしてください。'
                    await ctx.send(msg, hidden = True)
                    LOG.info(msg)
                    return

            elif temp_channel is None:
                temp_channel_id = re.sub(r'[<#>]', '', channel)
                if temp_channel_id.isdecimal() and '#' in channel:
                    channel_id = int(temp_channel_id)
                else:
                    msg = 'チャンネル名が不正です。もう一度、適切な名前で登録してください(#チャンネル名でもOK)。'
                    await ctx.send(msg, hidden = True)
                    LOG.info(msg)
                    return
            else:
                channel_id = temp_channel.id
        else:
            channel_id = ctx.channel.id

            # チャンネルが設定されておらず、ギルドが無いなら、ギルドとチャンネルをNoneとする
            if guild_id is None:
                channel_id = None

        today = datetime.datetime.now(self.JST).date()
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

        # 時間の変換
        now_time = datetime.datetime.now(self.JST)
        m_hours = re.match('^([0-9]{1,3})h$', time)
        m_minutes = re.match('^([0-9]{1,4})mi$', time)
        m_normal = re.match('^([0-9]{1,2}:[0-9]{1,2})$', time)
        if m_hours:
            result_time = now_time + datetime.timedelta(hours=int(m_hours.group(1)))
            time = result_time.strftime('%H:%M')
        elif m_minutes:
            result_time = now_time + datetime.timedelta(minutes=int(m_minutes.group(1)))
            time = result_time.strftime('%H:%M')
        elif m_normal:
            pass
        else:
            error_message = '不正な時間のため、リマインドを登録できませんでした'
            LOG.info(error_message)
            await ctx.send(error_message, hidden = True)
            return

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

        status = self.remind.STATUS_PROGRESS

        # 繰り返し間隔の設定
        repeat_flg = '0'
        if repeat_interval:
            # 間隔設定のチェック
            now = datetime.datetime.now(self.JST)
            next_remind_datetime = self.check_next_reminder_date(remind_datetime, repeat_interval, now)
            if next_remind_datetime is None:
                error_message = '繰り返し間隔が不正のため、リマインドを登録できませんでした'
                LOG.info(error_message)
                await ctx.send(error_message, hidden = True)
                return
            repeat_flg  = '1'

        repeat_count = 1

        # 実際の処理(remind.pyでやる)
        id = await self.remind.make(guild_id, ctx.author.id, remind_datetime, message, channel_id, status, repeat_flg,
                        repeat_interval, repeat_count, repeat_max_count)

        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(f'リマインドを登録しました(No.{id})', hidden = hidden)

    @cog_ext.cog_slash(
        name='remind-cancel',
        # guild_ids=guilds,
        description='remindをキャンセルする',
        options=[
            manage_commands.create_option(name='cancel_no',
                                        description='キャンセルするリマインドの番号(No)',
                                        option_type=3,
                                        required=True),
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def remind_cancel(self,
                            ctx,
                            cancel_no: str,
                            reply_is_hidden: str = 'True'):
        LOG.info('remindをcancelするぜ！')
        self.check_printer_is_running()

        # チェック
        if not cancel_no.isdecimal():
            invalid_number_msg = '有効な数字ではありません'
            await ctx.send(invalid_number_msg, hidden = True)
            LOG.info(invalid_number_msg)
            return

        # コマンド実行者が指定したNoのリマインドを持っているかチェック
        id = int(cancel_no)
        row = self.remind.get(ctx, id)
        if row is None:
            cancel_id_is_none_msg = 'リマインドをキャンセルできませんでした(Noが違う可能性があります)'
            await ctx.send(cancel_id_is_none_msg, hidden = True)
            LOG.info(cancel_id_is_none_msg)
            return

        # 添付する際にギルドIDが必要なので準備する(DMの場合はNone(デフォルトのギルドへ登録する))
        guild_id = ctx.guild.id if ctx.guild is not None else None

        # リマインドをキャンセル
        await self.remind.update_status(id, guild_id, self.remind.STATUS_CANCELED)
        cancel_msg = f'リマインドをキャンセルしました(No.{cancel_no})'

        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(cancel_msg, hidden = hidden)
        LOG.info(cancel_msg)

    @cog_ext.cog_slash(
        name='remind-list',
        # guild_ids=guilds,
        description='remindを確認する',
        options=[
            manage_commands.create_option(name='status',
                                        description='リマインドリストで表示させるステータス',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='実行予定のリマインドリスト(デフォルト)',
                                            value='Progress'),
                                            manage_commands.create_choice(
                                            name='キャンセルしたリマインドリスト',
                                            value='Canceled'),
                                            manage_commands.create_choice(
                                            name='終了したリマインドリスト',
                                            value='Finished')
                                        ]),
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def remind_list(self, ctx, status: str = 'Progress', reply_is_hidden: str = 'True'):
        LOG.info('remindをlistするぜ！')
        self.check_printer_is_running()

        rows = self.remind.list(ctx, status)
        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(rows, hidden = hidden)

    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @cog_ext.cog_slash(
        name='remind-list-guild-all',
        # guild_ids=guilds,
        description='<注意>ギルドのremindをぜんぶ確認する(administrator権限保持者のみ実行可能です！)',
        options=[
            manage_commands.create_option(name='status',
                                        description='リマインドリストで表示させるステータス',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='実行予定のリマインドリスト',
                                            value='Progress'),
                                            manage_commands.create_choice(
                                            name='キャンセルしたリマインドリスト',
                                            value='Canceled'),
                                            manage_commands.create_choice(
                                            name='終了したリマインドリスト',
                                            value='Finished')
                                        ]),
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def _remind_list_guild_all(self, ctx, reply_is_hidden: str = 'True', status: str = None):
        LOG.info('remindをlist(guild)するぜ！')
        self.check_printer_is_running()

        rows = self.remind.list_all_guild(ctx, status)
        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(rows, hidden = hidden)

    @commands.dm_only()
    @commands.is_owner()
    @cog_ext.cog_slash(
        name='remind-list-all',
        description='<注意>remindをぜんぶ確認する(BotのオーナーのみDMで実行可能です！)',
        options=[
            manage_commands.create_option(name='status',
                                        description='リマインドリストで表示させるステータス',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='実行予定のリマインドリスト',
                                            value='Progress'),
                                            manage_commands.create_choice(
                                            name='キャンセルしたリマインドリスト',
                                            value='Canceled'),
                                            manage_commands.create_choice(
                                            name='終了したリマインドリスト',
                                            value='Finished')
                                        ]),
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインド使わせたい場合、全員に見せる方がオススメです))',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def _remind_list_all(self, ctx, reply_is_hidden: str = 'True', status: str = None):
        LOG.info('remindをlist(owner)するぜ！')
        self.check_printer_is_running()

        rows = self.remind.list_all(ctx, status)
        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(rows, hidden = hidden)

    @cog_ext.cog_slash(
        name='remind-task-check',
        description='remindのTaskを確認する(リマインドが発動しない場合に実行してください)',
        options=[
            manage_commands.create_option(name='reply_is_hidden',
                                        description='Botの実行結果を全員に見せるどうか',
                                        option_type=3,
                                        required=False,
                                        choices=[
                                            manage_commands.create_choice(
                                            name='自分のみ',
                                            value='True'),
                                            manage_commands.create_choice(
                                            name='全員に見せる',
                                            value='False')
                                        ])
        ])
    async def _remind_task_check(self, ctx, reply_is_hidden: str = 'True'):
        LOG.info('remindのTaskを確認するぜ！')
        self.check_printer_is_running()

        msg = 'Taskは問題なく起動しています。'
        self.check_printer_is_running()
        hidden = True if reply_is_hidden == 'True' else False
        await ctx.send(msg, hidden = hidden)

    def calc_next_reminder_date(self, remind_datetime, repeat_interval):
        re_minutes = r'([0-9]*)mi$'
        next_remind_datetime = self.re_reminder_date(re_minutes, repeat_interval, remind_datetime, 'minutes')
        if next_remind_datetime:
            return next_remind_datetime

        re_hours = r'([0-9]*)h$'
        next_remind_datetime = self.re_reminder_date(re_hours, repeat_interval, remind_datetime, 'hours')
        if next_remind_datetime:
            return next_remind_datetime

        re_days = r'([0-9]*)d$'
        next_remind_datetime = self.re_reminder_date(re_days, repeat_interval, remind_datetime, 'days')
        if next_remind_datetime:
            return next_remind_datetime

        re_weeks = r'([0-9]*)w$'
        next_remind_datetime = self.re_reminder_date(re_weeks, repeat_interval, remind_datetime, 'weeks')
        if next_remind_datetime:
            return next_remind_datetime

        re_months = r'([0-9]*)m$'
        next_remind_datetime = self.re_reminder_date(re_months, repeat_interval, remind_datetime, 'months')
        if next_remind_datetime:
            return next_remind_datetime

        re_years = r'([1-9]?)y$'
        next_remind_datetime = self.re_reminder_date(re_years, repeat_interval, remind_datetime, 'years')
        if next_remind_datetime:
            return next_remind_datetime

        # 月初, 月末
        if repeat_interval == '月初':
            return remind_datetime + relativedelta(months=+1, day=1)
        if repeat_interval == '月末':
            return remind_datetime + relativedelta(months=+1, day=99)

        # 平日, 休日, 曜日(月火水木金土日)
        start = remind_datetime + relativedelta(days=+1)
        end = remind_datetime + relativedelta(weeks=+1)
        byweekday = self.str2byweekday(repeat_interval)
        if byweekday:
            return self.re_reminder_date_rrule(start, end, byweekday)

        # それ以外のパターンはNoneとする
        return None

    def re_reminder_date(self, re_str, repeat_interval, datetime, time_param_name):
        '''
        正規表現で取り出した値を使い、次の日時を決定
        '''
        m = re.match(re_str, repeat_interval)
        if m:
            next = 1 if m.group(1) == '' else int(m.group(1))
            if next == 0:
                return None
            param = {time_param_name:+next}
            return datetime + relativedelta(**param)

    def str2byweekday(self, string):
        '''
        文字列からrruleのbyweekdayに設定するリストを作成
        '''
        if string == '平日':
            return [rrule.MO, rrule.TU, rrule.WE, rrule.TH, rrule.FR]
        elif string == '休日':
            return [rrule.SA, rrule.SU]
        weekday_set = set()
        for s in string:
            if s == '月':
                weekday_set.add(rrule.MO)
            elif s == '火':
                weekday_set.add(rrule.TU)
            elif s == '水':
                weekday_set.add(rrule.WE)
            elif s == '木':
                weekday_set.add(rrule.TH)
            elif s == '金':
                weekday_set.add(rrule.FR)
            elif s == '土':
                weekday_set.add(rrule.SA)
            elif s == '日':
                weekday_set.add(rrule.SU)

        if len(weekday_set) == 0:
            return None
        else:
            return list(weekday_set)

    def re_reminder_date_rrule(self, start, end, byweekday):
        '''
        rruleを使い、次回の日付を決定
        '''
        rule = rrule.rrule(dtstart=start, freq=rrule.DAILY, byweekday=byweekday)
        next_days = rule.between(start, end, inc=True)
        if len(next_days) > 0:
            return next_days[0]
        else:
            return None

    def check_next_reminder_date(self, remind_datetime, next, now, id='未定'):
        count = 0
        next_remind_datetime = self.calc_next_reminder_date(remind_datetime, next)
        if next_remind_datetime is None:
            return None
        while(next_remind_datetime <= now):
            next_remind_datetime = self.calc_next_reminder_date(next_remind_datetime, next)
            count += 1
            # countが100を超えた場合は異常なので、処理を中断
            if count > 100:
                LOG.warning(f'No.{id}の{next}を100回実行しても、現実時間に追いつかないため、None扱いとします。')
                next_remind_datetime = None
                break
        return next_remind_datetime

    def check_printer_is_running(self):
        if not self.printer.is_running():
            msg = 'Taskが停止していたので再起動します。'
            LOG.info(msg)
            self.printer.start()

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, ex):
        '''
        slash_commandでエラーが発生した場合の動く処理
        '''
        try:
            raise ex
        except discord.ext.commands.PrivateMessageOnly:
            await ctx.send(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', hidden = True)
        except discord.ext.commands.NoPrivateMessage:
            await ctx.send(f'エラーが発生しました(ギルドでのみ実行できます(DMやグループチャットでは実行できません))', hidden = True)
        except discord.ext.commands.NotOwner:
            await ctx.send(f'エラーが発生しました(Botのオーナーのみ実行できます)', hidden = True)
        except discord.ext.commands.MissingPermissions:
            if ex.missing_perms[0] == 'administrator':
                await ctx.send(f'エラーが発生しました(ギルドの管理者のみ実行できます)', hidden = True)
        except:
            await ctx.send(f'エラーが発生しました({ex})', hidden = True)

# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    LOG.info('DiscordReminderBotを読み込む！')
    bot.add_cog(ReminderCog(bot))  # ReminderCogにBotを渡してインスタンス化し、Botにコグとして登録する。
