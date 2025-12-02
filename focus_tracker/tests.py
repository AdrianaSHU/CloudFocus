from django.test import TestCase
from django.contrib.auth.models import User
from .models import Device

class DeviceModelTest(TestCase):
    def setUp(self):
        self.device = Device.objects.create(name="Test Pi")

    def test_device_creation(self):
        """Test that a device gets a UUID and API Key automatically"""
        self.assertTrue(self.device.device_id)
        self.assertTrue(self.device.api_key)
        self.assertEqual(str(self.device), "Test Pi")

class PublicViewsTest(TestCase):
    def test_home_page_status(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')