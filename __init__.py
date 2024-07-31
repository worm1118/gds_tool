import os

from support import SupportSC

try:
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'gdrive.py')):
        from .gdrive import SSGDrive
    else:
        SSGDrive = SupportSC.load_module_f(__file__, 'gdrive').SSGDrive

    if os.path.exists(os.path.join(os.path.dirname(__file__), 'activity.py')):
        from .activity import GDSActivity
    else:
        GDSActivity = SupportSC.load_module_f(__file__, 'activity').GDSActivity
  
except:
    pass