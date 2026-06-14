"""Unit tests for enterprise features: SAML, RBAC, GDPR, SOC2."""

import unittest
import tempfile
import os


class TestSAMLServiceProvider(unittest.TestCase):

    def setUp(self):
        from cherenkov.enterprise.saml import SAMLServiceProvider, SAMLConfig
        config = SAMLConfig(idp_metadata_url="https://idp.example.com/saml", enabled=True)
        self.sp = SAMLServiceProvider(config)

    def test_not_enabled_when_disabled(self):
        from cherenkov.enterprise.saml import SAMLServiceProvider
        sp = SAMLServiceProvider()
        self.assertFalse(sp.is_enabled())

    def test_enabled_when_configured(self):
        self.assertTrue(self.sp.is_enabled())

    def test_get_login_url_returns_url(self):
        url = self.sp.get_login_url()
        self.assertIn("https://idp.example.com/saml", url)
        self.assertIn("SAMLRequest", url)

    def test_get_login_url_empty_when_disabled(self):
        from cherenkov.enterprise.saml import SAMLServiceProvider
        sp = SAMLServiceProvider()
        self.assertEqual(sp.get_login_url(), "")

    def test_empty_response_returns_none(self):
        from cherenkov.enterprise.saml import SAMLAssertion
        result = self.sp.process_response("")
        self.assertIsNotNone(result)
        self.assertEqual(result.name_id, "")

    def test_authn_request_is_base64(self):
        url = self.sp.get_login_url()
        self.assertIn("SAMLRequest=", url)

    def test_end_session_works(self):
        from cherenkov.enterprise.saml import SAMLAssertion
        self.sp._sessions["test-user"] = SAMLAssertion(name_id="test-user", email="test@test.com")
        self.assertTrue(self.sp.end_session("test-user"))

    def test_end_session_nonexistent(self):
        self.assertFalse(self.sp.end_session("ghost"))


class TestRBACEngine(unittest.TestCase):

    def setUp(self):
        from cherenkov.enterprise.rbac import RBACEngine, User, Role
        self.rbac = RBACEngine()
        self.admin = User(id="admin-1", name="Admin", email="admin@test.com", role=Role.ADMIN)
        self.viewer = User(id="viewer-1", name="Viewer", email="viewer@test.com", role=Role.VIEWER)
        self.rbac.register_user(self.admin)
        self.rbac.register_user(self.viewer)

    def test_register_user(self):
        from cherenkov.enterprise.rbac import Role, Permission, User
        self.rbac.register_user(User(id="new", name="New", email="new@test.com", role=Role.READ_ONLY))
        self.assertIsNotNone(self.rbac.get_user("new"))

    def test_admin_has_all_permissions(self):
        from cherenkov.enterprise.rbac import Permission, Role
        for perm in Permission:
            self.assertTrue(self.rbac.has_permission("admin-1", perm))

    def test_viewer_lacks_approve(self):
        from cherenkov.enterprise.rbac import Permission
        self.assertFalse(self.rbac.has_permission("viewer-1", Permission.HITL_APPROVE))

    def test_viewer_has_list(self):
        from cherenkov.enterprise.rbac import Permission
        self.assertTrue(self.rbac.has_permission("viewer-1", Permission.HITL_LIST))

    def test_nonexistent_user_has_no_permissions(self):
        from cherenkov.enterprise.rbac import Permission
        self.assertFalse(self.rbac.has_permission("ghost", Permission.VALIDATE_VIEW))

    def test_require_permission_raises(self):
        from cherenkov.enterprise.rbac import Permission
        with self.assertRaises(PermissionError):
            self.rbac.require_permission("viewer-1", Permission.HITL_APPROVE)

    def test_set_role(self):
        from cherenkov.enterprise.rbac import Role, Permission
        self.rbac.set_role("viewer-1", Role.ADMIN)
        self.assertTrue(self.rbac.has_permission("viewer-1", Permission.HITL_APPROVE))

    def test_remove_user(self):
        self.assertTrue(self.rbac.remove_user("viewer-1"))
        self.assertIsNone(self.rbac.get_user("viewer-1"))

    def test_list_users(self):
        users = self.rbac.list_users()
        self.assertEqual(len(users), 2)

    def test_user_has_any(self):
        from cherenkov.enterprise.rbac import Permission
        self.assertTrue(self.rbac.user_has_any("viewer-1", [Permission.HITL_APPROVE, Permission.HITL_LIST]))
        self.assertFalse(self.rbac.user_has_any("viewer-1", [Permission.HITL_APPROVE, Permission.HITL_REJECT]))


