# cog.py
import discord
from discord.ext import commands
from .modules import setting
from discord_slash import cog_ext, SlashContext
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands # Allows us to manage the command settings.

# bot = discord.Client(command_prefix='/', intents=discord.Intents.all())
# slashClient = SlashCommand(bot, sync_commands=True)

class Slash(commands.Cog):
    guilds = [] if setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST is None else list(map(int, setting.ENABLE_SLASH_COMMAND_GUILD_ID_LIST.split(';')))

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="hello", guild_ids=guilds)
    async def _slash_hello(self, ctx: SlashContext):
        await ctx.send(content="Hello!")

    @cog_ext.cog_slash(name="moyashi", guild_ids=guilds, description='test command.')
    # @slashClient.slash(name="moyashi", guild_ids=[465376233115353098])
    async def _test(self, ctx: SlashContext):
        embed = discord.Embed(title="embed test")
        await ctx.send(content="test", embeds=[embed])

def setup(bot):
    bot.add_cog(Slash(bot))