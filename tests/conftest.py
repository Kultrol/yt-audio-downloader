def pytest_configure(config):
    config.addinivalue_line("markers", "ffmpeg: tests that require ffmpeg")
