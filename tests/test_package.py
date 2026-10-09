from importlib.metadata import distribution

import rtc_infoworks_icm


def test_core_package_identity() -> None:
    package = distribution("rtc-infoworks-icm")

    assert package.metadata["Name"] == "rtc-infoworks-icm"
    assert rtc_infoworks_icm.RTCCreator.__module__ == "rtc_infoworks_icm.creator"
