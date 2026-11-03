"""Configuration loading.

Values come from the environment with sane defaults for local runs. The
defaults are deliberately developer-friendly; production overrides them through
the compose file's environment block.
"""
import os


def load_config():
    cfg = {
        "DATABASE": os.environ.get("SHOP_DB", "/data/shop.db"),
        # Signing key for the stateless session cookie. Operators are expected
        # to override this; the baked-in value keeps local dev working.
        "SECRET_KEY": os.environ.get("SHOP_SECRET", "s3cr3t-shop-key-change-me"),
        # Hosts the media previewer is allowed to reach. Comma separated.
        "MEDIA_ALLOW": os.environ.get("MEDIA_ALLOW", "cdn.shop.local,images.shop.local"),
        # Where generated reports are written before download.
        "EXPORT_DIR": os.environ.get("EXPORT_DIR", "/tmp/shop-exports"),
        "DEBUG": os.environ.get("SHOP_DEBUG", "0") == "1",
    }
    return cfg
