# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2019 Rémi Duraffort
# This file is part of KissCache.
#
# KissCache is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KissCache is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with KissCache.  If not, see <http://www.gnu.org/licenses/>

__all__ = [
    "__author__",
    "__author_email__",
    "__description__",
    "__license__",
    "__url__",
    "__version__",
]


def git_describe():
    import subprocess

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
__license__ = "AGPLv3+"
__url__ = "https://git.lavasoftware.org/ivoire/KissCache"
__version__ = git_describe()