from cogs.modules import setting
from discord.ext import commands
from discord_slash import SlashCommand
from logging import basicConfig, getLogger

import discord
import traceback

basicConfig(level=setting.LOG_LEVEL)
LOG = getLogger(__name__)

# 読み込むCogの名前を格納しておく。
INITIAL_EXTENSIONS = [
    'cogs.testcog'
    , 'cogs.remindercog'
    , 'cogs.slashcog'
]

async def on_ready(self):
    LOG.info('We have logged in as {0.user}'.format(self))

intents = discord.Intents.all()
intents.typing = False

bot = commands.Bot(command_prefix='/', intents=intents, case_insensitive=True)
slash = SlashCommand(bot, sync_commands=True)

for cog in INITIAL_EXTENSIONS:
    bot.load_extension(cog) # エラーを出したい時に使うぞ！
bot.run(setting.DISCORD_TOKEN)