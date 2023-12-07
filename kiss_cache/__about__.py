# -*- coding: utf-8 -*-
# vim: set ts=4
#
# Copyright 2019 Linaro Limited
#
# Author: Rémi Duraffort <remi.duraffort@linaro.org>
#
# SPDX-License-Identifier: MIT

__all__ = [
    "__author__",
    "__author_email__",
    "__description__",
    "__license__",
    "__url__",
    "__version__",
]


def git_describe():
    import subprocess  # pylint: disable=import-outside-toplevel

    try:
        # git describe?
        out = subprocess.check_output(["git", "describe"], stderr=subprocess.STDOUT)
        version = out.decode("utf-8").rstrip("\n")
        return version
    except Exception:
        return "git"


__author__ = "Rémi Duraffort"
__author_email__ = "remi.duraffort@linaro.org"
__description__ = "A simple and stupid cache service"
__license__ = "MIT"
__url__ = "https://gitlab.com/linaro/KissCache"
__version__ = git_describe()
