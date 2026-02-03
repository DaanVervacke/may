import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()


APP_VERSION = '0.5.0'
RELEASE_CHANNEL = os.environ.get('RELEASE_CHANNEL', 'stable')
GITHUB_REPO = 'dannymcc/may'


class Config:
    APP_VERSION = APP_VERSION
    RELEASE_CHANNEL = RELEASE_CHANNEL
    GITHUB_REPO = GITHUB_REPO
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        import secrets
        # Generate a random key for development, but warn about it
        SECRET_KEY = secrets.token_hex(32)
        import warnings
        warnings.warn(
            "SECRET_KEY environment variable not set. Using randomly generated key. "
            "Sessions will not persist across restarts. Set SECRET_KEY for production.",
            RuntimeWarning
        )
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{basedir}/data/may.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(basedir / 'data' / 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
