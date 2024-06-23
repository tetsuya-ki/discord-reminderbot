from datetime import timedelta, timezone
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from discord.ext import tasks, commands
from discord import app_commands
from logging import getLogger
from typing import Literal
from .modules.remind import Remind
from .modules import settings

import datetime, dateutil.parser, discord, re

LOG = getLogger('reminderbot')


# コグとして用いるクラスを定義。
class ReminderCog(commands.Cog):
    guilds = settings.ENABLE_SLASH_COMMAND_GUILD_ID
    JST = timezone(timedelta(hours=9), 'JST')
    NUM_1to3keta = '^[0-9]{1,3}$'
    SHOW_ME = '自分のみ'
    NOT_SILENT = 'ふつう'

    # ReminderCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot
        self.remind = Remind(bot)
        self.info = None

    # 読み込まれた時の処理
    @commands.Cog.listener()
    async def on_ready(self):
        dm_guild = self.bot.guilds[0].id if len(self.bot.guilds) > 0 else None

        # PRIORITY_GUILDがある場合の上書き
        if settings.PRIORITY_GUILD and settings.PRIORITY_GUILD.isdecimal():
            pr_guild = [i for i in self.bot.guilds if i.id == int(settings.PRIORITY_GUILD)]
            if len(pr_guild) > 0:
                dm_guild = pr_guild[0].id
        await self.remind.prepare(dm_guild)  # dbを作成
        self.info = await self.bot.application_info()
        LOG.info('SQlite準備完了')
        LOG.debug(self.bot.guilds)
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=30.0)
    async def printer(self):
        now = datetime.datetime.now(self.JST)
        LOG.debug(f'printer is kicked.({now})')

        # LOG.info(discord.utils.get(self.bot.get_all_channels()))
        for remind in self.remind.remind_rows:
            remind_datetime = dateutil.parser.parse(f'{remind[1]} +0900 (JST)',
                                                    yearfirst=True)
            # リマインドを発動
            if remind_datetime <= now:
                # silentの設定
                silent_flg = False
                # メッセージ作成
                msg = re.sub(r'<br>|[\[\(【<]改行[\)\]」】>]|@{3}', '\n', remind[5])
                if re.search('@silent', msg, flags=re.IGNORECASE):
                    msg = re.sub(r' *@silent *', '', msg, flags=re.IGNORECASE)
                    silent_flg = True
                # ギルド対象、かつ、:xxxx:である場合、Sticker(スタンプ)の取得
                sticker_list = []
                if remind[2] and re.search(':\w+:', msg):
                    # Sticker取得のため、ギルドの取得
                    try:
                        guild = await self.bot.fetch_guild(remind[2])
                        # ギルドのStickerの数だけ繰り返す
                        for sticker in guild.stickers:
                            # 文章にStickerが含まれていれば、Stickerリストに追加し、文章から削除
                            if re.search(f':{sticker.name}:', msg, flags=re.IGNORECASE):
                                sticker_list.append(sticker)
                                msg = re.sub(f' *<?:{sticker.name}:(\d*)>? *', '', msg, flags=re.IGNORECASE)
                                if len(sticker_list) >= 3:
                                    break
                    except:
                        msg = f'＊＊＊ギルド:{remind[2]}の取得({remind[4]})に失敗しました！＊＊＊'
                        LOG.error(msg)

                        # リマインドを削除
                        try:
                            await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_ERROR)
                        except:
                            LOG.warning('リマインドを削除(フェッチ失敗/CH)/update中に失敗(ギルド内チャンネルのフェッチに失敗)')
                            continue
                        # 通知失敗について連絡
                        try:
                            get_control_channel = discord.utils.get(self.bot.get_all_channels(),guild__id=remind[2],name=self.remind.REMIND_CONTROL_CHANNEL)
                            remind_msg = await get_control_channel.send(f'@here No.{remind[0]}は権限不足などの原因でリマインドできませんでした。リマインドしたい場合は、投稿先チャンネルの設定見直しをお願いします\n> {remind[5]}')
                        except:
                            msg = f'＊＊＊さらに、{remind[2]}のチャンネル({self.remind.REMIND_CONTROL_CHANNEL})への投稿に失敗しました(フェッチ失敗投稿後)！＊＊＊'
                            LOG.error(msg)
                            continue
                # DMの対応
                if remind[2] is None:
                    channel = await self.create_dm(remind[3])
                    try:
                        remind_msg = await channel.send(msg, silent=silent_flg)
                    except discord.errors.Forbidden:
                        msg = f'＊＊＊{remind[3]}のDMへの投稿に失敗しました！＊＊＊'
                        LOG.error(msg)

                        # リマインドを削除
                        try:
                            await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_ERROR)
                        except:
                            LOG.warning('リマインドを削除(投稿失敗/DM)/update中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
                            continue

                        # DMの通知失敗について連絡
                        try:
                            get_control_channel = discord.utils.get(self.bot.get_all_channels(),guild__id=self.remind.saved_dm_guild,name=self.remind.REMIND_CONTROL_CHANNEL)
                            remind_msg = await get_control_channel.send(f'No.{remind[0]}(DM)は権限不足などの原因でリマインドできませんでした')
                        except:
                            msg = f'＊＊＊さらに、{self.remind.saved_dm_guild}(saved_dm_guild)のチャンネル({self.remind.REMIND_CONTROL_CHANNEL})への投稿に失敗しました！＊＊＊'
                            LOG.error(msg)
                            continue
                # ギルド対応
                else:
                    channel = discord.utils.get(self.bot.get_all_channels(), guild__id=remind[2], id=remind[4])
                    # チャンネルへの投稿
                    if channel is not None:
                        try:
                            remind_msg = await channel.send(msg, silent=silent_flg, stickers=sticker_list)
                        except:
                            msg = f'＊＊＊{remind[2]}のチャンネルへの投稿に失敗しました！＊＊＊'
                            LOG.error(msg)

                            # リマインドを削除
                            try:
                                await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_ERROR)
                            except:
                                LOG.warning('リマインドを削除(投稿失敗/CH)/update中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
                                continue

                            # 通知失敗について連絡
                            try:
                                get_control_channel = discord.utils.get(self.bot.get_all_channels(),guild__id=remind[2],name=self.remind.REMIND_CONTROL_CHANNEL)
                                remind_msg = await get_control_channel.send(f'@here No.{remind[0]}は権限不足などの原因でリマインドできませんでした。リマインドしたい場合は、投稿先チャンネルの設定見直しをお願いします\n> {remind[5]}')
                            except:
                                msg = f'＊＊＊さらに、{remind[2]}のチャンネル({self.remind.REMIND_CONTROL_CHANNEL})への投稿に失敗しました！＊＊＊'
                                LOG.error(msg)
                                continue

                            continue
                    # スレッドへの投稿
                    else:
                        try:
                            guild = await self.bot.fetch_guild(remind[2])
                            # utilsやget_channel_or_threadで取得。無理な場合はfetch_channelで取得
                            thread = guild.get_channel_or_thread(remind[4])
                            if thread is None:
                                thread = await guild.fetch_channel(remind[4])
                            remind_msg = await thread.send(msg, silent=silent_flg, stickers=sticker_list)
                        except:
                            msg = f'＊＊＊{remind[2]}のスレッド({remind[4]})への投稿に失敗しました！＊＊＊'
                            LOG.error(msg)

                            # リマインドを削除
                            try:
                                await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_ERROR)
                            except:
                                LOG.warning('リマインドを削除(投稿失敗/CH)/update中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
                                continue

                            # 通知失敗について連絡
                            try:
                                get_control_channel = discord.utils.get(self.bot.get_all_channels(),guild__id=remind[2],name=self.remind.REMIND_CONTROL_CHANNEL)
                                remind_msg = await get_control_channel.send(f'@here No.{remind[0]}は権限不足などの原因でリマインドできませんでした。リマインドしたい場合は、投稿先スレッドの設定見直しをお願いします\n> {remind[5]}')
                            except:
                                msg = f'＊＊＊さらに、{remind[2]}のチャンネル({self.remind.REMIND_CONTROL_CHANNEL})への投稿に失敗しました(スレッド投稿後)！＊＊＊'
                                LOG.error(msg)
                                continue
                # リマインドを削除
                try:
                    await self.remind.update_status(remind[0], remind[2], self.remind.STATUS_FINISHED)
                except:
                    LOG.warning('リマインドを削除/update中に失敗(リマインドを削除/おそらく添付用チャンネルの作成、または、添付に失敗)')
                    continue

                # リマインドを繰り返す場合の処理
                if remind[9] == '1':
                    try:
                        if remind[2]:
                            await self.bot.fetch_guild(remind[2])
                    except:
                        LOG.warning(f'No.{remind[0]}(guild:{remind[2]}が取得できなかったため、繰り返し対象外とします。')
                        continue

                    # BANチェック
                    if self.remind.check_deleted_member(remind[3]) > 0 or self.remind.check_deleted_member(remind[3], remind[2], True) > 0:
                        LOG.info('BANされているため、次回のリマインドを登録できませんでした')
                        continue

                    # remind[10](repeat_interval)に従って、次のリマインドを作成
                    # remind_datetimeは次の日付に変換（ちょっと難しいところ）
                    next_remind_datetime = self.check_next_reminder_date(remind_datetime, remind[10], now,remind[0])

                    # 計算できなかったら、飛ばす
                    if next_remind_datetime is None:
                        LOG.warning(f'No.{remind[0]}の{remind[10]}が計算できなかったため、飛ばしました。')
                        await remind_msg.reply(f'次回のリマインドに失敗しました(No.{remind[0]}の{remind[10]}が計算できなかったため)')
                        continue

                    status = self.remind.STATUS_PROGRESS

                    # 繰り返し回数のチェック
                    repeat_count = remind[7] + 1
                    repeat_flg = self.check_repeat_num_and_calc(remind, repeat_count)
                    if repeat_flg == 'NG':
                        continue

                    # 繰り返し時のメッセージを変更(最後の行がURLの場合は繰り返し番号をつけない)
                    remind_message = self.check_message_last_line_is_url(remind, repeat_count)

                    id = await self.remind.make(remind[2], remind[3], next_remind_datetime, remind_message, remind[4], status, repeat_flg,
                        remind[10], repeat_count, remind[8])
                    try:
                        # 返信にリマインド予定日時記載(<t:unix時間:F>でいい感じに表示)
                        msg = f'次回のリマインドを登録しました(No.{id})\nリマインド予定日時: <t:{int(next_remind_datetime.timestamp())}:F>'
                        await remind_msg.reply(msg, silent=True)
                    except:
                        # 投稿に失敗した場合は登録を削除してしまう
                        await self.remind.update_status(id, remind[2], self.remind.STATUS_ERROR)
                        LOG.error(f'channelがないので、メッセージ送れませんでした！(No.{id})')

            else:
                break

    @app_commands.command(
        name='remind-make',
        description='remindを作成する')
    @app_commands.describe(
        date='日付(mm/dd形式)、もしくは、何日後かの数字1桁(0-9)。年がある場合はyyyy/mm/dd形式(yyyy-mm-dd形式も可)')
    @app_commands.describe(
        time='時間(hh24:mi形式)、もしくは、xxh(xxは数字(0-9)。xx時間後)、xxmi(xx分後)')
    @app_commands.describe(
        message='メッセージ(<br>か@@@などで改行。メンションは通常のメッセージのように @xxxx と書く。@silentでこっそり)')
    @app_commands.describe(
        repeat_interval='繰り返し間隔(数字+英字を付与：分(mi)/時間(h)/日(d)/週(w)/月(m)/年(y)か、特殊(平日/休日/月初/月末/曜日文字列(「月水」など)))')
    @app_commands.describe(
        repeat_max_count='繰り返し最大数(設定がない場合、ずっと繰り返されます)')
    @app_commands.describe(
        channel='リマインドを投稿するチャンネル(#general等。「DM」でBotとのDMへ登録されます。未指定の場合はリマインド登録したチャンネルに投稿)')
    @app_commands.describe(
        silent='こっそり送信(メッセージに@silentでも可)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def _remind_make(self,
                        interaction: discord.Interaction,
                        date: str,
                        time: str,
                        message: str,
                        repeat_interval: str = None,
                        repeat_max_count: app_commands.Range[int, 1, 999] = None,
                        channel: str = None,
                        silent: Literal['ふつう', 'こっそり'] = NOT_SILENT,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindをmakeするぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        silent_mode = True if silent != self.NOT_SILENT else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # ギルドの設定
        if interaction.guild is not None:
            guild_id = interaction.guild.id
        else:
            if channel is not None and channel.upper() != 'DM':
                msg = 'DMでチャンネル指定はできません。チャンネルは未指定でリマインドを登録ください。'
                await interaction.followup.send(msg, ephemeral=True)
                LOG.info(msg)
                return

            channel,guild_id = None,None

        # BANチェック
        if self.remind.check_deleted_member(interaction.user.id) > 0 or self.remind.check_deleted_member(interaction.user.id, guild_id, True) > 0:
            error_message = '不正な状態のため、リマインドを登録できませんでした'
            LOG.info(error_message)
            await interaction.followup.send(error_message, ephemeral=False)
            return

        # 分指定チェック(分指定の場合は5回以下である必要がある)
        if repeat_interval is not None and \
            re.search('mi', repeat_interval, flags=re.IGNORECASE) and \
            (repeat_max_count is None or (repeat_max_count is not None and repeat_max_count > 5)):
            error_message = '分指定(**XXmi**)の場合は必ず5回以下の繰り返し回数を指定してください'
            LOG.info(error_message)
            await interaction.followup.send(error_message, ephemeral=False)
            return

        # dateの確認&変換
        date = self.check_date_and_convert(date)
        # 時間の変換
        time, add_day = self.check_time_and_convert(time)
        if time == 'NG':
            error_message = '不正な時間のため、リマインドを登録できませんでした'
            LOG.info(error_message)
            await interaction.followup.send(error_message, ephemeral=True)
            return

        # リマインド日時への変換
        remind_datetime = None
        try:
            remind_datetime = dateutil.parser.parse(
                f'{date} {time} +0900 (JST)', yearfirst=True)
            # 1日加算の処理
            remind_datetime = remind_datetime + relativedelta(days=+int(add_day))
        except ValueError as e:
            error_message = '不正な日時のため、リマインドを登録できませんでした'
            LOG.info(error_message)
            LOG.info(e)
            await interaction.followup.send(error_message, ephemeral=True)
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
                await interaction.followup.send(error_message, ephemeral=True)
                return
            repeat_flg  = '1'

        repeat_count = 1

        # チャンネルの設定(指定なしなら投稿されたチャンネル、指定があればそちらのチャンネルとする)
        channel_id = None
        if channel is not None:
            temp_channel = discord.utils.get(interaction.guild.text_channels, name=channel)
            if channel.upper() == 'DM': # チャンネルが'DM'なら、ギルドとチャンネルをNoneとする
                guild_id = None
                if self.remind.saved_dm_guild is None:
                    msg = 'ギルドが何も登録されていない段階で、DMを登録することはできません。ギルドを登録してから再度リマインドの登録をしてください。'
                    await interaction.followup.send(msg, ephemeral=True)
                    LOG.info(msg)
                    return
                # DMのチェック(BotとのDMでリマインド作成していない場合は、送信できるか不確定のため)
                dm_channel = await self.create_dm(interaction.user.id)
                try:
                    # await dm_channel.typing() # typingで送信できるかチェックできたら嬉しかったけれど、これじゃチェックできなかった...
                    await dm_channel.send(content='リマインドできるか事前チェックです...。数秒後に消えます', delete_after=3, silent=True) # 実際に送信してみて、DMできるかチェックする
                except:
                    msg = 'リマインド登録に失敗しました。DM(ダイレクトメッセージ)できません。\nこのBotのあるサーバーの「プライバシー設定」で「サーバーにいるメンバーからのダイレクトメッセージを許可する」をONにしてください。」'
                    await interaction.followup.send(msg, ephemeral=True)
                    LOG.error(msg)
                    return

            elif temp_channel is None:
                temp_channel_id = re.sub(r'[<#>]', '', channel)
                if temp_channel_id.isdecimal() and '#' in channel:
                    channel_id = int(temp_channel_id)
                else:
                    msg = 'チャンネル名が不正です。もう一度、適切な名前で登録してください(#チャンネル名でもOK)。'
                    await interaction.followup.send(msg, ephemeral=True)
                    LOG.info(msg)
                    return
            else:
                channel_id = temp_channel.id
        else:
            # チャンネルが設定されておらず、ギルドが無いなら、ギルドとチャンネルをNoneとする
            # DMでリマインド登録されている時点で、Botからも送信可能であるため、DMチェックは不要
            if guild_id is None:
                channel_id = None
            # ギルドがあり、チャンネルが取得できるならそのチャンネルを使う
            else:
                # sendが存在しない場合は、ボイスチャンネル内チャンネルと想定
                if not hasattr(interaction.channel, 'send'):
                    msg = 'リマインド登録に失敗しました。ボイスチャンネル内のチャンネルは指定できません(DMで申し訳ないです)\n他のチャンネルで実行するか、オプションのchannel部分をボイスチャンネル以外で登録してください(#チャンネル名でもOK)'
                    await interaction.followup.send(msg, ephemeral=True)
                    LOG.info(msg)
                    return
                channel_id = interaction.channel.id

        # DM以外の場合、チャンネルに送信できるか事前チェック
        if guild_id is not None:
            channel = discord.utils.get(interaction.guild.text_channels, id=channel_id)
            try:
                await channel.send(content='リマインドできるか事前チェックです...。数秒後に消えます', delete_after=3, silent=True)
            except:
                try:
                    thread = discord.utils.get(interaction.guild.threads, id=channel_id)
                    await thread.send(content='リマインドできるか事前チェックです...。数秒後に消えます', delete_after=3, silent=True)
                except:
                    msg = 'リマインド登録に失敗しました。Botは指定されたチャンネルにメッセージ送信できません。\n送信先のチャンネルで、このBotのメッセージ送信権限を許可してください。'
                    await interaction.followup.send(msg, ephemeral=True)
                    LOG.error(msg)
                    return

        # silentの設定(silentならこっそり先頭に@silent付与)
        if silent_mode:
            message = '@silent ' + message
        # 実際の処理(remind.pyでやる)
        try:
            id = await self.remind.make(guild_id, interaction.user.id, remind_datetime, message, channel_id, status, repeat_flg,
                            repeat_interval, repeat_count, repeat_max_count)
        except:
            # 失敗した場合自分で最後のidを取得
            id = self.remind.get_last_id()
            LOG.warning('コマンドremind_make中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')

        # 返信にリマインド予定日時記載(<t:unix時間:F>でいい感じに表示)
        msg = f'リマインドを登録しました(No.{id})\nリマインド予定日時: <t:{int(remind_datetime.timestamp())}:F>'
        await interaction.followup.send(msg, ephemeral = hidden)

    @app_commands.command(
        name='remind-cancel',
        description='remindをキャンセルする')
    @app_commands.describe(
        cancel_no='キャンセルするリマインドの番号(No)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def remind_cancel(self,
                        interaction: discord.Interaction,
                        cancel_no: app_commands.Range[int, 1, 999999999999],
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindをcancelするぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # コマンド実行者が指定したNoのリマインドを持っているかチェック
        id = int(cancel_no)
        row = self.remind.get(interaction, id)
        owner_flg = interaction.user == self.info.owner
        dm_flg = interaction.guild is None
        guild_admin_flg = interaction.user.guild_permissions.administrator if not dm_flg else False
        cancel_id_is_none_msg = 'リマインドをキャンセルできませんでした(Noが違う可能性があります)'
        cancel_msg = f'リマインドをキャンセルしました(No.{cancel_no})'
        if row is None:
            if  not owner_flg and (not dm_flg and not guild_admin_flg):
                # オーナー以外かギルドで管理者以外が実行(一般ユーザが実行し、対象が存在しないパターン)
                await interaction.followup.send(cancel_id_is_none_msg, ephemeral=True)
                LOG.info(cancel_id_is_none_msg)
                return
            else:
                row = self.remind.get_by_owner(id)
                if row is None or (dm_flg and not owner_flg):
                    # 全部みたけどない OR DMでBot管理者以外が実行
                    await interaction.followup.send(cancel_id_is_none_msg, ephemeral=True)
                    LOG.info(cancel_id_is_none_msg)
                    return
                elif not dm_flg and guild_admin_flg:
                    # ギルドで管理者が実行(ギルドチェックが必要)
                    if str(row[2]) == str(interaction.guild.id):
                        cancel_msg = 'ギルド管理者が' + cancel_msg
                else:
                    # Bot管理者が実行
                    cancel_msg = 'Botオーナーが' + cancel_msg

        # 添付する際にギルドIDが必要なので準備する(DMの場合はNone(デフォルトのギルドへ登録する))
        guild_id = interaction.guild.id if interaction.guild is not None else None

        # リマインドをキャンセル
        try:
            await self.remind.update_status(id, guild_id, self.remind.STATUS_CANCELED)
        except:
            LOG.warning('コマンドremind_cancel中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')

        await interaction.followup.send(cancel_msg, ephemeral = hidden)
        LOG.info(cancel_msg)

    @app_commands.command(
        name='remind-skip',
        description='remindをスキップする。日付、時間未指定の場合は次回をスキップ')
    @app_commands.describe(
        skip_no='スキップするリマインドの番号(No)')
    @app_commands.describe(
        next_date='リマインド再開日付。日付(mm/dd形式)、もしくは、何日後かの数字1桁(0-9)。年がある場合はyyyy/mm/dd形式(yyyy-mm-dd形式も可)')
    @app_commands.describe(
        next_time='リマインド再開時間。時間(hh24:mi形式)、もしくは、xxh(xxは数字(0-9)。xx時間後)、xxmi(xx分後)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def remind_skip(self,
                        interaction: discord.Interaction,
                        skip_no: app_commands.Range[int, 1, 999999999999],
                        next_date: str = None,
                        next_time: str = None,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindをskipするぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden, thinking=False)

        # コマンド実行者が指定したNoのリマインドを持っているか、繰り返し対象かチェック
        id = int(skip_no)
        row = self.remind.get(interaction, id)
        if row is None:
            skip_no_is_none_msg = 'リマインドをスキップできませんでした(Noが違う可能性があります)'
            await interaction.followup.send(skip_no_is_none_msg, ephemeral=True)
            LOG.info(skip_no_is_none_msg)
            return
        elif row[9] != '1':
            skip_no_is_wrong_msg = 'リマインドが繰り返しされていないため、スキップできませんでした(Noが違う可能性があります)'
            await interaction.followup.send(skip_no_is_wrong_msg, ephemeral=True)
            LOG.info(skip_no_is_wrong_msg)
            return

        # 添付する際にギルドIDが必要なので準備する(DMの場合はNone(デフォルトのギルドへ登録する))
        guild_id = interaction.guild.id if interaction.guild is not None else None

        # 日付、時間が両方とも未指定の場合は次回スキップとみなす(時間に1mが指定されているものとする)
        if next_date is None and next_time is None:
            next_time = '1mi'

        # リマインド日付の変換
        remind_datetime = None
        try:
            remind_datetime = dateutil.parser.parse(
                f'{row[1]} +0900 (JST)', yearfirst=True)
        except ValueError as e:
            LOG.info(error_message)
            LOG.info(e)
            await interaction.followup.send(error_message, ephemeral=True)
            return

        # dateの確認&変換
        if next_date is None:
            next_date = remind_datetime.strftime('%Y-%m-%d')
        date = self.check_date_and_convert(next_date, remind_datetime)
        # 時間の変換
        if next_time is None:
            next_time = remind_datetime.strftime('%H:%M')
        time, add_day = self.check_time_and_convert(next_time, remind_datetime)
        error_message = '不正な時間のため、スキップできませんでした'
        if time == 'NG':
            LOG.info(error_message)
            await interaction.followup.send(error_message, ephemeral=True)
            return

        # リマインド日時への変換
        next_remind_datetime = None
        try:
            next_remind_datetime = dateutil.parser.parse(
                f'{date} {time} +0900 (JST)', yearfirst=True)
            # 1日加算の処理
            next_remind_datetime = next_remind_datetime + relativedelta(days=+int(add_day))
        except ValueError as e:
            LOG.info(error_message)
            LOG.info(e)
            await interaction.followup.send(error_message, ephemeral=True)
            return

        # 繰り返し回数のチェック
        repeat_count = row[7] + 1
        repeat_flg = self.check_repeat_num_and_calc(row, repeat_count)
        if repeat_flg == 'NG':
            error_message = '繰り返し回数で不正な状態が見つかったため、スキップできませんでした'
            LOG.info(error_message)
            await interaction.followup.send(error_message, ephemeral=True)
            return

        # リマインドをスキップ
        try:
            await self.remind.update_status(id, guild_id, self.remind.STATUS_SKIPPED)
        except:
            LOG.warning('コマンドremind_skip中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')

        # 繰り返し時のメッセージを変更(最後の行がURLの場合は繰り返し番号をつけない)
        remind_message = self.check_message_last_line_is_url(row, repeat_count)
        display_next_remind_datetime = next_remind_datetime.strftime('%Y/%m/%d(%a) %H:%M:%S')

        id = await self.remind.make(row[2], row[3], next_remind_datetime, remind_message, row[4], self.remind.STATUS_PROGRESS, repeat_flg,
            row[10], repeat_count, row[8])
        skip_msg = f'リマインドを1回スキップしました(No.{skip_no})\n次回のリマインドを登録しました(No.{id})\n再開日時: {display_next_remind_datetime}'
        try:
            await interaction.followup.send(skip_msg, ephemeral = hidden)
            LOG.info(skip_msg)
        except:
            # 投稿に失敗した場合は登録を削除してしまう
            await self.remind.update_status(id, row[2], self.remind.STATUS_ERROR)
            LOG.error(f'channelがないので、メッセージ送れませんでした！(No.{id})')

    @app_commands.command(
        name='remind-id-user-delete',
        description='<注意>remindを作ったユーザーのものをすべて削除する(Botのオーナーのみ実行可能です！)')
    @app_commands.describe(
        delete_no='削除したいユーザーのリマインドの番号(No)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def remind_id_user_delete(self,
                        interaction: discord.Interaction,
                        delete_no: app_commands.Range[int, 1, 999999999999],
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.user != self.info.owner:
            await interaction.response.send_message('このコマンドはBotのオーナー以外は実行できません', ephemeral = True)
            return
        LOG.info('remindしたユーザーをdeleteするぜ！(owner)')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # 指定したNoのリマインドが存在するかチェック
        id = int(delete_no)
        row = self.remind.get_by_owner(id)
        if row is None:
            delete_id_is_none_msg = 'リマインド対象のユーザーの削除ができませんでした(Noが違う可能性があります)'
            await interaction.followup.send(delete_id_is_none_msg, ephemeral=True)
            LOG.info(delete_id_is_none_msg)
            return

        # 添付する際にギルドIDが必要なので準備する(DMの場合はNone(デフォルトのギルドへ登録する))
        guild_id = interaction.guild.id if interaction.guild is not None else None

        # リマインド削除(&BAN) ＊指定されたデータに加え、現在PROGRESS状態のものを削除
        try:
            await self.remind.delete_remind_by_id(id, guild_id)
            await self.remind.delete_remind_by_user_id(row[3], guild_id)
        except:
            LOG.warning('コマンドremind_id_user_delete中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
        delete_msg = f'リマインド対象のユーザーの削除を実施しました(No.{delete_no})'

        await interaction.followup.send(delete_msg, ephemeral = hidden)
        LOG.info(delete_msg)

    @app_commands.command(
        name='remind-id-user-recover',
        description='<注意>削除されたユーザーを復活する(データは復活しません/Botのオーナーのみ実行可能です！)')
    @app_commands.describe(
        recover_no='復活させたいユーザーのリマインドの番号(No)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def remind_id_user_recover(self,
                        interaction: discord.Interaction,
                        recover_no: app_commands.Range[int, 1, 999999999999],
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.user != self.info.owner:
            await interaction.response.send_message('このコマンドはBotのオーナー以外は実行できません', ephemeral = True)
            return
        LOG.info('remindしたユーザーをrecoverするぜ！(owner)')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # 指定したNoのリマインド(DELETED)が存在するかチェック
        id = int(recover_no)
        row = self.remind.recovery_check(id)
        if row is None:
            recover_id_is_none_msg = 'リマインド対象のユーザーの復活ができませんでした(Noが違う可能性があります)'
            await interaction.followup.send(recover_id_is_none_msg, ephemeral=True)
            LOG.info(recover_id_is_none_msg)
            return

        # 添付する際にギルドIDが必要なので準備する(DMの場合はNone(デフォルトのギルドへ登録する))
        guild_id = interaction.guild.id if interaction.guild is not None else None

        # リマインドユーザーの復活
        try:
            await self.remind.recover_remind_by_user_id(row[3], guild_id)
        except:
            LOG.warning('コマンドremind_id_user_recover中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
        recover_msg = f'リマインド対象のユーザーの復活を実施しました(No.{recover_no})'

        await interaction.followup.send(recover_msg, ephemeral = hidden)
        LOG.info(recover_msg)


    @app_commands.command(
        name='remind-id-user-guild-delete',
        description='<注意>remindを作ったユーザーのものをギルドから削除する(administrator権限保持者のみ実行可能です！)')
    @app_commands.describe(
        delete_no='削除したいユーザーのリマインドの番号(No)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def remind_id_user_guild_delete(self,
                        interaction: discord.Interaction,
                        delete_no: app_commands.Range[int, 1, 999999999999],
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.guild is None:
            await interaction.response.send_message('想定外のエラーが発生したため、処理を注意しました', ephemeral = True)
            return
        LOG.info('remindしたユーザーをdeleteするぜ！(guild)')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # 指定したNoのリマインドが存在するかチェック
        id = int(delete_no)
        row = self.remind.get_by_owner(id, '', interaction.guild.id)
        if row is None:
            delete_id_is_none_msg = 'リマインド対象のユーザーの削除ができませんでした(Noが違う可能性があります)'
            await interaction.followup.send(delete_id_is_none_msg, ephemeral=True)
            LOG.info(delete_id_is_none_msg)
            return

        # リマインド削除(&BAN) ＊指定されたデータに加え、現在PROGRESS状態のものを削除
        try:
            await self.remind.delete_remind_by_id(id, interaction.guild.id, True)
            await self.remind.delete_remind_by_user_id(row[3], interaction.guild.id, True)
        except:
            LOG.warning('コマンドremind_id_user_delete中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
        delete_msg = f'リマインド対象のユーザーの削除を実施しました(No.{delete_no})'

        await interaction.followup.send(delete_msg, ephemeral = hidden)
        LOG.info(delete_msg)

    @app_commands.command(
        name='remind-id-user-guild-recover',
        description='<注意>削除されたユーザーを復活する(データは復活しません/administrator権限保持者のみ実行可能です！)')
    @app_commands.describe(
        recover_no='復活させたいユーザーのリマインドの番号(No)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def remind_id_user_guild_recover(self,
                        interaction: discord.Interaction,
                        recover_no: app_commands.Range[int, 1, 999999999999],
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.guild is None:
            await interaction.response.send_message('想定外のエラーが発生したため、処理を注意しました', ephemeral = True)
            return
        LOG.info('remindしたユーザーをrecoverするぜ！(guild)')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        self.check_printer_is_running()
        await interaction.response.defer(ephemeral = hidden)

        # 指定したNoのリマインド(DELETED)が存在するかチェック
        id = int(recover_no)
        row = self.remind.recovery_check(id, interaction.guild.id)
        if row is None:
            recover_id_is_none_msg = 'リマインド対象のユーザーの復活ができませんでした(Noが違う可能性があります)'
            await interaction.followup.send(recover_id_is_none_msg, ephemeral=True)
            LOG.info(recover_id_is_none_msg)
            return

        # リマインドユーザーの復活
        try:
            await self.remind.recover_remind_by_user_id(row[3], interaction.guild.id, True)
        except:
            LOG.warning('コマンドremind_id_user_recover中に失敗(おそらく添付用チャンネルの作成、または、添付に失敗)')
        recover_msg = f'リマインド対象のユーザーの復活を実施しました(No.{recover_no})'

        await interaction.followup.send(recover_msg, ephemeral = hidden)
        LOG.info(recover_msg)

    @app_commands.command(
        name='remind-list',
        description='remindを確認する')
    @app_commands.describe(
        status='リマインドリストで表示させるステータス')
    @app_commands.describe(
        filter='リマインドリストを検索')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def remind_list(self,
                        interaction: discord.Interaction,
                        status: Literal['実行予定のリマインドリスト(デフォルト)', 'キャンセルしたリマインドリスト', 'スキップしたリマインドリスト', '終了したリマインドリスト', 'エラーになったリマインドリスト'] = '実行予定のリマインドリスト(デフォルト)',
                        filter: str = None,
                        reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindをlistするぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        command_status = self.get_command_status(status)
        self.check_printer_is_running()

        rows = self.remind.list(interaction, command_status, filter)
        await interaction.followup.send(rows, ephemeral = hidden)

    @app_commands.command(
        name='remind-list-guild-all',
        description='<注意>ギルドのremindをぜんぶ確認する(administrator権限保持者のみ実行可能です！)')
    @app_commands.describe(
        status='リマインドリストで表示させるステータス')
    @app_commands.describe(
        filter='リマインドリストを検索')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def _remind_list_guild_all(self,
                                    interaction: discord.Interaction,
                                    status: Literal['実行予定のリマインドリスト(デフォルト)', 'キャンセルしたリマインドリスト', 'スキップしたリマインドリスト', '終了したリマインドリスト', 'エラーになったリマインドリスト', 'ギルドで削除されたリマインドリスト', 'ギルドで復活されたリマインドリスト'] = '実行予定のリマインドリスト(デフォルト)',
                                    filter: str = None,
                                    reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindをlist(guild)するぜ！')
        command_status = self.get_command_status(status)
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        rows = self.remind.list_all_guild(interaction, command_status, filter)
        await interaction.followup.send(rows, ephemeral = hidden)

    def check_on_dm(interaction: discord.Interaction) -> bool:
        return interaction.guild is None

    @app_commands.command(
        name='remind-list-all',
        description='<注意>remindをぜんぶ確認する(BotのオーナーのみDMで実行可能です！)')
    @app_commands.describe(
        status='リマインドリストで表示させるステータス')
    @app_commands.describe(
        filter='リマインドリストを検索')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    @app_commands.check(check_on_dm)
    async def _remind_list_all(self,
                            interaction: discord.Interaction,
                            status: Literal['実行予定のリマインドリスト(デフォルト)', 'キャンセルしたリマインドリスト', 'スキップしたリマインドリスト', '終了したリマインドリスト', 'エラーになったリマインドリスト', '削除されたリマインドリスト', '復活されたリマインドリスト', 'ギルドで削除されたリマインドリスト', 'ギルドで復活されたリマインドリスト'] = '実行予定のリマインドリスト(デフォルト)',
                            filter: str = None,
                            reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.user != self.info.owner:
            await interaction.response.send_message('このコマンドはBotのオーナー以外は実行できません', ephemeral = True)
            return
        LOG.info('remindをlist(owner)するぜ！')
        command_status = self.get_command_status(status)
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        rows = self.remind.list_all(interaction, command_status, filter)
        await interaction.followup.send(rows, ephemeral = hidden)

    @app_commands.command(
        name='remind-task-check',
        description='remindのTaskを確認する(リマインドが発動しない場合に実行してください)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def _remind_task_check(self,
                                interaction: discord.Interaction,
                                reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        LOG.info('remindのTaskを確認するぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        msg = 'Taskは問題なく起動しています。'
        self.check_printer_is_running()
        await interaction.followup.send(msg, ephemeral = hidden)

    @app_commands.command(
        name='delete-old-remind',
        description='<注意>完了したremindをぜんぶ削除する(BotのオーナーのみDMで実行可能です！)')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def _delete_old_remind(self,
                            interaction: discord.Interaction,
                            reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if interaction.user != self.info.owner:
            await interaction.response.send_message('このコマンドはBotのオーナー以外は実行できません', ephemeral = True)
            return
        LOG.info('remindをdelete(owner)するぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        await self.remind.delete_old_reminder(interaction)
        await interaction.followup.send('ステータスが完了のリマインドを全て削除しました', ephemeral = hidden)

    @app_commands.command(
        name='delete-own-remind',
        description='<注意>自分のremindをぜんぶ削除する')
    @app_commands.describe(
        confirm='削除したら元に戻せませんが、削除しますか？')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    async def _delete_own_remind(self,
                            interaction: discord.Interaction,
                            confirm: Literal['やっぱりやめておく', '削除する'] = 'やっぱりやめておく',
                            reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if confirm != '削除する':
            await interaction.response.send_message('自分の全リマインドの削除を取り消しました(削除にはオプションで「削除する」が必要です)', ephemeral = True)
            return
        LOG.info('自分のremindをdeleteするぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        message = await self.remind.delete_by_own(interaction)
        await interaction.followup.send(message, ephemeral = hidden)

    @app_commands.command(
        name='delete-guild-remind',
        description='<注意>ギルドのremindをぜんぶ削除する(administrator権限保持者のみ実行可能です！)')
    @app_commands.describe(
        confirm='削除したら元に戻せませんが、削除しますか？')
    @app_commands.describe(
        reply_is_hidden='Botの実行結果を全員に見せるどうか(リマインド自体は普通です/他の人にもリマインドを使わせたい場合、全員に見せる方がオススメです))')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def _delete_guild_remind(self,
                            interaction: discord.Interaction,
                            confirm: Literal['やっぱりやめておく', '削除する'] = 'やっぱりやめておく',
                            reply_is_hidden: Literal['自分のみ', '全員に見せる'] = SHOW_ME):
        if confirm != '削除する':
            await interaction.response.send_message('ギルドの全リマインドの削除を取り消しました(削除にはオプションで「削除する」が必要です)', ephemeral = True)
            return
        LOG.info('ギルドのremindをdelete(admin)するぜ！')
        hidden = True if reply_is_hidden == self.SHOW_ME else False
        await interaction.response.defer(ephemeral = hidden)
        self.check_printer_is_running()

        message = await self.remind.delete_guild_by_admin(interaction)
        await interaction.followup.send(message, ephemeral = hidden)

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

    def check_date_and_convert(self, date:str, base_date=None):
        if base_date is None:
            base_date = datetime.datetime.now(self.JST).date()
        if re.match(r'[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}', date) \
        or re.match(r'[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}', date) \
        or re.match(r'[0-9]{8}', date):
            pass
        elif re.match(r'^[0-9]{1,2}-[0-9]{1,2}', date):
            date = f'{base_date.year}-{date}'
        elif re.match(r'[0-9]{1,2}/[0-9]{1,2}', date):
            date = f'{base_date.year}/{date}'
        elif re.match(r'[0-9]{4}', date):
            date = f'{base_date.year}{date}'
        # エイリアス(特定の文字列の場合、日付に変換)
        elif date.lower().startswith('t'):
            date = base_date
        elif re.match(self.NUM_1to3keta, date):
            date = base_date + relativedelta(days=+int(date))
        return date

    def check_time_and_convert(self, time:str, base_time=None):
        add_day = 0
        result_time = None
        if base_time is None:
            base_time = datetime.datetime.now(self.JST)
        m_hours = re.match('^([0-9]{1,3})h$', time)
        m_minutes = re.match('^([0-9]{1,4})mi$', time)
        m_normal = re.match('^([0-9]{1,2}:[0-9]{1,2})$', time)
        if time == '0':
            time = base_time.strftime('%H:%M')
        elif m_hours:
            result_time = base_time + datetime.timedelta(hours=int(m_hours.group(1)))
            time = result_time.strftime('%H:%M')
        elif m_minutes:
            result_time = base_time + datetime.timedelta(minutes=int(m_minutes.group(1)))
            time = result_time.strftime('%H:%M')
        elif m_normal:
            pass
        else:
            return 'NG'

        # 1日加算の処理
        if result_time is not None and base_time.strftime('%Y/%m/%d') != result_time.strftime('%Y/%m/%d'):
            add_day = 1

        return time, add_day

    def check_repeat_num_and_calc(self, remind, repeat_count):
        remind_repeat_max_str = str(remind[8])
        if remind[8] is None or (remind_repeat_max_str.isdecimal() and repeat_count < remind[8]):
            repeat_flg = '1'
        elif remind_repeat_max_str.isdecimal() and repeat_count > remind[8]:
            LOG.warning(f'No.{remind[0]}のrepeat_max_count({remind_repeat_max_str})を超えているため、追加をしません。')
            repeat_flg = 'NG'
        else:
            repeat_flg = '0'
            if not remind_repeat_max_str.isdecimal():
                LOG.warning(f'繰り返し上限に数字以外が登録されました。remind[8]は{remind_repeat_max_str}')
        return repeat_flg

    def check_message_last_line_is_url(self, remind, repeat_count):
        last_remind_message = re.sub('\(\d+\)','', remind[5])
        last_line_url = re.search(r'https?://[a-zA-Z0-9/:%#\$&?()~.=+_-]+\Z', remind[5])
        remind_message =  remind[5]
        if repeat_count > 1 and last_line_url is None:
            remind_message = f'{last_remind_message}({repeat_count})'
        return remind_message

    def get_command_status(self, status):
        command_status = self.remind.STATUS_PROGRESS
        if status == 'キャンセルしたリマインドリスト':
            command_status = self.remind.STATUS_CANCELED
        elif status == 'スキップしたリマインドリスト':
            command_status = self.remind.STATUS_SKIPPED
        elif status == '終了したリマインドリスト':
            command_status = self.remind.STATUS_FINISHED
        elif status == 'エラーになったリマインドリスト':
            command_status = self.remind.STATUS_ERROR
        elif status == '削除されたリマインドリスト':
            command_status = self.remind.STATUS_DELETED
        elif status == '復活されたリマインドリスト':
            command_status = self.remind.STATUS_RECOVERED
        elif status == 'ギルドで削除されたリマインドリスト':
            command_status = self.remind.STATUS_DELETED_BY_GUILD
        elif status == 'ギルドで復活されたリマインドリスト':
            command_status = self.remind.STATUS_RECOVERED_BY_GUILD
        return command_status

    async def create_dm(self, user_id):
        remind_user = self.bot.get_user(user_id)
        text = remind_user or ''
        if remind_user is None:
            remind_user = await self.bot.fetch_user(user_id)
            text = remind_user or ''
        LOG.debug(f'user id :{str(user_id)}, user:{text}')
        return await remind_user.create_dm()

    async def cog_app_command_error(self, interaction, error):
        '''
        slash_commandでエラーが発生した場合の動く処理
        '''
        LOG.error(error)
        if isinstance(error, app_commands.CheckFailure):
            if interaction.command.name == 'remind-list-all':
                await interaction.response.send_message(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', ephemeral=True)
            else:
                await interaction.response.send_message(f'エラーが発生しました(コマンドが実行できません)', ephemeral=True)
        elif isinstance(error, discord.ext.commands.PrivateMessageOnly):
            await interaction.response.send_message(f'エラーが発生しました(DM(ダイレクトメッセージ)でのみ実行できます)', ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(f'エラーが発生しました(ギルドでのみ実行できます(DMやグループチャットでは実行できません))', ephemeral=True)
        elif isinstance(error, discord.ext.commands.NotOwner):
            await interaction.response.send_message(f'エラーが発生しました(Botのオーナーのみ実行できます)', ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            if error.missing_perms[0] == 'administrator':
                await interaction.response.send_message(f'エラーが発生しました(ギルドの管理者のみ実行できます)', ephemeral=True)
            else:
                await interaction.response.send_message(f'エラーが発生しました(権限が足りません)', ephemeral=True)
        elif isinstance(error, discord.errors.Forbidden):
            await interaction.response.send_message(f'エラーが発生しました(権限が足りません(おそらくBotが表示/編集できない))', ephemeral=True)
        else:
            await interaction.response.send_message(f'エラーが発生しました({error})', ephemeral=True)

# Bot本体側からコグを読み込む際に呼び出される関数。
async def setup(bot):
    LOG.info('DiscordReminderBotを読み込む！')
    await bot.add_cog(ReminderCog(bot))  # ReminderCogにBotを渡してインスタンス化し、Botにコグとして登録する。
