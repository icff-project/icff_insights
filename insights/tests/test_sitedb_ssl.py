"""PR-Foundry fork patch (framework) — the Insights "Site DB" data source must
not force DB certificate verification on a containerised (self-signed) MariaDB.

Regression: SiteDB.create_engine must derive ssl_verify_cert from
frappe.conf.db_ssl_ca (mirroring Frappe core), NOT from developer_mode — which
forced verification on every non-dev containerised site and produced
CERTIFICATE_VERIFY_FAILED. We assert the value passed to the engine factory, so
the test needs no live DB / SSL.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

import insights.insights.doctype.insights_data_source.sources.frappe_db as frappe_db_mod
from insights.insights.doctype.insights_data_source.sources.frappe_db import SiteDB

_CREDS = {
    "username": "u",
    "password": "p",
    "database": "d",
    "host": "h",
    "port": "3306",
}


class TestSiteDBSSLVerify(FrappeTestCase):
    def _captured_verify(self):
        # create_engine doesn't touch self; __new__ avoids a data-source doc.
        with patch.object(frappe_db_mod, "get_sqlalchemy_engine") as m:
            SiteDB.__new__(SiteDB).create_engine(_CREDS)
            return m.call_args.kwargs["ssl_verify_cert"]

    def test_no_verification_without_db_ssl_ca(self):
        # Containerised default: no CA -> must NOT verify (self-signed cert).
        with patch.dict(frappe.conf, {"db_ssl_ca": None, "developer_mode": 0}):
            self.assertFalse(self._captured_verify())

    def test_verifies_when_db_ssl_ca_configured(self):
        with patch.dict(frappe.conf, {"db_ssl_ca": "/etc/ca.pem", "developer_mode": 0}):
            self.assertTrue(self._captured_verify())

    def test_developer_mode_no_longer_governs_verification(self):
        # The old bug keyed off developer_mode; it must now be irrelevant.
        with patch.dict(frappe.conf, {"db_ssl_ca": None, "developer_mode": 1}):
            self.assertFalse(self._captured_verify())
