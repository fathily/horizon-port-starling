#!/usr/bin/env python3
"""Prepare Mojang's official unobfuscated Minecraft 1.21.11 artifacts for Horizon port analysis.

Downloaded game files and generated data stay under HORIZON_VERSIONS (outside Git).
Only the compact facts/class indexes and compatibility report are intended as CI artifacts.
"""

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import class_index
import lab
import version_port as vp

VERSION = "1.21.11"
JAVA_MAJOR = 21
WORLD_VERSION = 4671
PROTOCOL_VERSION = 774
RESOURCE_PACK_FORMAT = "75.0"
DATA_PACK_FORMAT = "94.1"

# Exact links published by Mojang on the 1.21.11 release page.
CLIENT_ZIP_URL = (
    "https://piston-data.mojang.com/v1/objects/"
    "e11114e8a2eea43bac93c022c9327d3916b24738/1_21_11_unobfuscated.zip"
)
CLIENT_ZIP_SHA1 = "e11114e8a2eea43bac93c022c9327d3916b24738"
SERVER_URL = (
    "https://piston-data.mojang.com/v1/objects/"
    "3ca78d5068bf9b422f694d3f0820e289581c0f0d/server.jar"
)
SERVER_SHA1 = "3ca78d5068bf9b422f694d3f0820e289581c0f0d"


def extract_client(archive_path: Path, destination: Path) -> dict:
    """Extract the one client jar whose embedded version.json identifies 1.21.11."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    matches = []
    with zipfile.ZipFile(archive_path) as archive:
        jar_members = [name for name in archive.namelist() if name.lower().endswith(".jar")]
        for member in jar_members:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, suffix=".jar", delete=False
            ) as stream:
                temporary = Path(stream.name)
                with archive.open(member) as source:
                    shutil.copyfileobj(source, stream)
            try:
                facts = vp.jar_facts(temporary)
                expected = (
                    facts["world_version"] == WORLD_VERSION
                    and facts["protocol_version"] == PROTOCOL_VERSION
                    and facts["java_version"] == JAVA_MAJOR
                    and facts["resource_pack"] == RESOURCE_PACK_FORMAT
                    and facts["data_pack"] == DATA_PACK_FORMAT
                )
                if expected and facts["id"] in {VERSION, VERSION + "_unobfuscated"}:
                    matches.append((member, temporary, facts))
                else:
                    temporary.unlink(missing_ok=True)
            except (KeyError, ValueError, zipfile.BadZipFile, json.JSONDecodeError):
                temporary.unlink(missing_ok=True)

    if len(matches) != 1:
        for _, temporary, _ in matches:
            temporary.unlink(missing_ok=True)
        raise SystemExit(
            "Expected exactly one Mojang 1.21.11 client jar with the pinned version facts; "
            f"found {len(matches)}. Refusing to guess."
        )

    member, temporary, facts = matches[0]
    temporary.replace(destination)
    print(f"Verified 1.21.11 client jar from {member}", flush=True)
    return facts


def prepare(args: argparse.Namespace) -> int:
    store = vp.version_dir(VERSION)
    store.mkdir(parents=True, exist_ok=True)
    official = store / "official"
    official.mkdir(parents=True, exist_ok=True)

    client_zip = lab.download(
        CLIENT_ZIP_URL, official / "1_21_11_unobfuscated.zip", CLIENT_ZIP_SHA1
    )
    server = lab.download(SERVER_URL, store / "jars" / "server.jar", SERVER_SHA1)
    client = store / "jars" / "client.jar"
    facts = extract_client(client_zip, client)

    # Recheck at the boundary where metadata is persisted, not only while scanning the ZIP.
    if facts["world_version"] != WORLD_VERSION or facts["protocol_version"] != PROTOCOL_VERSION:
        raise SystemExit(f"Unexpected Minecraft identity: {facts}")
    if facts["java_version"] != JAVA_MAJOR:
        raise SystemExit(f"Expected Java {JAVA_MAJOR}, got {facts['java_version']}")

    version_json = store / "version.json"
    with zipfile.ZipFile(client) as archive:
        version_json.write_bytes(archive.read("version.json"))

    server_game = vp.unpack_game(server, store / "jars" / "server-game.jar", VERSION)
    reports = store / "datagen" / "reports"
    if not reports.exists():
        print(f"Running the official {VERSION} data generator with Java {JAVA_MAJOR}", flush=True)
        vp.run_datagen(server, reports, JAVA_MAJOR)

    classes = class_index.index_jars([client, server_game], jobs=args.jobs)
    lab.write_json(store / "facts.json", facts)
    lab.write_json(
        store / "prepared.json",
        {
            "version": VERSION,
            "pinned": False,
            "source": "Mojang official unobfuscated development artifacts",
            "java_major": JAVA_MAJOR,
            "paths": {
                "client": str(client.resolve()),
                "server": str(server.resolve()),
                "server_game": str(server_game.resolve()),
                "reports": str(reports.resolve()),
                "version_json": str(version_json.resolve()),
            },
        },
    )
    lab.write_json(store / "classes.json", classes)
    print(
        f"Prepared {VERSION}: {len(classes)} classes indexed; "
        f"reports at {reports}",
        flush=True,
    )
    print(json.dumps(facts, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=2,
        help="class indexing processes (default: 2 for CI memory limits)",
    )
    return prepare(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
