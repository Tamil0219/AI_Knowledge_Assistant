import unittest
from unittest.mock import MagicMock, patch

# ensure project path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

class TestImageUploadKeys(unittest.TestCase):
    """Ensure upload widget keys can be namespaced to avoid duplicates."""

    def setUp(self):
        # prepare a fake streamlit module with just the functions we need
        self.st_mock = MagicMock()
        # file_uploader should simply return None
        self.st_mock.file_uploader.return_value = None
        self.st_mock.button.return_value = False
        # make columns return a tuple of mocks so unpacking works
        self.st_mock.columns.side_effect = lambda n: tuple(MagicMock() for _ in range(n))
        sys.modules['streamlit'] = self.st_mock
        # create a simple session_state object that supports both dict
        # semantics and attribute access
        class DummyState(dict):
            def __getattr__(self, name):
                return self.get(name)
            def __setattr__(self, name, value):
                self[name] = value
        self.st_mock.session_state = DummyState()
        # stub out various third-party packages used by imports
        for pkg in ['PIL', 'PIL.Image', 'pandas', 'cv2', 'numpy', 'razorpay']:
            if pkg not in sys.modules:
                sys.modules[pkg] = MagicMock()
        # ensure frontend modules reload so they pick up our fresh stub
        for mod in ['frontend.image_upload', 'frontend.dashboard', 'frontend.style_selection']:
            if mod in sys.modules:
                del sys.modules[mod]

    def tearDown(self):
        # remove our stub so it doesn't leak into other tests
        sys.modules.pop('streamlit', None)

    def test_default_keys(self):
        import importlib
        import frontend.image_upload as iu_module
        importlib.reload(iu_module)
        image_upload_page = iu_module.image_upload_page
        # call with no prefix
        image_upload_page()
        # file_uploader should have been called with correct key
        self.st_mock.file_uploader.assert_called_with(
            "Choose an image",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            key='image_uploader'
        )

    def test_prefixed_keys(self):
        import importlib
        import frontend.image_upload as iu_module
        importlib.reload(iu_module)
        image_upload_page = iu_module.image_upload_page
        image_upload_page(key_prefix='history_')
        self.st_mock.file_uploader.assert_called_with(
            "Choose an image",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            key='history_image_uploader'
        )

    def test_two_calls_different_prefixes(self):
        import importlib
        import frontend.image_upload as iu_module
        importlib.reload(iu_module)
        image_upload_page = iu_module.image_upload_page
        image_upload_page(key_prefix='a_')
        image_upload_page(key_prefix='b_')
        # last call should show prefix b in last invocation
        self.assertEqual(self.st_mock.file_uploader.call_args_list[-1][1]['key'], 'b_image_uploader')

if __name__ == '__main__':
    unittest.main()
