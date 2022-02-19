def test_load_platforms() -> None:
    from ipwndfu.device_platform import all_platforms

    assert len(all_platforms) > 1