class TestGDPRManager(unittest.TestCase):

    def setUp(self):
        from cherenkov.enterprise.gdpr import GDPRManager, GDPRConfig
        tmpdir = tempfile.mkdtemp()
        config = GDPRConfig(enabled=True, data_directory=tmpdir)
        self.gdpr = GDPRManager(config)

    def test_disabled_by_default(self):
        from cherenkov.enterprise.gdpr import GDPRManager
        gdpr = GDPRManager()
        self.assertFalse(gdpr.is_enabled())

    def test_enabled_when_configured(self):
        self.assertTrue(self.gdpr.is_enabled())

    def test_record_consent(self):
        record = self.gdpr.record_consent("user-1", True)
        self.assertTrue(record.granted)

    def test_has_consent(self):
        self.gdpr.record_consent("user-1", True)
        self.assertTrue(self.gdpr.has_consent("user-1"))

    def test_no_consent_without_record(self):
        self.assertFalse(self.gdpr.has_consent("unknown-user"))

    def test_withdraw_consent(self):
        self.gdpr.record_consent("user-1", True)
        self.assertTrue(self.gdpr.withdraw_consent("user-1"))
        self.assertFalse(self.gdpr.has_consent("user-1"))

    def test_create_access_request(self):
        req = self.gdpr.create_request("user-1", "access")
        self.assertEqual(req.request_type, "access")
        self.assertEqual(req.status, "pending")

    def test_fulfill_access_request(self):
        req = self.gdpr.create_request("user-1", "access")
        result = self.gdpr.fulfill_request(req.request_id)
        self.assertIn("data_held", result)

    def test_fulfill_erasure_request(self):
        self.gdpr.record_consent("user-1", True)
        req = self.gdpr.create_request("user-1", "erasure")
        result = self.gdpr.fulfill_request(req.request_id)
        self.assertEqual(result["status"], "erased")

    def test_fulfill_portability_request(self):
        self.gdpr.record_consent("user-1", True)
        req = self.gdpr.create_request("user-1", "portability")
        result = self.gdpr.fulfill_request(req.request_id)
        self.assertIn("data", result)
        self.assertEqual(result["format"], "json")

    def test_purge_old_data(self):
        import time
        self.gdpr.create_request("user-1", "access")
        purged = self.gdpr.purge_old_data()
        # Should not purge recent data
        self.assertEqual(purged, 0)


class TestSOC2ReportGenerator(unittest.TestCase):

    def setUp(self):
        from cherenkov.enterprise.soc2 import SOC2ReportGenerator
        self.soc2 = SOC2ReportGenerator()

    def test_get_controls_returns_defaults(self):
        controls = self.soc2.get_controls()
        self.assertGreater(len(controls), 0)

    def test_update_control(self):
        self.assertTrue(self.soc2.update_control("CC1.1", evidence="Policy document v2"))
        controls = self.soc2.get_controls()
        c = next(c for c in controls if c.id == "CC1.1")
        self.assertEqual(c.evidence, "Policy document v2")

    def test_update_nonexistent_control(self):
        self.assertFalse(self.soc2.update_control("GHOST", evidence="nope"))

    def test_generate_report(self):
        report = self.soc2.generate_report("TestOrg")
        self.assertEqual(report.organization, "TestOrg")
        self.assertIn("report_id", report.__dict__)
        self.assertGreater(len(report.controls), 0)

    def test_report_summary(self):
        report = self.soc2.generate_report("TestOrg")
        self.assertIn("total_controls", report.summary)
        self.assertIn("coverage_pct", report.summary)

    def test_list_reports(self):
        self.soc2.generate_report("TestOrg")
        reports = self.soc2.list_reports()
        self.assertEqual(len(reports), 1)

    def test_get_report(self):
        r1 = self.soc2.generate_report("TestOrg")
        r2 = self.soc2.get_report(r1.report_id)
        self.assertIsNotNone(r2)
        self.assertEqual(r2.organization, "TestOrg")

    def test_get_nonexistent_report(self):
        self.assertIsNone(self.soc2.get_report("ghost"))

    def test_export_report(self):
        r1 = self.soc2.generate_report("TestOrg")
        tmpdir = tempfile.mkdtemp()
        path = self.soc2.export_report(r1.report_id, tmpdir)
        self.assertTrue(os.path.exists(path))

    def test_get_compliance_summary(self):
        summary = self.soc2.get_compliance_summary()
        self.assertIn("security", summary)
        self.assertIn("availability", summary)

    def test_compliance_summary_coverage(self):
        from cherenkov.enterprise.soc2 import ControlStatus
        for c in self.soc2.get_controls():
            self.soc2.update_control(c.id, status=ControlStatus.OPERATIONAL)
        summary = self.soc2.get_compliance_summary()
        for cat in summary.values():
            self.assertEqual(cat["coverage_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
