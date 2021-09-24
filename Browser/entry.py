# Copyright 2020-     Robot Framework Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from subprocess import DEVNULL, PIPE, STDOUT, CalledProcessError, Popen

INSTALLATION_DIR = Path(__file__).parent / "wrapper"
# This is required because weirdly windows doesn't have `npm` in PATH without shell=True.
# But shell=True breaks our linux CI
SHELL = True if platform.platform().startswith("Windows") else False


def rfbrowser_init(skip_browser_install: bool):
    print("Installing node dependencies...")
    if not (INSTALLATION_DIR / "package.json").is_file():
        print(
            f"Installation directory `{INSTALLATION_DIR}` does not contain the required package.json "
            + "\nPrinting contents:"
        )
        for root, _dirs, files in os.walk(INSTALLATION_DIR):
            level = root.replace(INSTALLATION_DIR.__str__(), "").count(os.sep)
            indent = " " * 4 * (level)
            print("{}{}/".format(indent, os.path.basename(root)))
            subindent = " " * 4 * (level + 1)
            for f in files:
                print("{}{}".format(subindent, f))
        raise RuntimeError("Could not find robotframework-browser's package.json")
    if not os.access(INSTALLATION_DIR, os.W_OK):
        sys.tracebacklimit = 0
        raise RuntimeError(
            f"`rfbrowser init` needs write permissions to {INSTALLATION_DIR}"
        )

    print(f"Installing rfbrowser node dependencies at {INSTALLATION_DIR}")

    try:
        subprocess.run(["npm", "-v"], stdout=DEVNULL, check=True, shell=SHELL)
    except (CalledProcessError, FileNotFoundError, PermissionError) as exception:
        print(
            "Couldn't execute npm. Please ensure you have node.js and npm installed and in PATH."
            "See https://nodejs.org/ for documentation"
        )
        sys.exit(exception)

    if skip_browser_install:
        os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"
    else:
        if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

    process = Popen(
        "npm install --production",
        shell=True,
        cwd=INSTALLATION_DIR,
        stdout=PIPE,
        stderr=STDOUT,
    )

    while process.poll() is None:
        if process.stdout:
            output = process.stdout.readline()
            print(output.decode("utf-8"))

    if process.returncode != 0:
        raise RuntimeError(
            "Problem installing node dependencies."
            + f"Node process returned with exit status {process.returncode}"
        )

    print("rfbrowser init completed")


def rfbrowser_clean_node():
    if not INSTALLATION_DIR.is_dir():
        print(f"Could not find {INSTALLATION_DIR}, nothing to delete.")
        return
    print("Delete library node dependencies...")
    shutil.rmtree(INSTALLATION_DIR)


def show_trace(file: str):
    print(f"Opening file: {file}")
    playwright = INSTALLATION_DIR / "node_modules" / "playwright"
    local_browsers = playwright / ".local-browsers"
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(local_browsers)
    trace_arguments = [
        "npx",
        "playwright",
        "show-trace",
        file,
    ]
    subprocess.run(trace_arguments, env=env, shell=SHELL)


# Based on: https://stackoverflow.com/questions/3853722/how-to-insert-newlines-on-argparse-help-text
class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("Possible commands are:"):
            parts = []
            for part in text.splitlines():
                part = argparse.HelpFormatter._split_lines(self, part, width)
                parts.extend(part if part else "\n")
            return parts
        return argparse.HelpFormatter._split_lines(self, text, width)


def run():
    parser = argparse.ArgumentParser(
        description="Robot Framework Browser library command line tool.",
        formatter_class=SmartFormatter,
    )
    parser.add_argument(
        "command",
        help=(
            "Possible commands are:\ninit\nclean-node\nshow-trace\n\ninit command will install the required node "
            "dependencies. init command is needed when library is installed or updated.\n\nclean-node is used to delete"
            "node side dependencies and installed browser binaries from the library default installation location. "
            "When upgrading browser library, it is recommended to clean old node side binaries after upgrading the "
            "Python side. Example:\n1) pip install -U robotframework-browser\n2) rfbrowser clean-node\n3)rfbrowser "
            "init.\nRun rfbrowser clean-node command also before uninstalling the library with pip. This makes sure "
            "that playwright browser binaries are not left in the disk after the pip uninstall command."
            "\n\nshow-trace command will start the Playwright trace viewer tool.\n\nSee the each command argument "
            "group for more details what (optional) arguments that command supports."
        ),
    )
    install = parser.add_argument_group("init options")
    install.add_argument(
        "--skip-browsers",
        help="If defined skips the Playwright browser installation. Argument is optional",
        default=False,
        action="store_true",
    )
    trace = parser.add_argument_group("show-trace options")
    trace.add_argument(
        "--file",
        "-F",
        help=(
            "Full path to trace zip file. See New Context keyword for more details how to "
            "create trace file. Argument is mandatory."
        ),
        default=False,
    )
    args = parser.parse_args()
    command = args.command.lower()
    if command == "init":
        rfbrowser_init(args.skip_browsers)
    if command == "clean-node":
        rfbrowser_clean_node()
    elif command == "show-trace":
        if not args.file:
            raise Exception("show-trace needs also --file argument")
        show_trace(args.file)
    else:
        raise Exception(
            f"Command should be init or show-trace, but it was {args.command}"
        )


if __name__ == "__main__":
    run()
