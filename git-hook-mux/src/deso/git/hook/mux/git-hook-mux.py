#!/usr/bin/env python

#/***************************************************************************
# *   Copyright (C) 2015-2016 Daniel Mueller (deso@posteo.net)              *
# *                                                                         *
# *   This program is free software: you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation, either version 3 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program.  If not, see <http://www.gnu.org/licenses/>. *
# ***************************************************************************/

"""This script can be used to enable multiple hooks for git(1)."""

from argparse import (
  ArgumentParser,
)
from deso.execute import (
  execute,
  findCommand,
  ProcessError,
)
from os.path import (
  basename,
)
from shlex import (
  split as shsplit,
)
from sys import (
  argv as sysargv,
  stdout,
  stderr,
)


GIT = findCommand("git")
GIT_HOOK_SECTION = "hook-mux"


def retrieveHookList(section, hook_type):
  """Retrieve the list of configured hooks for the given hook type."""
  name = "%s.%s" % (section, hook_type)
  try:
    out, _ = execute(GIT, "config", "--get-all", name, stdout=b"", stderr=None)
    value = out.decode("utf-8")
    # Split each line reported by git-config into a separate string.
    # Remove all whitespace only strings.
    return list(filter(lambda x: x.strip() != "", value.splitlines()))
  except ProcessError:
    return []


def isVerbose(section):
  """Check if the script should be verbose."""
  name = "%s.%s" % (section, "verbose")
  try:
    out, _ = execute(GIT, "config", "--bool", "--get", name, stdout=b"", stderr=None)
    return out[:-1] == b"true"
  except ProcessError:
    return False


def setupArgumentParser():
  """Create and initialize an argument parser, ready for use."""
  parser = ArgumentParser(prog="git-hook-mux")
  parser.add_argument(
    "-s", "--section", action="store", default=GIT_HOOK_SECTION,
    dest="section",
    help="The name of the git-config(1) section to use (defaults to "
         "'%s')." % GIT_HOOK_SECTION,
  )
  parser.add_argument(
    "-t", "--hook-type", action="store", default=None, dest="hook_type",
    help="The type of hook to invoke (e.g., 'pre-commit').",
  )
  return parser


def main(argv):
  """Check the type of hook we got invoked for and invoke the configured user-defined ones."""
  parser = setupArgumentParser()
  namespace = parser.parse_args(argv[1:])
  section = namespace.section
  verbose = isVerbose(section)

  # We support two use cases: the hook multiplexer can be copied (or
  # symlinked) to a git hook in which case the hook type to use is
  # inferred from the script/symlink name. The script can also be
  # invoked with the hook type as argument which would override the file
  # name based hook type determination.
  if namespace.hook_type is not None:
    hook_type = namespace.hook_type
  else:
    hook_type = basename(argv[0])

  hooks = retrieveHookList(section, hook_type)

  if verbose:
    print("Section: %s" % section)
    print("Hook type: %s" % hook_type)
    print("Hooks registered:\n%s" % "\n".join(hooks))

  try:
    for hook in hooks:
      execute(*shsplit(hook), stdout=stdout.fileno(), stderr=stderr.fileno())
  except ProcessError as e:
    # Note that since we redirected stderr directly we will not have the
    # output here. However, we will still get the command run and the
    # exit status.
    print("%s" % e, file=stderr)
    return e.status

  return 0


if __name__ == "__main__":
  exit(main(sysargv))
