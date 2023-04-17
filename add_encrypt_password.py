import base64
import boto3
import yaml

kms = boto3.client("kms")


class Encrypt:
    """
    secrets.yml の plain_password を暗号化し、password 属性として追加する。
    """
    secrets = {}
    arn = None
    plain_password = None
    encrypted_password = None
    decoded_password = None

    def __init__(self):
        """
        secrets.yml を読み込み arn と plain_password を設定する。
        """
        with open("./.secrets.yml", "r") as yml:
            self.secrets = yaml.safe_load(yml)
            self.arn = self.secrets.get("arn", None)
            self.plain_password = self.secrets.get("plain_password", None)

    def create_encrypted_password(self):
        """
        パスワードを暗号化する。
        """
        response = kms.encrypt(KeyId=self.arn, Plaintext=self.plain_password)
        self.encrypted_password = response["CiphertextBlob"]

    def create_decoded_password(self):
        """
        (暗号化された)パスワードをデコードする。
        """
        self.decoded_password = base64.b64encode(self.encrypted_password).decode(
            "utf-8"
        )

    def write_encrypted_password(self):
        """
        (暗号化された)パスワードを password 属性として追加する。
        """
        self.secrets["password"] = self.decoded_password
        with open("./.secrets.yml", "w") as f:
            yaml.dump(self.secrets, f)


encrypt = Encrypt()
encrypt.create_encrypted_password()
encrypt.create_decoded_password()
encrypt.write_encrypted_password()