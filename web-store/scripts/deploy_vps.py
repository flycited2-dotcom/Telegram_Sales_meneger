from __future__ import annotations

import argparse
import getpass
import os
import posixpath
import shlex
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path


REMOTE_ROOT = "/var/www/climat-simf.ru"
PROCESS_NAME = "climat-simf-store"
PUBLIC_URL = "https://climat-simf.ru"

EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".pnp",
    ".superpowers",
    ".vercel",
    "__pycache__",
    "build",
    "coverage",
    "node_modules",
    "out",
}


def should_include_archive_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    if not normalized:
        return False

    name = posixpath.basename(normalized)
    parts = set(normalized.split("/"))
    if parts & EXCLUDED_PARTS:
        return False
    if name == ".env" or name.startswith(".env."):
        return False
    if name.endswith(".pyc") or name.endswith(".tsbuildinfo"):
        return False
    if name.endswith(".log") or name.startswith("dev-server."):
        return False
    return True


def build_remote_deploy_script(
    *,
    remote_root: str,
    process_name: str,
    build_log: str,
    run_install: bool,
) -> str:
    quoted_root = shlex.quote(remote_root)
    quoted_process = shlex.quote(process_name)
    quoted_log = shlex.quote(build_log)
    install = "npm ci\n" if run_install else ""

    return "\n".join(
        [
            "set -euo pipefail",
            f"cd {quoted_root}",
            install.rstrip(),
            f"npm run build >{quoted_log} 2>&1",
            "test -f .next/prerender-manifest.json",
            "test -s .next/BUILD_ID",
            f"pm2 delete {quoted_process} >/tmp/{process_name}-pm2.log 2>&1 || true",
            "pm2 start ecosystem.config.cjs --update-env",
            "sleep 5",
            "pm2 jlist >/tmp/climat-simf-pm2.json",
            "curl -fsS -m 30 http://127.0.0.1:3001/ >/tmp/climat-simf-health.html",
        ]
    )


def create_archive(project_root: Path) -> Path:
    temp = tempfile.NamedTemporaryFile(prefix="climat-simf-deploy-", suffix=".tar.gz", delete=False)
    temp.close()
    archive_path = Path(temp.name)

    with tarfile.open(archive_path, "w:gz") as archive:
        for path in project_root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(project_root).as_posix()
            if should_include_archive_path(rel):
                archive.add(path, arcname=rel)

    return archive_path


def load_dotenv_if_available(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in os.environ:
            continue
        os.environ[key] = value.strip().strip("\"'")


def public_healthcheck(url: str) -> None:
    checks = [url.rstrip("/") + "/", url.rstrip("/") + "/catalog?available=1&photo=1", url.rstrip("/") + "/robots.txt"]
    for check_url in checks:
        with urllib.request.urlopen(check_url, timeout=45) as response:
            if response.status != 200:
                raise RuntimeError(f"{check_url} returned HTTP {response.status}")


def build_connect_kwargs(*, host: str, user: str, key_path: str | None, password: str | None) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "hostname": host,
        "username": user,
        "timeout": 20,
        "banner_timeout": 20,
        "auth_timeout": 20,
    }
    if key_path:
        kwargs["key_filename"] = key_path
    if password:
        kwargs["password"] = password
    return kwargs


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv_if_available(project_root)

    parser = argparse.ArgumentParser(description="Deploy web-store to the production VPS with backup, build, restart and healthchecks.")
    parser.add_argument("--host", default=os.getenv("WEB_STORE_VPS_HOST") or "212.116.115.150")
    parser.add_argument("--user", default=os.getenv("WEB_STORE_VPS_USER") or "root")
    parser.add_argument("--remote-root", default=os.getenv("WEB_STORE_VPS_REMOTE_ROOT") or REMOTE_ROOT)
    parser.add_argument("--process-name", default=os.getenv("WEB_STORE_PM2_PROCESS") or PROCESS_NAME)
    parser.add_argument("--public-url", default=os.getenv("WEB_STORE_PUBLIC_URL") or PUBLIC_URL)
    parser.add_argument("--key-path", default=os.getenv("WEB_STORE_SSH_KEY_PATH"))
    parser.add_argument("--install", action="store_true", help="Run npm ci on the server before build.")
    parser.add_argument("--skip-public-healthcheck", action="store_true")
    args = parser.parse_args()

    password = os.getenv("WEB_STORE_VPS_PASSWORD")
    if not password and not args.key_path:
        password = getpass.getpass("VPS password: ")

    try:
        import paramiko
    except ImportError as exc:
        raise SystemExit("paramiko is required: python -m pip install paramiko") from exc

    timestamp = time.strftime("%Y%m%d%H%M%S")
    backup_path = f"{args.remote_root}.source-backup-{timestamp}.tar.gz"
    remote_archive = f"/tmp/climat-simf-deploy-{timestamp}.tar.gz"
    build_log = f"/tmp/climat-simf-build-{timestamp}.log"
    archive_path = create_archive(project_root)

    print(f"Archive: {archive_path}")
    print(f"Backup: {backup_path}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(**build_connect_kwargs(host=args.host, user=args.user, key_path=args.key_path, password=password))

    try:
        sftp = client.open_sftp()
        sftp.put(str(archive_path), remote_archive)
        sftp.close()

        backup_command = (
            f"test -d {shlex.quote(args.remote_root)} && "
            f"tar --exclude=node_modules --exclude=.next --exclude=.env -czf {shlex.quote(backup_path)} "
            f"-C {shlex.quote(posixpath.dirname(args.remote_root))} {shlex.quote(posixpath.basename(args.remote_root))}"
        )
        extract_command = f"mkdir -p {shlex.quote(args.remote_root)} && tar -xzf {shlex.quote(remote_archive)} -C {shlex.quote(args.remote_root)}"
        deploy_command = build_remote_deploy_script(
            remote_root=args.remote_root,
            process_name=args.process_name,
            build_log=build_log,
            run_install=args.install,
        )
        command = f"{backup_command}\n{extract_command}\n{deploy_command}\nrm -f {shlex.quote(remote_archive)}"

        stdin, stdout, stderr = client.exec_command(f"bash -lc {shlex.quote(command)}", timeout=900)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            print(out[-4000:])
            print(err[-4000:], file=sys.stderr)
            raise SystemExit(code)
    finally:
        client.close()
        archive_path.unlink(missing_ok=True)

    if not args.skip_public_healthcheck:
        public_healthcheck(args.public_url)

    print("Deploy completed.")
    print(f"Build log: {build_log}")
    print(f"Backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
