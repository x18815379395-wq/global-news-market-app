from tools import doctor


def test_doctor_collect_status(monkeypatch):
    sample_cfg = {
        "crawler": {
            "user_agent": "UA",
            "timeout_sec": 5,
            "per_domain_min_interval_sec": 0.1,
            "rss": {
                "WSJ": {"enabled": True, "feeds": ["https://example.com/wsj"]},
                "Bloomberg": {"enabled": True, "feeds": ["https://example.com/bbg"]},
                "FinancialTimes": {"enabled": True, "feeds": ["https://example.com/ft"]},
            },
            "social": {
                "TruthSocial": {"enabled": True, "handles": ["realDonaldTrump"]},
                "X": {"enabled": True, "handles": ["realDonaldTrump"]},
            },
        },
        "playwright": {"browser": "firefox", "headless": True, "wait_after_load_sec": 0.1},
        "healthcheck": {"rss_sample_limit": 1, "truth_sample_limit": 1, "x_sample_limit": 1},
    }
    selectors_cfg = {
        "truth": {"article": "article", "link_contains": "/post/", "time": "time"},
        "x": {"article": "article", "link_contains": "/status/", "time": "time"},
    }

    def fake_load_yaml(path):
        return selectors_cfg if "selectors" in path else sample_cfg

    monkeypatch.setattr(doctor, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(doctor, "check_rss", lambda *args, **kwargs: (True, ["rss ok"]))
    monkeypatch.setattr(doctor, "check_truth", lambda *args, **kwargs: (True, ["truth ok"]))
    monkeypatch.setattr(doctor, "check_x", lambda *args, **kwargs: (True, ["x ok"]))

    status = doctor.collect_status()

    assert status["rss"] == {"WSJ": True, "Bloomberg": True, "Financial Times": True}
    assert status["truth"] == {"realDonaldTrump": True}
    assert status["twitter_ready"] is True
    assert "rss ok" in status["details"]
    assert "truth ok" in status["details"]
    assert "x ok" in status["details"]
