from discord.ext import commands # Bot Commands Frameworkのインポート
from logging import getLogger

LOG = getLogger(__name__)

# コグとして用いるクラスを定義。
class TestCog(commands.Cog):

    # TestCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot

    # コマンドの作成。コマンドはcommandデコレータで必ず修飾する。
    @commands.command()
    async def ping(self, ctx):
        LOG.info('pong!するぜ！')
        await ctx.send('pong!')

    @commands.command()
    async def pong(self, ctx):
        LOG.info('ping!するぜ！')
        await ctx.send('ping!')

# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    LOG.info('TestCogを読み込む！')
    bot.add_cog(TestCog(bot)) # TestCogにBotを渡してインスタンス化し、Botにコグとして登録する。