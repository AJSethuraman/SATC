from occam_template_desk.core.outlook import OutlookDraftService


def test_outlook_fallback_does_not_crash_when_unavailable(tmp_path):
    service = OutlookDraftService()
    status = service.fallback_status(tmp_path, "Unavailable in test")
    assert status["created"] is False
    assert (tmp_path / "outlook_status.json").exists()
