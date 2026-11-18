"""Create a teacher login in the local credentials file."""

import json
import secrets
from getpass import getpass

from app import hash_password, teachers_file


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass("Teacher password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    if teachers_file.exists():
        credentials = json.loads(teachers_file.read_text(encoding="utf-8"))
    else:
        credentials = {"teachers": []}

    if not isinstance(credentials, dict) or not isinstance(
        credentials.get("teachers"), list
    ):
        raise SystemExit("Credentials file must contain a teachers list.")
    teacher_records = credentials["teachers"]
    if any(
        not isinstance(record, dict)
        or not isinstance(record.get("username"), str)
        or record.get("username") == username
        for record in teacher_records
    ):
        raise SystemExit("Credentials file contains an invalid entry or username.")

    salt = secrets.token_bytes(16)
    teacher_records.append(
        {
            "username": username,
            "salt": salt.hex(),
            "password_hash": hash_password(password, salt).hex(),
        }
    )
    teachers_file.parent.mkdir(parents=True, exist_ok=True)
    teachers_file.write_text(
        json.dumps(credentials, indent=2) + "\n", encoding="utf-8"
    )
    teachers_file.chmod(0o600)
    print(f"Teacher '{username}' added to {teachers_file}.")


if __name__ == "__main__":
    main()
