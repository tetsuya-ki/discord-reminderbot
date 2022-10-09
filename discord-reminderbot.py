from lib2to3.pgen2 import token
from cogs.modules import settings
from discord.ext import commands
from logging import basicConfig, getLogger, StreamHandler, FileHandler, Formatter, NOTSET
from datetime import timedelta, timezone
import discord, os, datetime, asyncio
import keep_alive

# 時間
JST = timezone(timedelta(hours=9), 'JST')
now = datetime.datetime.now(JST)

# ストリームハンドラの設定
stream_handler = StreamHandler()
stream_handler.setLevel(settings.LOG_LEVEL)
stream_handler.setFormatter(Formatter("%(asctime)s@ %(name)s [%(levelname)s] %(funcName)s: %(message)s"))

# 保存先の有無チェック
if not os.path.isdir('./Log'):
    os.makedirs('./Log', exist_ok=True)

# ファイルハンドラの設定
file_handler = FileHandler(
    f"./Log/log-{now:%Y%m%d}.log"
)
file_handler.setLevel(settings.LOG_LEVEL)
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
    # DiscordReminderBotのコンストラクタ。
    def __init__(self, command_prefix, intents, application_id):
        # スーパークラスのコンストラクタに値を渡して実行。
        super().__init__(command_prefix, case_insensitive=True, intents=intents, help_command=None, application_id=application_id) # application_idが必要

    async def setup_hook(self):
        # INITIAL_EXTENSIONに格納されている名前からCogを読み込む。
        LOG.info('cogを読むぞ！')
        for cog in INITIAL_EXTENSIONS:
            await self.load_extension(cog) # awaitが必要

        # テスト中以外は環境変数で設定しないことを推奨(環境変数があれば、ギルドコマンドとして即時発行される)
        if settings.ENABLE_SLASH_COMMAND_GUILD_ID is not None and len(settings.ENABLE_SLASH_COMMAND_GUILD_ID) > 0:
            LOG.info(settings.ENABLE_SLASH_COMMAND_GUILD_ID)
            for guild in settings.ENABLE_SLASH_COMMAND_GUILD_ID:
                LOG.info(guild)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
        else:
            await self.tree.sync() # グローバルコマンドとして発行(使用できるまで、最大1時間程度かかる)

    async def on_ready(self):
        LOG.info('We have logged in as {0.user}'.format(self))
        LOG.info(f"### guilds ### \n{self.guilds}")

async def main():
    # Botの起動
    async with bot:
        await bot.start(settings.DISCORD_TOKEN)
        LOG.info('We have logged in as {0}'.format(bot.user))

# discord-reminderbotのインスタンス化、および、起動処理
if __name__ == '__main__':
    intents = discord.Intents.all()
    intents.typing = False
    intents.members = False
    intents.presences = False
    intents.message_content = False

    bot = DiscordReminderBot(
            command_prefix = '/'
            ,intents=intents
            ,application_id=settings.APPLICATION_ID
        )
    asyncio.run(main())

    # start a server
    keep_alive.keep_alive()
    asyncio.run(main())