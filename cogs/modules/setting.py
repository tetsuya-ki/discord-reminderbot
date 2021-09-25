import os
from os.path import join, dirname
from dotenv import load_dotenv
from logging import DEBUG, INFO, WARNING, ERROR

def if_env(str):
    '''
    strをTrue／Falseに変換(NoneのときはFalse)
    '''
    if str is None:
        return False
    elif str.upper() == 'TRUE':
        return True
    else:
        return False

def get_log_level(str):
    '''
    ログレベルを設定(Noneや無効のときはWARNING)
    '''
    if str is None:
        return WARNING

    upper_str = str.upper()
    if upper_str == 'DEBUG':
        return DEBUG
    elif upper_str == 'INFO':
        return INFO
    elif upper_str == 'ERROR':
        return ERROR
    else:
        return WARNING

# 環境変数をファイルから読み込む
load_dotenv(verbose=True)
dotenv_path = join(dirname(__file__), 'files' + os.sep + '.env')
load_dotenv(dotenv_path)

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
LOG_LEVEL = get_log_level(os.environ.get('LOG_LEVEL'))
ENABLE_SLASH_COMMAND_GUILD_ID_LIST = os.environ.get('ENABLE_SLASH_COMMAND_GUILD_ID_LIST')
KEEP_DECRYPTED_FILE = not if_env(os.environ.get('KEEP_DECRYPTED_FILE'))
IS_HEROKU = if_env(os.environ.get('IS_HEROKU'))
IS_REPLIT = if_env(os.environ.get('IS_REPLIT'))
RESTRICT_ATTACHMENT_FILE = if_env(os.environ.get('RESTRICT_ATTACHMENT_FILE'))
PRIORITY_GUILD = os.environ.get('PRIORITY_GUILD')