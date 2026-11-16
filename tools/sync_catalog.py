"""Import files from tracked upstream Agent Skill publishers, without running them."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "wac81/mini-harness-plugins"
ARCHIVE_LIMIT = 24 * 1024 * 1024
SKILL_LIMIT = 64 * 1024
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION = re.compile(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})")
SHA = re.compile(r"[0-9a-f]{40}")
WINDOWS_DEVICES = {"con", "prn", "aux", "nul", *(f"{prefix}{i}" for prefix in ("com", "lpt") for i in range(1, 10))}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


def download(url: str, limit: int, *, api=False) -> bytes:
    headers = {"User-Agent": "mini-harness-catalog-sync"}
    if api and (token := os.getenv("GH_TOKEN")):
        headers["Authorization"] = f"Bearer {token}"
    with OPENER.open(Request(url, headers=headers), timeout=30) as reply:
        raw = reply.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("download exceeds size limit")
    return raw


def github(path: str) -> dict:
    return json.loads(download(f"https://api.github.com/repos/{path}", 2 * 1024 * 1024, api=True))


def upstream_ref(source: dict) -> tuple[str, str | None]:
    repo = source["repo"]
    ref = source["ref"]
    version = None
    if ref == "latest-release":
        ref = github(f"{repo}/releases/latest")["tag_name"]
        version = ref.removeprefix("v")
        if not VERSION.fullmatch(version):
            raise ValueError("latest release does not have a stable version tag")
    sha = github(f"{repo}/commits/{quote(ref, safe='')}")["sha"]
    if not SHA.fullmatch(sha):
        raise ValueError("invalid upstream commit")
    return sha, version


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(path: str) -> bool:
    return all(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", part)
               and not part.endswith(".") and part.lower() != ".git"
               and part.split(".", 1)[0].lower() not in WINDOWS_DEVICES for part in path.split("/"))


def locate_skills(source: dict, names: dict) -> list[str]:
    if "paths" in source:
        return source["paths"]
    prefix = source["discover"].rstrip("/") + "/"
    return sorted(path.rsplit("/", 1)[0] for path in names
                  if path.startswith(prefix) and re.fullmatch(r"[a-z0-9-]+/SKILL\.md", path[len(prefix):]))


def read_metadata(raw: bytes) -> tuple[str, str]:
    if len(raw) > SKILL_LIMIT:
        raise ValueError("SKILL.md exceeds size limit")
    info = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", raw.decode("utf-8"), re.S)
    if not info or not info[2].strip():
        raise ValueError("missing Skill frontmatter or body")
    name = re.search(r"^name:\s*([^\n]+)", info[1], re.M)
    description = re.search(r"^description: *(.*(?:\n[ \t]+[^\n]*)*)", info[1], re.M)
    if not name or not description:
        raise ValueError("name and description are required")
    skill_id = name[1].strip().strip("\"'")
    text = " ".join(description[1].strip().lstrip("|>").split()).strip("\"'")
    if not ID.fullmatch(skill_id) or len(skill_id) > 48 or not text:
        raise ValueError("invalid Skill name or description")
    return skill_id, text[:380].rstrip()


def bundle_skill(archive: ZipFile, names: dict, base: str, source: dict, licence_path: str, licence: bytes) -> bytes:
    prefix = f"{base}/" if base else ""
    files = {}
    size = 0
    for path, info in names.items():
        if not path.startswith(prefix):
            continue
        relative = path[len(prefix):]
        if relative.startswith(tuple(source.get("omit", []))):
            continue
        mode = stat.S_IFMT(info.external_attr >> 16)
        if not safe_path(relative) or mode not in (0, stat.S_IFREG):
            raise ValueError("archive contains an unsupported path or member")
        size += info.file_size
        if size > ARCHIVE_LIMIT or len(files) >= 999:
            raise ValueError("Skill bundle exceeds size limit")
        files[relative] = archive.read(info)
    if licence_path not in {prefix + name for name in files}:
        files["LICENSE"] = licence
        size += len(licence)
    if size > ARCHIVE_LIMIT or len(set(name.casefold() for name in files)) != len(files):
        raise ValueError("Skill bundle has excessive size or conflicting paths")
    packed = io.BytesIO()
    with ZipFile(packed, "w", ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(files.items()):
            member = ZipInfo(name)
            member.compress_type = ZIP_DEFLATED
            output.writestr(member, data, compresslevel=9)
    if packed.tell() > ARCHIVE_LIMIT:
        raise ValueError("compressed Skill bundle exceeds size limit")
    return packed.getvalue()


def equivalent_package(previous: dict, incoming: bytes) -> bool:
    archive = previous.get("archive")
    if not archive or archive["repo"] != REGISTRY or not safe_path(archive["path"]):
        return False
    path = ROOT / archive["path"]
    if not path.is_file():
        return False
    with ZipFile(path) as old, ZipFile(io.BytesIO(incoming)) as new:
        return sorted((x.filename, x.CRC, x.file_size) for x in old.infolist()) == sorted(
            (x.filename, x.CRC, x.file_size) for x in new.infolist())


def version_tuple(value: str) -> tuple[int, ...]:
    if not VERSION.fullmatch(value):
        raise ValueError("invalid catalog version")
    return tuple(map(int, value.split(".")))


def make_update(source, sha, release, archive, names, base, catalogue):
    path = f"{base}/SKILL.md" if base else "SKILL.md"
    if not safe_path(path):
        raise ValueError("invalid Skill path")
    member = names[path]
    if member.file_size > SKILL_LIMIT or stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG):
        raise ValueError("invalid Skill file")
    raw = archive.read(member)
    skill_id, description = read_metadata(raw)
    previous = catalogue.get(skill_id)
    license_path = source["license_file"].format(skill=base)
    licence_member = names[license_path]
    if licence_member.file_size > SKILL_LIMIT or stat.S_IFMT(licence_member.external_attr >> 16) not in (0, stat.S_IFREG):
        raise ValueError("invalid license file")
    licence = archive.read(licence_member)
    if digest(licence) != source["license_sha256"]:
        raise ValueError("license differs from the tracked license")
    if previous:
        old = previous["source"]
        if not isinstance(old, dict) or old["repo"].casefold() != source["repo"].casefold() or old["path"] != path:
            raise ValueError("plugin ID is owned by another source")
        if old["commit"] == sha or release and version_tuple(release) <= version_tuple(previous["version"]):
            return None
    if source.get("single_file"):
        packed = None
    else:
        packed = bundle_skill(archive, names, base, source, license_path, licence)
    if previous and previous["source"]["sha256"] == digest(raw) and (
            (packed is None and not previous["source"].get("archive"))
            or (packed is not None and equivalent_package(previous["source"], packed))):
        return None
    if release:
        version = release
    elif previous:
        major, minor, patch = version_tuple(previous["version"])
        version = f"{major}.{minor}.{patch + 1}"
    else:
        version = "1.0.0"
    version_tuple(version)
    metadata = previous or {
        "id": skill_id, "category": source["category"], "author": source["author"], "license": source["license"],
        "title": {"en": skill_id}, "description": {"en": description},
        "example": {"en": f"Show me a practical way to use {skill_id} in this project."},
    }
    entry = {**metadata, "version": version, "source": {"repo": source["repo"], "commit": sha,
                                                         "path": path, "sha256": digest(raw)}}
    return entry, packed


def discover(sources: list[dict], catalogue: dict) -> list:
    updates = []
    accepted = dict(catalogue)
    for source in sources:
        try:
            sha, release = upstream_ref(source)
            raw = download(f"https://codeload.github.com/{source['repo']}/zip/{sha}", 64 * 1024 * 1024)
            with ZipFile(io.BytesIO(raw)) as archive:
                members = [info for info in archive.infolist() if not info.is_dir()]
                names = {info.filename.split("/", 1)[1]: info for info in members}
                if len(members) != len(names):
                    raise ValueError("duplicate upstream archive paths")
                for base in locate_skills(source, names):
                    try:
                        result = make_update(source, sha, release, archive, names, base, accepted)
                        if result:
                            entry, _ = result
                            if entry["id"] not in accepted and len(accepted) >= 200:
                                raise ValueError("catalog is at capacity")
                            accepted[entry["id"]] = entry
                            updates.append(result)
                            print(f"Ready: {entry['id']} {entry['version']}")
                    except (KeyError, ValueError, BadZipFile) as error:
                        print(f"Skipped {source['repo']}:{base} ({error})")
        except (OSError, KeyError, ValueError, BadZipFile) as error:
            print(f"Skipped {source['repo']} ({error})")
    return updates


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def publish(catalogue: dict, updates: list) -> None:
    archives = []
    for entry, packed in updates:
        if packed is not None:
            path = f"packages/auto/{entry['id']}.zip"
            destination = ROOT / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(packed)
            archives.append(path)
            entry["source"]["archive"] = {"repo": REGISTRY, "path": path, "sha256": digest(packed)}
    if archives:
        git("add", "--", *archives)
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", "Sync upstream Skill packages")
        sha = git("rev-parse", "HEAD")
        for entry, packed in updates:
            if packed is not None:
                entry["source"]["archive"]["commit"] = sha
    catalogue.update({entry["id"]: entry for entry, _ in updates})
    document = json.dumps({"schema": 2, "plugins": list(catalogue.values())}, ensure_ascii=False, indent=2) + "\n"
    if len(document.encode()) > 256 * 1024:
        raise ValueError("catalog exceeds app size limit")
    (ROOT / "catalog.json").write_text(document, encoding="utf-8")
    git("add", "--", "catalog.json")
    git("commit", "-m", "Publish automatically validated upstream Skills")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="commit the auto-published entries locally")
    args = parser.parse_args()
    if args.write and git("status", "--porcelain"):
        raise SystemExit("Publishing requires a clean registry checkout")
    sources = json.loads((ROOT / "sources.json").read_bytes())
    entries = json.loads((ROOT / "catalog.json").read_bytes())["plugins"]
    catalogue = {entry["id"]: entry for entry in entries}
    updates = discover(sources, catalogue)
    if args.write and updates:
        publish(catalogue, updates)
    print(f"{len(updates)} publishable change(s)")


if __name__ == "__main__":
    main()
