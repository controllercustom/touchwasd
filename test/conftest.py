def pytest_addoption(parser):
    parser.addoption(
        "--host",
        action="store",
        help="AtomS3 hostname or IP (e.g. touchwasd.local) for live device tests",
    )
