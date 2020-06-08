import random
import string
import subprocess
import sys
from pathlib import Path
from subprocess import Popen

import pytest
from tartiflette import Engine

from coniql.app import make_context

SOFT_RECORDS = str(Path(__file__).parent / "soft_records.db")

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


@pytest.fixture
def ioc():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "epicscorelibs.ioc",
            "-m",
            f"P={PV_PREFIX}",
            "-d",
            SOFT_RECORDS,
        ],
        stdin=subprocess.PIPE,
        # stdout=subprocess.PIPE,
        # stderr=subprocess.STDOUT,
        text=True,
    )
    yield process
    try:
        process.communicate("exit")
    except ValueError:
        # Someone else already called communicate
        pass


def wait_for_ioc(ioc):
    while True:
        line = ioc.stdout.readline()
        if "complete" in line:
            return


@pytest.mark.asyncio
async def test_get_float_pv(engine: Engine, ioc: Popen):
    query = (
        """
query {
    getChannel(id: "ca://%slongout") {
        value {
            float
            string
        }
        display {
            widget
        }
    }
}
"""
        % PV_PREFIX
    )
    context = make_context()
    result = await engine.execute(query, context=context)
    assert result == dict(
        data=dict(
            getChannel=dict(
                value=dict(float=42.0, string="42"), display=dict(widget="TEXTINPUT"),
            ),
        )
    )
