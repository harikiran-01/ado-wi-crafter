import json
import os
from operator import itemgetter

script_dir = os.path.dirname(__file__)
config_path = os.path.join(script_dir, 'config.json')
with open(config_path) as config:
    config_data = json.load(config)
ado_config, craft_config, data_config = itemgetter('ado api config',
                                                         'wi craft config',
                                                         'data source config')(config_data)