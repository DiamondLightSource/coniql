import re

from re import Match

INCLUDE_REGEX = '#include (.*)\n'


def load_and_preprocess(yaml_path: str) -> str:
    """Loads a YAML file and includes any other YAML files using the
    #include <path> tags"""
    with open(yaml_path, 'r') as f:
        text = f.read()
    return re.sub(INCLUDE_REGEX, include_match, text)


def include_match(match: Match) -> str:
    """Auxilluary function to load_and_preprocess, called on a match for the
    include syntax"""
    return load_and_preprocess(match.group(1))
