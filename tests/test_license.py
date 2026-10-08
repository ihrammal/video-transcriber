"""License texts: the non-commercial clause must be present in both."""

from __future__ import annotations

import io
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_english_license_is_non_commercial():
    text = io.open(ROOT / "resources" / "agreement_en.txt", encoding="utf-8").read()
    assert "NON-COMMERCIAL" in text
    assert "commercial purposes of any kind" in text
    assert "Copyright (c) Iman Rammal" in text


def test_arabic_license_is_non_commercial():
    text = io.open(ROOT / "resources" / "agreement_ar.txt", encoding="utf-8").read()
    assert "غير تجاري" in text
    assert "لأي غرض تجاري" in text
    assert "إيمان رمل" in text or "إيمان رمل" in text or "رمل" in text


def test_installer_ships_both_licenses():
    iss = io.open(ROOT / "installer" / "VidTrans.iss", encoding="utf-8").read()
    assert "agreement_en.txt" in iss
    assert "agreement_ar.txt" in iss
    assert "LicenseFile" in iss
