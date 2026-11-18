import json
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, Request, Response

import src.app as school_app


def make_request(session_id: str | None = None) -> Request:
    headers = []
    if session_id:
        headers.append(
            (b"cookie", f"{school_app.session_cookie_name}={session_id}".encode())
        )
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("test", 1234),
            "server": ("test", 80),
        }
    )


class TeacherAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.credentials_path = Path(self.temporary_directory.name) / "teachers.json"
        self.previous_credentials_path = school_app.teachers_file
        school_app.teachers_file = self.credentials_path
        school_app.active_sessions.clear()
        self.original_participants = school_app.activities["Chess Club"]["participants"][:]

        password = "correct horse battery staple"
        salt = bytes.fromhex("0123456789abcdef0123456789abcdef")
        self.credentials_path.write_text(
            json.dumps(
                {
                    "teachers": [
                        {
                            "username": "teacher",
                            "salt": salt.hex(),
                            "password_hash": school_app.hash_password(
                                password, salt
                            ).hex(),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        school_app.activities["Chess Club"]["participants"] = self.original_participants
        school_app.active_sessions.clear()
        school_app.teachers_file = self.previous_credentials_path
        self.temporary_directory.cleanup()

    def test_activity_mutations_require_teacher_session(self) -> None:
        request = make_request()

        with self.assertRaises(HTTPException) as signup_error:
            school_app.signup_for_activity(
                "Chess Club", "student@mergington.edu", request
            )
        self.assertEqual(signup_error.exception.status_code, 401)

        with self.assertRaises(HTTPException) as unregister_error:
            school_app.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", request
            )
        self.assertEqual(unregister_error.exception.status_code, 401)
        self.assertEqual(
            school_app.activities["Chess Club"]["participants"],
            self.original_participants,
        )

    def test_teacher_login_allows_registration_until_logout(self) -> None:
        response = Response()
        result = school_app.login_teacher(
            school_app.TeacherLogin(
                username="teacher", password="correct horse battery staple"
            ),
            response,
        )
        self.assertTrue(result["authenticated"])

        session_id = response.headers["set-cookie"].split(";", maxsplit=1)[0].split(
            "=", maxsplit=1
        )[1]
        request = make_request(session_id)
        self.assertEqual(
            school_app.get_current_teacher(request),
            {"authenticated": True, "username": "teacher"},
        )

        school_app.signup_for_activity(
            "Chess Club", "student@mergington.edu", request
        )
        self.assertIn(
            "student@mergington.edu",
            school_app.activities["Chess Club"]["participants"],
        )

        school_app.logout_teacher(request, Response())
        with self.assertRaises(HTTPException) as error:
            school_app.signup_for_activity(
                "Chess Club", "another@mergington.edu", request
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_invalid_password_does_not_create_session(self) -> None:
        with self.assertRaises(HTTPException) as error:
            school_app.login_teacher(
                school_app.TeacherLogin(username="teacher", password="wrong password"),
                Response(),
            )

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(school_app.active_sessions, {})

    def test_activity_list_remains_public(self) -> None:
        self.assertIn("Chess Club", school_app.get_activities())


if __name__ == "__main__":
    unittest.main()
