import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import launch_app


class StartupTests(unittest.TestCase):
    def test_dll_import_error_returns_failure_report_without_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            report=Path(directory)/'result.json'
            with patch.object(launch_app.sys,'argv',['Descargador.exe','--check','--diagnostic-report',str(report)]), \
                 patch.object(launch_app,'load_application',side_effect=ImportError('DLL load failed while importing QtCore')):
                self.assertEqual(launch_app.main(),1)
            result=json.loads(report.read_text(encoding='utf-8'))
            self.assertFalse(result['ok'])
            self.assertEqual(result['error'],'ImportError')
            self.assertIn('QtCore',result['detail'])

    def test_successful_packaged_diagnostic_reports_version(self):
        with tempfile.TemporaryDirectory() as directory:
            report=Path(directory)/'result.json'
            application=Mock()
            with patch.object(launch_app.sys,'argv',['Descargador.exe','--check','--diagnostic-report',str(report)]), \
                 patch.object(launch_app,'load_application',return_value=application):
                self.assertEqual(launch_app.main(),0)
            self.assertTrue(json.loads(report.read_text())['ok'])
            application.main.assert_called_once()


if __name__ == '__main__':
    unittest.main()
