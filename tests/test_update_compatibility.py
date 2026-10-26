"""The renamed maintenance installer remains visible to existing users."""
import io
import json
import pytest


@pytest.mark.parametrize("installed,available", [("1.3.0", True), ("1.3.1", False)])
def test_update_feed_accepts_renamed_installer(monkeypatch, installed, available):
    import update_checker
    download = 'https://github.com/ihrammal/video-transcriber/releases/download/v1.3.1/AccessibleMediaTranscriber_Setup_1.3.1.exe'
    feed = {'tag_name': 'v1.3.1', 'body': 'Maintenance fixes',
            'assets': [{'name': 'SHA256SUMS-1.3.1.txt'},
                       {'name': 'AccessibleMediaTranscriber_Setup_1.3.1.exe', 'browser_download_url': download}]}
    monkeypatch.setattr(update_checker, 'APP_VERSION', installed)
    monkeypatch.setattr(update_checker.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(json.dumps(feed).encode()))
    result = update_checker.check_for_update()
    assert result['available'] is available
    assert result['download_url'] == download
    assert result['latest'] == '1.3.1'


def test_startup_check_respects_saved_choice_and_daily_interval(profile, monkeypatch):
    import update_checker
    monkeypatch.setattr(update_checker.time, 'time', lambda: 200000)
    update_checker.save_settings({'auto_check': False, 'last_check': 0})
    assert not update_checker.should_auto_check()
    update_checker.set_auto_check(True)
    assert update_checker.should_auto_check()
    update_checker.mark_checked()
    assert not update_checker.should_auto_check()
