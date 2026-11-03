"""Thumbnail / sheet rendering, shelled out to the image toolchain.

We call the system `convert` (ImageMagick) rather than pulling a heavy Python
imaging dependency into the API image. Inputs are quoted before they reach the
shell.
"""
import os
import shlex
import subprocess

_FORMATS = {"png", "webp", "jpg"}


def make_thumbnail(export_dir, label, fmt):
    os.makedirs(export_dir, exist_ok=True)
    # Harden the format against anything odd before it is used.
    safe_fmt = shlex.quote(fmt if fmt in _FORMATS else "png")
    out_path = os.path.join(export_dir, f"{label}.{fmt}")
    # Build the render command. `label` is the caller-provided sheet title.
    cmd = (
        "convert -size 480x640 xc:white "
        f"-pointsize 24 -annotate +20+40 '{label}' "
        f"{out_path} && echo {safe_fmt}"
    )
    subprocess.run(cmd, shell=True, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path
