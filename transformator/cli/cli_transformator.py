from pathlib import Path
import sys
import json
from importlib.metadata import version

from transformator import utils


def cli_transformator():
    if "--version" in sys.argv:
        print(f"meemoo-sip-transformator {version('meemoo-sip-transformator')}")
        exit()

    if len(sys.argv) != 2:
        print("Usage: meemoo-sip-transformator PATH\n\nSupported SIP versions: 2.1")
        exit(1)

    path = Path(sys.argv[1])

    profile = utils.get_sip_profile(path)
    transformator_fn = utils.get_sip_transformator(profile)
    data = transformator_fn(path)

    print(json.dumps(data))


if __name__ == "__main__":
    cli_transformator()
