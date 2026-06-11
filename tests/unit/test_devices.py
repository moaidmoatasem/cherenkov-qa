from cherenkov.core.devices import DeviceClass, VLMTier, DeviceInfo


def test_device_class_values():
    assert DeviceClass.DESKTOP in DeviceClass
    assert DeviceClass.MOBILE in DeviceClass
    assert DeviceClass.TABLET in DeviceClass
    assert DeviceClass.SERVER in DeviceClass
    assert DeviceClass.UNKNOWN in DeviceClass


def test_vlm_tier_values():
    assert VLMTier.NONE in VLMTier
    assert VLMTier.LOCAL in VLMTier
    assert VLMTier.CLOUD in VLMTier


def test_device_info_defaults():
    di = DeviceInfo()
    assert isinstance(di.device_class, DeviceClass)
    assert isinstance(di.vlm_tier, VLMTier)
    assert isinstance(di.has_gpu, bool)
    assert isinstance(di.has_docker, bool)
    assert isinstance(di.cpu_count, int)
    assert di.cpu_count > 0


def test_to_dict():
    di = DeviceInfo()
    d = di.to_dict()
    assert "device_class" in d
    assert "vlm_tier" in d
    assert "has_gpu" in d
    assert "has_docker" in d
    assert "os_name" in d
    assert "cpu_count" in d
    assert "memory_gb" in d
    assert isinstance(d["device_class"], str)


def test_detect_vlm_tier_default():
    tier = DeviceInfo._detect_vlm_tier()
    assert isinstance(tier, VLMTier)
