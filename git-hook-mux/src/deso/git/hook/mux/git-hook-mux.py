#!/usr/bin/env python

#/***************************************************************************
# *   Copyright (C) 2015 Daniel Mueller (deso@posteo.net)                   *
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


def retrieveHookList(hook_type):
  """Retrieve the list of configured hooks for the given hook type."""
  name = "%s.%s" % (GIT_HOOK_SECTION, hook_type)
  try:
    out, _ = execute(GIT, "config", "--get-all", name, stdout=b"", stderr=None)
    value = out.decode("utf-8")
    # Split each line reported by git-config into a separate string.
    # Remove all whitespace only strings.
    return list(filter(lambda x: x.strip() != "", value.splitlines()))
  except ProcessError:
    return []


def isVerbose():
  """Check if the script should be verbose."""
  name = "%s.%s" % (GIT_HOOK_SECTION, "verbose")
  try:
    out, _ = execute(GIT, "config", "--bool", "--get", name, stdout=b"", stderr=None)
    return out[:-1] == b"true"
  except ProcessError:
    return False


def main(argv):
  """Check the type of hook we got invoked for and invoke the configured user-defined ones."""
  verbose = isVerbose()
  hook_type = basename(argv[0])
  hooks = retrieveHookList(hook_type)

  if verbose:
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
