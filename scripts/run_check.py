import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from services.notification_service import check_and_send_reminders

APP_PATH = os.path.join(ROOT, 'app.py')

spec = importlib.util.spec_from_file_location('app', APP_PATH)
appmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(appmod)

if __name__ == '__main__':
    print('🔎 Running check_and_send_reminders once...')
    check_and_send_reminders(appmod.app)
    print('✅ Done.')
