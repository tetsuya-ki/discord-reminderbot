
# このBotについて

- Discordでリマインダーを使うBotです(リマインドの定期実行も可能)
- discord.py v2.0のスラッシュコマンドが使えるため、コマンドを覚える必要がなく、それぞれのオプションの意味が表示されます
  - [有名なリマインダーBotが定期実行に寄付が必要](https://qiita.com/kbt0401/items/1d26f2c99580647e12dc)という記事を見て作ってみました
- 以下の招待リンクからお試しできます
  - 招待リンク: <https://discord.com/api/oauth2/authorize?client_id=873515660674756639&permissions=2147723280&scope=bot%20applications.commands>
  - 止まってたりしたらこっそり教えてください(その前に、`/remind-task-check`で直るかもしれません)
- 上記Botの運営でお金がかかるので、[PIXIV FANBOXで支援を募ってみる](https://marukot-chan.fanbox.cc/posts/5541410)ことにしました
  - とくに支援しなくても全機能使えますが、支援してくださったらサーバーをクラウドにする等できるかもしれません
  - 支援がない場合でも可能な限り運営しますが、いつでも停止/一時停止される可能性があります
  - 支援者が数人いらっしゃったので、[v1.0.7](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.7)で追加でno_replyオプションを実装

## 利用者向け機能

### `/remind-list`

- ギルドで使用すると、自分がそのギルドで登録したリマインドを表示します
- BotとのDMで使用すると、自分が登録したリマインドを表示します
  - [v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)で日付の表示形式を変更
- オプション
  - status
    - 実行予定のリマインドリスト(デフォルトと同じ)
      - 今後リマインドされるリストを表示します
    - キャンセルしたリマインドリスト
      - キャンセルされたリマインドリストを表示します
    - スキップしたリマインドリスト([v1.0.2](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.2)で追加)
      - スキップされたリマインドリストを表示します
    - 終了したリマインドリスト
      - リマインドしたリストを表示します
    - エラーになったリマインドリスト
      - エラーになってしまったリストを表示します
  - filter
    - リマインドリストを検索
      - 検索対象は以下
        - No
        - 日付
        - メッセージ
        - 繰り返し設定
        - ギルドID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - メンバーID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - チャンネルID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
    - [v1.0.0](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.0)で追加
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-make`

- リマインドを登録します（登録したリマインドが**今は**表示されます）
  - 秘密なリマインドはコレで登録せず、ご自身のカレンダーやTODOへ登録するようにしてください
- 必須のオプション(3つ)
  - date(リマインド日時)
    - mm/dd形式
    - 日数でも登録できる(`0`で当日、`1`で1日後)
    - yyyy/mm/dd形式で年も含めて登録
    - mm-dd形式もOK(yyyy-mm-dd形式もOK)
    - mmdd形式もOK
    - 1-3桁の場合、現在日時+その日数後として登録
      - `0`→当日
      - `1`→1日後
      - `100`→100日後
  - time(リマインド時間)
    - 0(現在時間) ＊v1.0.1から
    - hh:mi形式(例→`23:12`)
    - xxh(xx時間後という意味。例→`10h`)
    - xxmi(xx分後という意味。例→`10mi`)
  - message(メッセージ)
    - リマインドするメッセージ
    - 改行したい場合は`<br>`、`<改行>`、`【改行】`、`@@@`のどれかを入力してください
      - 例→`改行テスト<br>改行したよ！`
    - メンションしたい場合、通常のメッセージと同様に、@xxxx形式で入力してください（リマインド時にメンションされます）
    - こっそり送りたい場合、`@silent`としてもよいです([v1.0.1](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.1)で追加)
      - オプションが欲しい人のために、別途オプションでも`silent`できます(こっそりメッセージの先頭につけるだけですが……)
    - スタンプ(Stickers)があればスタンプに変換([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
      - :ganbare:みたいにメッセージに紛れ込ませてください(Discordの予測変換的なのでやると、Botにいきませんので注意)
      - 最大3つ付与可能(スタンプの順番はテキトーです)

- オプション
  - repeat_interval(繰り返し間隔)
    - XX分: **XX**mi
      - 分単位での繰り返し間隔の場合、5回以下の繰り返し回数設定が必須になりました([v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)にて変更)
    - XX時間: **XX**h
    - X日:  **X**d
    - Xヶ月: **X**m
    - X年: **X**y
      - Xは数字(例→`10mi`)
      - 通知した後、上記で指定しただけ遅らせた年月で通知するリマインドを作成します
    - 特殊なもの
      - 平日: **平日**
        - 月曜日〜金曜日にリマインドされます(祝日は考慮しません)
      - 休日: **休日**
        - 土曜日〜日曜日にリマインドされます
      - 曜日: **月水**
        - 指定した曜日にリマインドされます(`月水金`のように複数指定できます)
  - repoeat_max_count(繰り返し最大回数)
    - 数字を設定
    - 例→`2`としたら、1回目の通知の後に**繰り返し間隔だけ遅らせたリマインドが作成されます**。2回目を通知し、それ以降は通知されません
      - 具体例: `/remind-make date:2021/3/26 time:21:00 message:@here test!!! repeat_interval:2d repeat_max_count:2`
        - 2021/3/26 21:00に「@here test!!!」が通知され、2回目として2021/3/28 21:00に「@here test!!!(2)」が通知されます
        - 2回目以降は勝手に、メッセージに連番をふります(URLの場合のみ連番をふりません)
      - 追加で通知したい場合は別途リマインドを作成してください
  - channel(リマインドするチャンネル)
    - #xxxxで指定したチャンネルにリマインドします
    - そのままチャンネル名を指定することもできます
    - このオプションが**ない場合、コマンドを実行したチャンネルにリマインドします**
      - ただし、ボイスチャンネル内のチャンネルで実行した場合は登録できません(DMで登録失敗の旨連絡)
  - silent(こっそり送る)
    - ふつう
      - 通常のメッセージです
    - こっそり
      - こっそりしたメッセージです。深夜帯や早朝にオススメ
      - discord曰く、「メッセージをそっと静かに送信」。受信者に通知の点は表示されます、アラートはありません、とのこと(プッシュ通知やデスクトップ通知されない)
    - [v1.0.1](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.1)で追加
  - no_reply(次回リマインドの返信なし)
    - 通常だと次回のリマインド予定を通知しますが、これを不要とするオプションです
      - 本当にリマインドが登録されているかはよくわからない状態になるので、適宜remind-listで確認ください
    - [v1.0.7](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.7)で追加
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-cancel`

- リマインドをキャンセルします([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で仕様変更あり)
- 必須のオプション(1つ)
  - cancel_no(キャンセルするリマインドのNo)
    - 数字
    - あなたが登録したリマインドのNoである必要があります（他人のリマインドはキャンセルできません）
    - ただし、**ギルド管理者の場合、ギルド内のリマインドもキャンセル可能**([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で変更)
    - ただし、**Botオーナーの場合、すべてのリマインドもキャンセル可能**([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で変更)
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-task-check`

- BotのTaskが正常に動いているかチェックする(止まってたらTaskを開始するはず)
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-skip`

- リマインドスキップします([v1.0.2](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.2)で追加)
  - オプションのリマインド再開日付と時間が両方とも未指定の場合は、1回スキップされます(リマインド再開時間に1miが指定されたものとしてスキップ)
- 必須のオプション(1つ)
  - skip_no(スキップするリマインドのNo)
    - 数字
    - あなたが登録したリマインドのNoである必要があります（他人のリマインドはスキップできません）
- オプション
  - next_date(リマインド再開日付)
    - mm/dd形式
    - 日数でも登録できる(`0`で当日、`1`で1日後)
    - yyyy/mm/dd形式で年も含めて登録
    - mm-dd形式もOK(yyyy-mm-dd形式もOK)
    - mmdd形式もOK
    - 1-3桁の場合、現在日時+その日数後として登録
      - `0`→当日
      - `1`→1日後
      - `100`→100日後
  - next_time(リマインド再開時間)
    - 0(現在時間)
    - hh:mi形式(例→`23:12`)
    - xxh(xx時間後という意味。例→`10h`)
    - xxmi(xx分後という意味。例→`10mi`)
      - ここの指定で時間が繰り上がる場合、おかしな挙動になるため注意してください([v1.0.2](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.2))
      - 例: 4/10 23:00が次回リマインドの時、2hを指定すると4/10 1:00となってしまう
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/delete-own-remind`

- 自分のリマインドをすべて削除します([v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)で追加)
- オプション
  - confirm(削除確認)
    - 削除するを選択したときのみ、削除します。
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

## ギルド管理者向けの機能

  ギルドの管理者権限保持者向けの機能です

### `/remind-list-guild-all`

- ギルド内のみ、かつ、ギルドの管理者権限保持者のみ使用可能
- そのギルドで登録されているリマインドをすべて表示します
  - [v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)で日付の表示形式を変更
- オプション
  - status
    - 実行予定のリマインドリスト(デフォルトと同じ)
      - 今後リマインドされるリストを表示します
    - キャンセルしたリマインドリスト
      - キャンセルされたリマインドリストを表示します
    - スキップしたリマインドリスト([v1.0.2](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.2)で追加)
      - スキップされたリマインドリストを表示します
    - 終了したリマインドリスト
      - リマインドしたリストを表示します
    - エラーになったリマインドリスト
      - エラーになってしまったリストを表示します
  - filter
    - リマインドリストを検索
      - 検索対象は以下
        - No
        - 日付
        - メッセージ
        - 繰り返し設定
        - ギルドID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - メンバーID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - チャンネルID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
    - [v1.0.0](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.0)で追加
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-id-user-guild-delete`

- ギルド内のみ、かつ、ギルドの管理者権限保持者のみ使用可能
- 指定したNoのリマインド登録者をギルドからBANします
  - 現在登録されているリマインドをすべて削除した上、今後ギルド内でリマインドできなくさせます
- 必須のオプション(1つ)
  - delete_no(BANするリマインドのNo)
    - 数字
    - BANする対象は登録者ですが、登録者を探すのは面倒なのでリマインドのNoを使います
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-id-user-guild-recovery`

- ギルド内のみ、かつ、ギルドの管理者権限保持者のみ使用可能
- 指定したNoのリマインド登録者のBANを解除します
  - ただし、BANされたときに削除されたリマインドはそのままの状態となります
- 必須のオプション(1つ)
  - recovery_no(BAN解除するリマインドのNo)
    - 数字
    - BAN解除されるのは登録者ですが、登録者を探すのは面倒なのでリマインドのNoを使います
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/delete-guild-remind`

- ギルドのリマインドをすべて削除します([v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)で追加)
- ギルド内のみ、かつ、ギルドの管理者権限保持者のみ使用可能
- オプション
  - confirm(削除確認)
    - 削除するを選択したときのみ、削除します。
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

## Botオーナー向けの機能

- ここでいう"Botオーナー"とは、discord-reminderbotのトークンを生成した人のことです
  - ギルド(Disocrdサーバー)の管理者とは違います

### `/remind-list-all`

- BotとのDMのみ、かつ、Botのオーナー(DiscordのBotのトークンを生成した人)のみ使用可能
- Botに登録されているリマインドをすべて表示します
  - [v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5)で日付の表示形式を変更
- オプション
  - status
    - 実行予定のリマインドリスト(デフォルトと同じ)
      - 今後リマインドされるリストを表示します
    - キャンセルしたリマインドリスト
      - キャンセルされたリマインドリストを表示します
    - スキップしたリマインドリスト([v1.0.2](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.2)で追加)
      - スキップされたリマインドリストを表示します
    - 終了したリマインドリスト
      - リマインドしたリストを表示します
    - エラーになったリマインドリスト
      - エラーになってしまったリストを表示します
  - filter
    - リマインドリストを検索
      - 検索対象は以下
        - No
        - 日付
        - メッセージ
        - 繰り返し設定
        - ギルドID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - メンバーID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
        - チャンネルID([v1.0.3](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.3)で追加)
    - [v1.0.0](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.0)で追加
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/delete-old-remind`

- Botのオーナー(DiscordのBotのトークンを生成した人)のみ使用可能
- 指定されたステータスのリマインドをすべて削除(添付ファイルの容量が厳しいため)
  - ([v1.0.7](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.7))でステータスに変更(元々は「完了」のみだった)
- もともと`/delete-old-data`だったが、`/delete-old-remind`へ修正([v1.0.5](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.5))

### `/remind-id-user-delete`

- Botのオーナー(DiscordのBotのトークンを生成した人)のみ使用可能
- 指定したNoのリマインド登録者をBANします
  - 現在登録されているリマインドをすべて削除した上、今後リマインドできなくさせます
- 必須のオプション(1つ)
  - delete_no(BANするリマインドのNo)
    - 数字
    - BANする対象は登録者ですが、登録者を探すのは面倒なのでリマインドのNoを使います
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### `/remind-id-user-recovery`

- Botのオーナー(DiscordのBotのトークンを生成した人)のみ使用可能
- 指定したNoのリマインド登録者のBANを解除します
  - ただし、BANされたときに削除されたリマインドはそのままの状態となります
- 必須のオプション(1つ)
  - recovery_no(BAN解除するリマインドのNo)
    - 数字
    - BAN解除されるのは登録者ですが、登録者を探すのは面倒なのでリマインドのNoを使います
- オプション
  - reply_is_hidden
    - 自分のみ
      - 実行結果は自分だけ見ることができます
    - 全員に見せる
      - 実行結果はBotからのリプライとして表示されます

### その他のコマンドは検討中です(リマインドの削除など実装予定)

## 環境変数

### DISCORD_TOKEN

- あなたのDiscordのトークンを記載（トークンは厳重に管理し、公開されないよう配慮すること！）
- 例: DISCORD_TOKEN="fdj2iur928u42q4u239858290"

### LOG_LEVEL

- ログレベル(DEBUG/INFO/WARNING/ERROR)
- 例: LOG_LEVEL="INFO"

### KEEP_DECRYPTED_FILE

- 復号されたファイルを残すかどうか(TRUEの時のみ残す。デフォルトでは復号されたファイルは削除される)
- 例: KEEP_DECRYPTED_FILE=FALSE

### IS_HEROKU

- Herokuで動かすかどうか
  - Herokuの場合、ファイルが削除されるので、discordの添付ファイルを使って保管を試みる(ファイルが削除されていたら、読み込む)
- 例: IS_HEROKU=FALSE

### RESTRICT_ATTACHMENT_FILE

- Bot自身が添付したファイルのみ読み込むように制限するかどうか
  - Bot以外(他のBotや人間)が添付したファイルのみを読み込むようになります
- 例: RESTRICT_ATTACHMENT_FILE=TRUE

### PRIORITY_GUILD

- 優先してファイルを添付するギルド(1件のみ指定してください)
  - 権限の問題で、Botがファイル保管に失敗することがあるため、失敗時に添付するギルドを指定できる
- 例: PRIORITY_GUILD=99999999999

### REMIND_CONTROL_CHANNEL_NAME

- リマインダーのデータを保存するチャンネル名を指定できます(未指定の場合remind_control_channel)
  - 他のギルドもその名前のチャンネルが保存先に使われるので気をつけてください
  - テスト中に複数のリマインダーBot動かしてて困ったので作成した環境変数です(基本開発に使うもの)
- 例: REMIND_CONTROL_CHANNEL_NAME=リマインドチャンネル

### APPLICATION_ID

- あなたのBotの`APPLICATION ID`を指定する(スラッシュコマンドを使う上で設定が必須となります)。[v1.0.0](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.0)で追加
  - [開発者ポータル](https://discord.com/developers/applications/)の該当Botの`General Information`の上部にある、`APPLICATION ID`

### ENABLE_SLASH_COMMAND_GUILD_ID

- あなたのBotのテストする際はテスト用のギルドですぐに使用したいものと思われます(グローバルコマンドは適用まで時間がかかってしまう)
- その場合、この環境変数にテスト用ギルドのIDを設定することで、すぐにスラッシュコマンドが試せます(ギルドコマンドとして設定する)。[v1.0.0](https://github.com/tetsuya-ki/discord-reminderbot/releases/tag/v1.0.0)で追加
  - 設定が**複数存在する場合、「;」を挟む必要**がある
    - 1件の場合: ENABLE_SLASH_COMMAND_GUILD_ID=18471289371923
    - 2件の場合: ENABLE_SLASH_COMMAND_GUILD_ID=18471289371923;1389103890128390

### 廃止された環境変数

- `ENABLE_SLASH_COMMAND_GUILD_ID_LIST`: ENABLE_SLASH_COMMAND_GUILD_IDに置き換えられました

## 動かし方

- wikiに書くつもりです(時期未定)
- わからないことがあれば[Discussions](https://github.com/tetsuya-ki/discord-reminderbot/discussions)に書いてみてください

### 普通に動かす場合

#### 前提

- poetryがインストールされていること
- `.env.sample`をコピーし、`.env`が作成されていること(それぞれの環境変数の意味は[環境変数](#環境変数)を参照ください)

#### 動かす

- 以下のコマンドを実行

```sh
poetry run python discord-reminderbot.py
```

### docker-composeを用いた起動手順

#### 前提(docker-compose)

- `docker`,`docker-compose`コマンドが利用できること

#### 環境変数の設定

- `.env`の準備の代わりに、`docker-compose.override.yml`を作成して環境変数を記載

```docker
version: "3"

services:
  app:
    environment:
      - DISCORD_TOKEN=__あなたのDicordトークン__
      - LOG_LEVEL=INFO
      - ENABLE_SLASH_COMMAND_GUILD_ID= __あなたのGuild_IDを入力(数字/複数あるなら;を挟むこと。グローバルコマンドの場合は入力しないこと！(その場合1時間程度登録に時間がかかる可能性があります))__
      - KEEP_DECRYPTED_FILE=FALSE
      - IS_HEROKU=FALSE
      - RESTRICT_ATTACHMENT_FILE=FALSE
      - PRIORITY_GUILD=__あなたのGuild_IDを入力(数字)__
      - REMIND_CONTROL_CHANNEL_NAME=remind_control_channel
      - APPLICATION_ID=__あなたのBotのAPPLICATION_IDを入力(数字)__
```

#### 起動・停止操作

- Dockerイメージのビルド
`docker-compose build`

- 起動
`docker-compose up -d`

- 停止
`docker-compose down`

- ログ出力
`docker-compose logs -f`
