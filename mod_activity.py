import base64

from .model import ModelActivity
from .setup import *


class ModuleActivity(PluginModuleBase):
    
    def __init__(self, P):
        super(ModuleActivity, self).__init__(P, name='activiy')
        self.db_default = {
            f'{self.name}_db_version' : '1',
        }
        self.web_list_model = ModelActivity
