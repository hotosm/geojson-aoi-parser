#!/usr/bin/env python
# Copyright (c) Humanitarian OpenStreetMap Team
# This file is part of geojson-aoi-parser.
#
#     geojson-aoi-parser is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     geojson-aoi-parser is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with geojson-aoi-parser.  If not, see <https:#www.gnu.org/licenses/>.
#
# This script is adapted from the work done by
# Emir Fabio Cognigni (https://github.com/emirfabio),
# Sam Woodcock (https://github.com/spwoodcock), and
# Stephen Garland (https://github.com/stephanGarland)
# for the HOT pg-nearest-city module (https://github.com/hotosm/pg-nearest-city).

"""Convert async modules to sync equivalents using tokenisation."""

import os
import re
import sys
from pprint import pprint

SUBS = [
    # General
    ("AsyncIterator", "Iterator"),
    ("Async([A-Z][A-Za-z0-9_]*)", r"\2"),
    ("async def", "def"),
    ("async with", "with"),
    ("async for", "for"),
    ("await ", ""),
    ("aclose", "close"),
    ("aiter_stream", "iter_stream"),
    ("aread", "read"),
    ("asynccontextmanager", "contextmanager"),
    ("__aenter__", "__enter__"),
    ("__aexit__", "__exit__"),
    ("__aiter__", "__iter__"),
    ("asynchronous", "synchronous"),
    ("_async", "_sync"),
    # Package specific
    ("AsyncPostGis", "PostGis"),
    ("AsyncConnection", "Connection"),
    ("AsyncCursor", "Cursor"),
    ("parse_aoi_async", "parse_aoi"),
    # Testing
    ("pytest_asyncio.fixture", "pytest.fixture"),
    ("import pytest_asyncio", ""),
    ("pytest_asyncio", "pytest"),
    ("@pytest.mark.anyio", ""),
    ("@pytest.mark.asyncio", ""),
]
COMPILED_SUBS = [
    (re.compile(r"(^|\b)" + regex + r"($|\b)"), repl) for regex, repl in SUBS
]

USED_SUBS = set()


def unasync_line(line):
    """Remove async tokens on given line."""
    for index, (regex, repl) in enumerate(COMPILED_SUBS):
        old_line = line
        line = re.sub(regex, repl, line)
        if old_line != line:
            USED_SUBS.add(index)
    return line


def unasync_file(in_path, out_path):
    """Remove async tokens in given file."""
    with open(in_path, "r") as in_file, open(out_path, "w", newline="") as out_file:
        for line in in_file.readlines():
            line = unasync_line(line)
            out_file.write(line)


def unasync_file_check(in_path, out_path):
    """Check if async tokens need to be removed."""
    with open(in_path, "r") as in_file, open(out_path, "r") as out_file:
        for in_line, out_line in zip(
            in_file.readlines(), out_file.readlines(), strict=False
        ):
            expected = unasync_line(in_line)
            if out_line != expected:
                print(f"unasync mismatch between {in_path!r} and {out_path!r}")
                print(f"Async code:         {in_line!r}")
                print(f"Expected sync code: {expected!r}")
                print(f"Actual sync code:   {out_line!r}")
                sys.exit(1)


def unasync_dir(in_dir, out_dir, check_only=False):
    """Remove async tokens for all Python files in dir."""
    for dirpath, _dirnames, filenames in os.walk(in_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            rel_dir = os.path.relpath(dirpath, in_dir)
            in_path = os.path.normpath(os.path.join(in_dir, rel_dir, filename))
            out_path = os.path.normpath(os.path.join(out_dir, rel_dir, filename))
            print(in_path, "->", out_path)
            if check_only:
                unasync_file_check(in_path, out_path)
            else:
                unasync_file(in_path, out_path)


def main():
    """Run the async --> sync converter."""
    check_only = "--check" in sys.argv

    if not check_only:
        print("**Files to unasync:**")
    unasync_dir("geojson_aoi/_async", "geojson_aoi/_sync", check_only=check_only)
    unasync_dir("tests/_async", "tests/_sync", check_only=check_only)

    if len(USED_SUBS) != len(SUBS):
        unused_subs = [SUBS[i] for i in range(len(SUBS)) if i not in USED_SUBS]

        print("")
        print("These patterns were not used:")
        pprint(unused_subs)
        # Allow pre-commit to pass
        sys.exit(0)


if __name__ == "__main__":
    main()
