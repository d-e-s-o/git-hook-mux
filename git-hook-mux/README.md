git-hook-mux
============


Purpose
-------

**git-hook-mux** is a `git` hook multiplexer. By its architecture, `git`
allows for *one* hook of a certain type to be in use at any time. For
example, the user may install a *single* `pre-commit` hook, one
`commit-msg` hook, and so on (see githooks(5) for more information on
hooks).

A hook multiplexer like **git-hook-mux** can be regarded as an
intermediary program that allows the user to actually configure
*multiple* hooks of the same type, by multiplexing them onto the one
hook type `git` supports natively. So instead of only allowing for a
single `pre-commit` hook the user can now install an arbitrary number of
them.


Installation
------------

In order to use **git-hook-mux** the
[cleanup](https://github.com/d-e-s-o/cleanup) and
[execute](https://github.com/d-e-s-o/execute) Python modules (contained
in the repository in compatible and tested versions) need to be
accessible by Python (typically by installing them in a directory listed
in `PYTHONPATH` or adjusting the latter to point to each of them).

On [Gentoo Linux](https://www.gentoo.org/), the provided
[ebuild](https://github.com/d-e-s-o/git-hook-mux-ebuild) can be used to
install the module on the system. On other systems the `PYTHONPATH`
environment variable could be adjusted within some initialization file
to include the path the module resides at or the module could be copied
into one of the folders searched by default.

As a next step **git-hook-mux** needs to be made known to `git`. In
particular, it needs to be made the target of the individual hooks to
multiplex onto. For the purpose of illustration we assume you want the
program to manage multiple `pre-commit` hooks, but installation can
happen similarly for all other hook types.

First, we tell `git` to use hooks we have control over. We do so by
pointing it to a designated directory. E.g.:

```bash
$ git config --global core.hooksPath ~/.git/hooks
```

Next, we create a symbolic link to our the
`git-hook-mux/src/deso/git/hook/mux/git-hook-mux.py` file:
```bash
$ ln -s <path-to-git-hook-mux.py> ~/.git/hooks/pre-commit
```

That's it. The hook multiplexer can now be [configured](#configuration).


Configuration
-------------

**git-hook-mux** is configured through `git`'s configuration. In
particular, it recognizes the `hook-mux` section. In this section you
can now list all the (`pre-commit`) hooks you want to run, in order:
```ini
[hook-mux]
  verbose = false
  pre-commit = <absolute-path-to-hook1>
  pre-commit = <absolute-path-to-hook2>
```

The `verbose` flag in each section can be used to debug hooks by
displaying what actions are performed. Each hook is simply a command or
script that is executed. Note that the path to each has to be absolute.

The above hooks would allow you to perform general actions on every
commit. However, sometimes you want to perform an action on the actual
`files` being committed and although nothing prevents you from
performing your own `git` commands from each script, **git-hook-mux**
can also help out here. In particular, it can be configured to allow for
comfortable invocation of hooks on files involved in a commit:
```ini
[hook-mux]
  ...
  pre-commit = <self> --section=hook-mux-files --file-cmd=\"/usr/bin/git diff --staged --name-only --diff-filter=AM --no-color --no-prefix\"

[hook-mux-files]
  # Do not allow committing of broken symbolic links.
  pre-commit = /usr/bin/readlink --canonicalize-existing
```

Here we invoke another instance of **git-hook-mux** (indicated by the
string `<self>`) recursively, which in turn can be configured using the
section `hook-mux-files`. Each hook in that section retrieves all the
files produced by the `git diff` command as arguments.
So in the example above, we have one `pre-commit` hook that simply tries
to resolve the paths to all committed files (those being added or
modified), failing if a broken symbolic link is to be committed, for
example.

You can play this game further and have additional sections for files of
a certain type. For instance, you can filter out all Python files and
make sure that a linter such as `pylint` does not complain about any, or
fail the commit otherwise (the
[file-filter](https://github.com/d-e-s-o/file-filter) program can help
you with that).


Support
-------

The module is tested with Python 3. There is no work going on to
ensure compatibility with Python 2.
