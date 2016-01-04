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
  environ,
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
from textwrap import (
  dedent,
)
from unittest import (
  main,
  TestCase,
)


GIT = findCommand("git")


class GitRepository(Repository):
  """A git repository with subrepo support."""
  def __init__(self, symlink=True, section=None):
    """Initialize the git repository."""
    super().__init__(GIT)

    # When using the symlink version we cannot pass any parameters to
    # the script.
    assert not (symlink and section is not None)

    self._symlink = symlink
    self._section = section


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

    src = dst
    dst = self.path(".git", "hooks", "pre-commit")

    if self._symlink:
      # We are pretty sure things work when copying the file. We want to
      # verify that symlinking works as well.
      symlink(src, dst)
    else:
      args = "--section=%s" % self._section if self._section is not None else ""

      # We also want to use the version with a command line parameter.
      # Note that we have to specify the PYTHONPATH here explicitly for
      # the case that virtual environments are in use.
      with open(dst, "w") as f:
        pyc = environ.get("PYTHONDONTWRITEBYTECODE", "")
        path = environ.get("PATH", "")
        pypath = environ.get("PYTHONPATH", "")
        content = dedent("""\
          #!/bin/sh
          PATH="{path}" \\
          PYTHONPATH="{pypath}" \\
          PYTHONDONTWRITEBYTECODE="{pyc}" \\
          {py} {script} {args} --hook-type pre-commit
        """)
        content = content.format(path=path, pypath=pypath, pyc=pyc,
                                 py=executable, script=src, args=args)

        f.write(content)

    # The hook script is required to be executable.
    chmod(dst, 0o755)


  def configAdd(self, *args):
    """Invoke a git-config command."""
    self.git("config", "--local", "--add", *args)


class TestGitHookMux(TestCase):
  """Tests for the git-subrepo script."""
  def testPreCommitHookInvocation(self):
    """Verify that pre-commit hooks are invoked correctly."""
    def doTest(hooks=None, symlink=True):
      """Configure pre-commit hooks in a repository and create a commit."""
      with GitRepository(symlink=symlink) as repo:
        write(repo, "test.dat", data="test")
        repo.add("test.dat")

        if hooks is not None:
          for hook in hooks:
            repo.configAdd("hook-mux.pre-commit", hook)

        repo.commit()

    # Check that everything works if no hook is configured.
    doTest()

    # Also verify that things just work if the hook key is empty.
    doTest([""], symlink=False)

    # Two in-line hooks. Both failing. Used to verify that both are
    # actually executed.
    hook1 = "%s -c 'exit(13)'" % executable
    hook2 = "%s -c 'exit(42)'" % executable

    with self.assertRaisesRegex(ProcessError, r"Status 13"):
      doTest(["", hook1, hook2])

    with self.assertRaisesRegex(ProcessError, r"Status 42"):
      doTest([hook2, "", hook1, " "], symlink=False)

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


  def testSectionIsConfigurable(self):
    """Verify that the section git-hook-mux uses is configurable."""
    def doTest(section):
      """Check whether the hook-mux script works when using the given section."""
      with GitRepository(symlink=False, section=section) as repo:
        hook = "%s -c 'exit(57)'" % executable

        write(repo, "file.txt", data="data")
        repo.add("file.txt")
        repo.configAdd("%s.pre-commit" % section, hook)

        with self.assertRaisesRegex(ProcessError, r"Status 57"):
          repo.commit()

    doTest("test")
    doTest("hook-mux")
    doTest("hook-mux-files-cxx")


  def testSelfInvocation(self):
    """Verify that the '<self>' keyword works properly."""
    def doTest(symlink):
      """Test the '<self>' keyword with forwarding hook muxes."""
      with GitRepository(symlink=symlink) as repo:
        hook = "%s -c 'exit(57)'" % executable

        write(repo, "file.txt", data="data")
        repo.add("file.txt")
        # Configure the "main" hook-mux.
        repo.configAdd("hook-mux.pre-commit", "<self> --section=test1-mux")
        # Also configure more hooks that forward invocations.
        repo.configAdd("test1-mux.pre-commit", "<self> --section=test2-mux")
        repo.configAdd("test2-mux.pre-commit", "<self> --section=test3-mux")
        repo.configAdd("test3-mux.pre-commit", "<self> --section=test4-mux")
        # The last one in the chain finally performs the hook invocation.
        repo.configAdd("test4-mux.pre-commit", hook)

        with self.assertRaisesRegex(ProcessError, r"Status 57"):
          repo.commit()

    doTest(True)
    doTest(False)


if __name__ == "__main__":
  main()
