import base64
import datetime
import json
import os
import shutil
import subprocess
import traceback
import urllib
import urllib.request

import boto3

REPOSITORY_URL = os.environ.get("REPOSITORY_URL", None)
USER_NAME = os.environ.get("USER_NAME", None).replace("@", "%40")
PASSWORD = os.environ.get("PASSWORD", None)
BUCKET_NAME = os.environ.get("BUCKET_NAME", None)
TARGET_BRANCHES = os.environ.get("TARGET_BRANCHES", [])

class PutSourceIntoS3:
    """
    ソースコードをZIPしてS3に配置する。
    Backlog の Webhook によるトリガーを想定。

    インスタンス変数は、レスポンスで見れるようにしているので、
    複合したパスワードやGITへのリクエストのURLは、設定しないでおく。
    """
    backlog_params = None  # Backlog から受け取ったパラメータ
    branch_name = None  # ブランチ名
    repository_name = None  # リポジトリ名
    request_url = None  # クローン生成のリクエストURL
    root = None  # ルートのパス
    source_path = None  # クローンしたソースコードのパス
    tmpdir = None  # 作業ディレクトリ

    def __init__(self, backlog_params):
        """
        初期値として Backlog のパラメータと root のパスを設定する。
        """
        self.backlog_params = backlog_params
        self.root = os.path.abspath(os.path.join(__file__, ".."))

    def get_decrypted_password(self):
        """
        パスワードを複合する。
        """
        kms = boto3.client('kms')
        return kms.decrypt(
            CiphertextBlob=base64.b64decode(PASSWORD)
        )['Plaintext'].decode('utf-8')

    def get_request_url(self):
        """
        リポジトリのURLから clone 生成のためのユーザー名とパスワード名を追加したリポジトリのURLを生成し設定する。
        """
        parsed_url = urllib.parse.urlparse(REPOSITORY_URL)
        return (
            parsed_url.scheme
            + "://"
            + USER_NAME
            + ":"
            + self.get_decrypted_password()
            + "@"
            + parsed_url.netloc
            + parsed_url.path
        )

    def set_working_dir(self):
        """
        作業ディレクトリ ./tmp/yyyymmddssss/ を生成し設定する。
        """
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.tmpdir = "/tmp/" + now
        os.makedirs(self.tmpdir)

    def set_branch_name(self):
        """
        Backlog のリクエストからブランチ名を取得し設定する。
        """
        self.branch_name = self.backlog_params["body"]["content"]["ref"].split("/")[-1]

    def set_repository_name(self):
        """
        リポジトリのURLからリポジトリ名を取得し設定する。
        """
        parsed_url = urllib.parse.urlparse(REPOSITORY_URL)
        repository_name_with_extension = parsed_url.path.split("/")[-1]
        self.repository_name = repository_name_with_extension.split(".")[0]

    def set_source_path(self):
        """
        zip するファイルのパスを取得する。
        """
        self.source_path = self.tmpdir + "/" + self.repository_name

    def git_clone(self):
        """
        コマンド git clone を実行し tmpdir 配下にファイルを設置する。
        """
        os.chdir(self.tmpdir)
        subprocess.call(
            [
                "git",
                "clone",
                "--branch",
                self.branch_name,
                self.get_request_url(),
            ]
        )

    def zip_files(self):
        """
        source_path に指定されたソースを zip にまとめる。
        """
        shutil.make_archive(self.source_path, "zip", self.source_path)

    def upload_to_s3(self):
        """
        zip したファイルを s3 にアップロードする。
        """
        s3 = boto3.resource("s3")
        bucket = s3.Bucket(BUCKET_NAME)
        try:
            bucket.upload_file(
                f"{self.source_path}.zip",
                f"{self.repository_name}.zip"
            )
        except Exception:
            raise Exception

def main(event, context):
    """
    serverless.yml から呼び出されるメインメソッド。
    """
    try:
        psis = PutSourceIntoS3(event)

        # Ready
        psis.set_working_dir()
        psis.set_branch_name()
        psis.set_repository_name()
        psis.set_source_path()

        if psis.branch_name in json.loads(TARGET_BRANCHES):
            message = f"Put '{psis.branch_name}' of source into S3."
            # Execute
            psis.git_clone()
            psis.zip_files()
            psis.upload_to_s3()
        else:
            message = f"'{psis.branch_name}' of branch is not target."

        return {
            "statusCode": 200,
            "params": vars(psis),
            "message": message,
        }
    except Exception:
        traceback.print_exc()
        return {
            "statusCode": 400,
            "params": vars(psis),
            "error": traceback.format_exc(),
        }
    finally:
        del psis