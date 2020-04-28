# This file has been copied from:
# <github-url-for-template-module>
from subprocess import check_output, CalledProcessError
import re


def get_version_from_git():
    tag, plus, dirty = "0.0", "unknown", ""
    git_cmd = "git describe --tags --dirty --always --long"
    try:
        # describe is TAG-NUM-gHEX[-dirty] or HEX[-dirty]
        describe = check_output(git_cmd.split()).decode().strip()
        if describe.endswith("-dirty"):
            describe = describe[:-6]
            dirty = ".dirty"
        if "-" in describe:
            # There is a tag, extract it and the other pieces
            match = re.search(r'^(.+)-(\d+)-g([0-9a-f]+)$', describe)
            tag, plus, md5 = match.groups()
        else:
            # No tag, just md5
            plus, md5 = "unknown", describe
    except CalledProcessError:
        # not a git repo, maybe an archive
        tags = [t[5:].strip() for t in "$Format:%D$".split(",")
                if t.startswith("tag: ")]
        if tags:
            tag = tags[0]
            plus = "0"
        md5 = "$Format:%h$"
        if md5.startswith("$"):
            md5 = "error"
    if plus != "0" or dirty:
        # Not on a tag, add additional info
        return "%(tag)s+%(plus)s.%(md5)s%(dirty)s" % locals()
    else:
        # On a tag, just return it
        return tag


__version__ = get_version_from_git()


def get_cmdclass():
    import os
    from setuptools.command import build_py, sdist

    def make_static_version(base_dir, pkg):
        with open(os.path.join(base_dir, pkg, "_static_version.py"), "w") as f:
            f.write("__version__ = %r\n" % __version__)

    class BuildPy(build_py.build_py):
        def run(self):
            super(BuildPy, self).run()
            for pkg in self.packages:
                make_static_version(self.build_lib, pkg)

    class Sdist(sdist.sdist):
        def make_release_tree(self, base_dir, files):
            super(Sdist, self).make_release_tree(base_dir, files)
            for pkg in self.distribution.packages:
                make_static_version(base_dir, pkg)

    return dict(build_py=BuildPy, sdist=Sdist)
