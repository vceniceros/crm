import unittest

from login_ticket_audit_runner import run_concurrency_test, run_replay_test


class LoginTicketAuditTests(unittest.TestCase):
    def test_login_ticket_replay(self) -> None:
        result = run_replay_test()
        self.assertTrue(result["pass"], result)

    def test_login_ticket_concurrency(self) -> None:
        result = run_concurrency_test()
        self.assertTrue(result["pass"], result)


if __name__ == "__main__":
    unittest.main()
