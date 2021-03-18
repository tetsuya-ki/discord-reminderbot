from cogs.modules import setting
from discord.ext import commands
from discord_slash import SlashCommand
from logging import basicConfig, getLogger

import discord
import keep_alive

basicConfig(level=setting.LOG_LEVEL)
LOG = getLogger(__name__)

# 読み込むCogの名前を格納しておく。
INITIAL_EXTENSIONS = [
    # 'cogs.taskcog'
    'cogs.remindercog'
    # , 'cogs.testcog'
    # , 'cogs.slashcog'
]

class DiscordReminderBot(commands.Bot):
    # MyBotのコンストラクタ。
    def __init__(self, command_prefix, intents):
        # スーパークラスのコンストラクタに値を渡して実行。
        super().__init__(command_prefix, case_insensitive=True, intents=intents)
        slash = SlashCommand(self, sync_commands=True) # ココにslashをおこう！(第一引数はself)
        LOG.info('cogを読むぞ！')

        # INITIAL_COGSに格納されている名前から、コグを読み込む。
        for cog in INITIAL_EXTENSIONS:
            self.load_extension(cog)

    async def on_ready(self):
        LOG.info('We have logged in as {0.user}'.format(self))

# discord-reminderbotbのインスタンス化、および、起動処理
if __name__ == '__main__':
    intents = discord.Intents.all()
    intents.typing = False
    intents.members = False
    intents.presences = False

    bot = DiscordReminderBot(command_prefix='/', intents=intents)
    # slash = SlashCommand(bot, sync_commands=True) #ここはダメ

    # start a server
    keep_alive.keep_alive()
    bot.run(setting.DISCORD_TOKEN)