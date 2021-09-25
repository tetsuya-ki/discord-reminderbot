from cogs.modules import setting
from discord.ext import commands
from discord_slash import SlashCommand
# from discord_slash.utils import manage_commands # for delete slash command
from logging import basicConfig, getLogger, StreamHandler, FileHandler, Formatter, NOTSET
from datetime import timedelta, timezone
import discord, os, datetime
import keep_alive

# 時間
JST = timezone(timedelta(hours=9), 'JST')
now = datetime.datetime.now(JST)

# ストリームハンドラの設定
stream_handler = StreamHandler()
stream_handler.setLevel(setting.LOG_LEVEL)
stream_handler.setFormatter(Formatter("%(asctime)s@ %(name)s [%(levelname)s] %(funcName)s: %(message)s"))

# 保存先の有無チェック
if not os.path.isdir('./Log'):
    os.makedirs('./Log', exist_ok=True)

# ファイルハンドラの設定
file_handler = FileHandler(
    f"./Log/log-{now:%Y%m%d_%H%M%S}.log"
)
file_handler.setLevel(setting.LOG_LEVEL)
file_handler.setFormatter(
    Formatter("%(asctime)s@ %(name)s [%(levelname)s] %(funcName)s: %(message)s")
)

# ルートロガーの設定
basicConfig(level=NOTSET, handlers=[stream_handler, file_handler])

LOG = getLogger('reminderbot')

# 読み込むCogの名前を格納しておく。
INITIAL_EXTENSIONS = [
    'cogs.remindercog'
]

class DiscordReminderBot(commands.Bot):
    # MyBotのコンストラクタ。
    def __init__(self, command_prefix, intents):
        # スーパークラスのコンストラクタに値を渡して実行。
        super().__init__(command_prefix, case_insensitive=True, intents=intents, help_command=None)
        slash = SlashCommand(self, sync_commands=True) # ココにslashをおこう！(第一引数はself)
        LOG.info('cogを読むぞ！')

        # INITIAL_COGSに格納されている名前から、コグを読み込む。
        for cog in INITIAL_EXTENSIONS:
            self.load_extension(cog)

    async def on_ready(self):
        LOG.info('We have logged in as {0.user}'.format(self))
        LOG.info(f"### guilds ### \n{self.guilds}")

        # #### for delete slash command #####
        # guilds = [] if setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST is None else list(
        #     map(int, setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST.split(';')))
        # for guild in guilds:
        #     await manage_commands.remove_all_commands_in(self.user.id, setting.DISCORD_TOKEN, guild)
        #     LOG.info('remove all guild command for {0}.'.format(guild))

# discord-reminderbotbのインスタンス化、および、起動処理
if __name__ == '__main__':
    intents = discord.Intents.all()
    intents.typing = False
    intents.members = False
    intents.presences = False

    bot = DiscordReminderBot(command_prefix='/', intents=intents)

    # start a server
    keep_alive.keep_alive()
    bot.run(setting.DISCORD_TOKEN)