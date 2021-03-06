
# このBotについて

- Discordでリマインダーを使うBotです(リマインドの定期実行も可能)
- スラッシュコマンド（[eunwoo1104 / discord-py-slash-command](https://github.com/eunwoo1104/discord-py-slash-command)）が使えるため、コマンドを覚える必要がなく、それぞれのオプションの意味が表示されます
  - [有名なリマインダーBotが定期実行に寄付が必要](https://qiita.com/kbt0401/items/1d26f2c99580647e12dc)という記事を見て作ってみました

## 機能

### `/remind-list`

- 自分がそのギルドで登録したリマインドを表示します

### `/remind-make`

- リマインドを登録します（登録したリマインドが**今は**表示されます）
  - 秘密なリマインドはコレで登録せず、ご自身のカレンダーやTODOへ登録するようにしてください
- 必須のオプション(3つ)
  - date(リマインド日時)
    - mm/dd形式
    - 日数でも登録できる(`0`で当日、`1`で1日後)
    - yyyy/mm/dd形式で年も含めて登録
    - mm-dd形式もOK(yyyy-mm-dd形式もOK)
  - time(リマインド時間)
    - hh:mi形式(例→`23:12`)
  - message(メッセージ)
    - リマインドするメッセージ
- オプション
  - repeat_interval(繰り返し間隔)
    - XX分: **XX**mi
    - XX時間: **XX**h
    - X日:  **X**d
    - Xヶ月: **X**m
    - X年: **X**y
      - Xは数字(例→`10mi`)
      - 通知した後、上記で指定しただけ遅らせた年月で通知するリマインドを作成します
  - repoeat_max_count(繰り返し最大回数)
    - 数字を設定
    - 例→`2`としたら、1回目の通知の後に**繰り返し間隔だけ遅らせたリマインドが作成されます**。2回目を通知し、それ以降は通知されません
      - 具体例: `/remind-make date:2021/3/26 time:21:00 message:@here test!!! repeat_interval:2d repeat_max_count:2`
        - 2021/3/26 21:00に「@here test!!!」が通知され、2回目として2021/3/28 21:00に「@here test!!!(2)」が通知されます
        - 2回目以降は勝手に、メッセージに連番をふります
      - 追加で通知したい場合は別途リマインドを作成してください
  - channel(リマインドするチャンネル)
    - #xxxxで指定したチャンネルにリマインドします
    - そのままチャンネル名を指定することもできます
    - このオプションが**ない場合、コマンドを実行したチャンネルにリマインドします**

### `/remind-cancel`

- リマインドをキャンセルします
- 必須のオプション(1つ)
  - cancel_no(キャンセルするリマインドのNo)
    - 数字
    - あなたが登録したリマインドのNoである必要があります（他人のリマインドはキャンセルできません）

### その他のコマンドは検討中です(リマインドの削除など実装予定)

## 環境変数

### DISCORD_TOKEN

- あなたのDiscordのトークンを記載（トークンは厳重に管理し、公開されないよう配慮すること！）
- 例: DISCORD_TOKEN="fdj2iur928u42q4u239858290"

### LOG_LEVEL

- ログレベル(DEBUG/INFO/WARNING/ERROR)
- 例: LOG_LEVEL="INFO"

### ENABLE_SLASH_COMMAND_GUILD_ID_LIST

- スラッシュコマンドを有効にするギルドID(複数ある場合は「;」を間に挟むこと)
- 例
  - 1件の場合: ENABLE_SLASH_COMMAND_GUILD_ID_LIST=18471289371923
  - 2件の場合: ENABLE_SLASH_COMMAND_GUILD_ID_LIST=18471289371923;1389103890128390

### KEEP_DECRYPTED_FILE

- 復号されたファイルを残すかどうか(TRUEの時のみ残す。デフォルトでは復号されたファイルは削除される)
- 例: KEEP_DECRYPTED_FILE=FALSE

### IS_HEROKU

- Herokuで動かすかどうか
  - Herokuの場合、ファイルが削除されるので、discordの添付ファイルを使って保管を試みる(ファイルが削除されていたら、読み込む)
- 例: IS_HEROKU=FALSE

### IS_REPLIT

- Repl.itで動かすかどうか
  - Repl.itの場合、sqlite3の保管が怪しいので、discordの添付ファイルを使って保管を試みる
- 例: IS_REPLIT=TRUE

## 動かし方

- wikiに書くつもりです(時期未定)
- わからないことがあれば[Discussions](https://github.com/tetsuya-ki/discord-reminderbot/discussions)に書いてみてください
