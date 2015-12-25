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

"""Various tests for the git hook multiplexer."""

from deso.cleanup import (
  defer,
)
from deso.execute import (
  findCommand,
  ProcessError,
)
from deso.git.repo import (
  Repository,
  write,
)
from os import (
  chmod,
  symlink,
  unlink,
)
from os.path import (
  dirname,
  join,
)
from shutil import (
  copyfile,
)
from sys import (
  executable,
)
from tempfile import (
  NamedTemporaryFile,
)
from unittest import (
  main,
  TestCase,
)


GIT = findCommand("git")


class GitRepository(Repository):
  """A git repository with subrepo support."""
  def __init__(self):
    """Initialize the git repository."""
    super().__init__(GIT)


  def _init(self):
    """Initialize the repository and install the copyright hook."""
    super()._init()
    # We need to install our hook multiplexer script to get into effect
    # for the repository we just created.
    # TODO: Using a relative path based on this file might break once we
    #       install things properly, in which case the hook mux script
    #       could reside somewhere else.
    src = join(dirname(__file__), "..", "git-hook-mux.py")
    # For now we are just interested in it working in conjunction with
    # the pre-commit hook.
    dst = self.path(".git", "hooks", "git-hook-mux.py")
    copyfile(src, dst)
    # The hook script is required to be executable.
    chmod(dst, 0o755)

    # We are pretty sure things work when copying the file. We want to
    # verify that symlinking works as well.
    src = dst
    dst = self.path(".git", "hooks", "pre-commit")
    symlink(src, dst)


  def configAdd(self, *args):
    """Invoke a git-config command."""
    self.git("config", "--local", "--add", *args)


class TestGitHookMux(TestCase):
  """Tests for the git-subrepo script."""
  def testPreCommitHookInvocation(self):
    """Verify that pre-commit hooks are invoked correctly."""
    def doTest(hooks=None):
      """Configure pre-commit hooks in a repository and create a commit."""
      with GitRepository() as repo:
        write(repo, "test.dat", data="test")
        repo.add("test.dat")

        if hooks is not None:
          for hook in hooks:
            repo.configAdd("hook-mux.pre-commit", hook)

        repo.commit()

    # Check that everything works if no hook is configured.
    doTest()

    # Also verify that things just work if the hook key is empty.
    doTest([""])

    # Two in-line hooks. Both failing. Used to verify that both are
    # actually executed.
    hook1 = "%s -c 'exit(13)'" % executable
    hook2 = "%s -c 'exit(42)'" % executable

    with self.assertRaisesRegex(ProcessError, r"Status 13"):
      doTest(["", hook1, hook2])

    with self.assertRaisesRegex(ProcessError, r"Status 42"):
      doTest([hook2, "", hook1, " "])

    with defer() as d:
      script = NamedTemporaryFile(mode="w", delete=False)
      d.defer(unlink, script.name)

      try:
        script.write("#!%s\nexit(12)" % executable)
      finally:
        script.close()

      # Make sure the script is executable.
      chmod(script.name, 0o755)
      with self.assertRaisesRegex(ProcessError, r"Status 12"):
        doTest([script.name])


if __name__ == "__main__":
  main()
