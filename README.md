Backlog の GIT が AWS の Codepipeline と直接連携出来ないので Webhook ApiGateway Lambda S3 を使用する事で連携出来るようにする為のリポジトリです。

このリポジトリでは下記 2 点の設定を設定と手順について記載します。

1. Serverless Framework で ApiGateway Lambda のデプロイ
2. Backlog の Webhook の設定

## 参考

- [AWS CodePipeline が対応していない git リポからの CI/CD 構築](https://qiita.com/hideBBBtec/items/fca41214faf7663f2a54)
- [serverless (公式の whitelist 形式)](https://www.serverless.com/framework/docs/providers/aws/events/apigateway#resource-policy)
- [Webhook 送信サーバーの IP アドレスを教えてください](https://support-ja.backlog.com/hc/ja/articles/360035645534-Webhook-%E9%80%81%E4%BF%A1%E3%82%B5%E3%83%BC%E3%83%90%E3%83%BC%E3%81%AE-IP-%E3%82%A2%E3%83%89%E3%83%AC%E3%82%B9%E3%82%92%E6%95%99%E3%81%88%E3%81%A6%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84)

## 流れ

1. Backlog の GIT にプッシュする。
2. Backlog の Webhook が ApiGateway にリクエストを送る。
3. ApiGateway が Lambda を実行する。
4. Lambda が git clone を実行し S3 にコードを配置する。

## 前提

1. awscli が設定済み。
2. S3 バケットが作成済み。
3. KMS でマスターキーを作成済み。
4. serverless をインストール済み。

## 階層

serverless で作成したプロジェクト直下は下記のとおりです。

```bash
.
├── README.md
├── add_encrypt_password.py
├── handler.py
└── serverless.yml
```

## 設定手順

1. シークレットファイルを作成する
2. 暗号化したパスワードを追加する
3. デプロイする
4. レイヤーを追加する
5. Backlog の Webhook を設定する

## シークレットファイルを作成する

ファイル .secrets.yml をプロジェクト直下に作り下記の通り設定します。  
このファイルの値を使用して暗号化と環境変数を設定します。

```yml
arn: arn:aws:kms:ap-northeast-1:xxxxxxxxxxxx:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
bucket_name: bucket_name
plain_password: password
repository_url: https://subdomain.backlog.com/git/PROJECT/
repository-name.git
target_branches: '["master","develop"]'
user_name: firstname.lastname@example.com
```

- arn: KMS の ARN の値を設定する。
- bucket_name: コードを配置したい S3 のバケット名を設定する。
- plain_password: GIT のパスワードを設定する。
- repository_url: GIT のリポジトリの URL を設定する。
- target_branches: プッシュされた時に S3 に入れたいブランチ名を設定する。
- user_name: GIT のユーザー名を設定する。

## 暗号化したパスワードを追加する

ファイル add_encrypt_password.py を実行します。  
ファイル .secrets.yml に password 属性で GIT のパスワードを暗号化した値を追加します。

```bash
python add_encrypt_password.py
```

## ローカル環境で実行する

ローカル環境にて実行するのコマンドは下記の通りです。

```bash
sls invoke local --function main --data '{"body": {"content": {"ref": "refs/heads/master"}}}'
```

オプション「--data」の引数でリクエストの body を擬似的に取得しています。  
テストなので最低限必要な JSON のみで master ブランチがプッシュされたとして記載しています。

## デプロイする

Lambda にデプロイするコマンドは下記の通りです。

```bash
sls deploy
```

## レイヤーを追加する

Lambda で git コマンドが使えるようにレイヤーを追加します。

1. [このページ](https://github.com/lambci/git-lambda-layer)の「Version ARNs for Amazon Linux 2 runtimes」の「ARN」をコピーする。
2. Lambda のページを開く。
3. 対象の関数をクリックする。
4. 「関数概要」の図の中の「Layers (0)」をクリックする。
5. 項目「レイヤー」の「レイヤーの追加」をクリックする。
6. 「RAN を指定」をクリックする。
7. 手順 1 でコピーした値をテキストボックスにペーストする。
8. ペーストした値のリージョンを該当するリージョンに書き換える。
9. 「追加」をクリックする。

※ 手順 8 の値の例。

```console
arn:aws:lambda:ap-northeast-1:553035198032:layer:git-lambda2:8
```

## Backlog の Webhook を設定する

1. 左サイドバーの「プロジェクトの設定」をクリックする。
2. 「インテグレーション」をクリックする。
3. 「Webhook」の「設定」をクリックする。
4. 「設定」タブの「Webhook を追加する」をクリックする。
5. 下記の設定をする。
   - Webhook 名: put_source_into_s3
   - 説明: ApiGateway -> lambda -> s3 と言う流れでソースコードを s3 に保存する。
   - WebHook URL: [ApiGateway のエンドポイント]
   - 「通知するイベント」の「Git プッシュ」にチェックを付ける。
   - 「保存」をクリックする。
