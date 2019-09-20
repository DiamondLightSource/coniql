try:
    # In a release there will be a static version file written by setup.py
    from ._static_version import __version__
except ImportError:
    # Otherwise get the release number from git describe
    from ._git_version import __version__
