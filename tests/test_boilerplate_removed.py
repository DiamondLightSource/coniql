"""This file checks that all the example boilerplate text has been removed"""
import os

import pytest


@pytest.fixture
def readme():
    readme_file = os.path.abspath("README.rst")
    with open(readme_file, "r") as f:
        contents = f.read().replace("\n", " ")
    return contents


@pytest.fixture
def setupcfg():
    import configparser

    conf = configparser.ConfigParser()
    conf.read("setup.cfg")

    return conf["metadata"]


@pytest.fixture
def doc_index():
    indexrst = os.path.abspath("docs/index.rst")
    with open(indexrst, "r") as f:
        contents = f.read().replace("\n", " ")
    return contents


@pytest.fixture
def doc_api():
    apirst = os.path.abspath("docs/reference/api.rst")
    with open(apirst, "r") as f:
        contents = f.read().replace("\n", " ")
    return contents


# README
def test_changed_README(readme):
    if "This is where you should write a short paragraph" in readme:
        raise AssertionError(
            "Please change ./README.rst "
            "to include a paragraph on what your module does"
        )


# setup.cfg
def test_module_description(setupcfg):
    if "One line description of your module" in setupcfg["description"]:
        raise AssertionError(
            "Please change description in ./setup.cfg "
            "to be a one line description of your module"
        )


# Docs
def test_docs_index_changed(doc_index):
    if "Write some introductory paragraphs here" in doc_index:
        raise AssertionError(
            "Please change the documentation in docs/index.rst "
            "to describe how to use your module"
        )


def test_docs_ref_api_changed(doc_api):
    if "You can mix verbose text with docstring and signature" in doc_api:
        raise AssertionError(
            "Please change the documentation in docs/reference/api.rst "
            "to introduce the API for your module"
        )
