import unittest
from cherenkov.core.devices import DeviceClass, VLMTier, DeviceInfo


class TestDeviceClass(unittest.TestCase):
    def test_device_class_values(self):
        self.assertIn(DeviceClass.DESKTOP, DeviceClass)
        self.assertIn(DeviceClass.MOBILE, DeviceClass)
        self.assertIn(DeviceClass.TABLET, DeviceClass)
        self.assertIn(DeviceClass.SERVER, DeviceClass)
        self.assertIn(DeviceClass.UNKNOWN, DeviceClass)


class TestVLMTier(unittest.TestCase):
    def test_vlm_tier_values(self):
        self.assertIn(VLMTier.NONE, VLMTier)
        self.assertIn(VLMTier.LOCAL, VLMTier)
        self.assertIn(VLMTier.CLOUD, VLMTier)


class TestDeviceInfo(unittest.TestCase):
    def test_device_info_defaults(self):
        di = DeviceInfo()
        self.assertIsInstance(di.device_class, DeviceClass)
        self.assertIsInstance(di.vlm_tier, VLMTier)
        self.assertIsInstance(di.has_gpu, bool)
        self.assertIsInstance(di.has_docker, bool)
        self.assertIsInstance(di.cpu_count, int)
        self.assertGreater(di.cpu_count, 0)

    def test_to_dict(self):
        di = DeviceInfo()
        d = di.to_dict()
        self.assertIn("device_class", d)
        self.assertIn("vlm_tier", d)
        self.assertIn("has_gpu", d)
        self.assertIn("has_docker", d)
        self.assertIn("os_name", d)
        self.assertIn("cpu_count", d)
        self.assertIn("memory_gb", d)
        self.assertIsInstance(d["device_class"], str)

    def test_detect_vlm_tier_default(self):
        tier = DeviceInfo._detect_vlm_tier()
        self.assertIsInstance(tier, VLMTier)
