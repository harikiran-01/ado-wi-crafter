import sys
import os
MODULE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if MODULE_DIR not in sys.path:
    sys.path.append(os.path.join(MODULE_DIR))
from resolve_config import ado_config, craft_config, data_config
from ado_wi_utils.craft_wi import craft_wis
from data_utils import get_all_rows


def main():
    wis_data = get_all_rows(data_config['excel file path'])
    craft_wis(ado_config=ado_config, craft_config=craft_config, wis_data=wis_data)


if __name__ == '__main__':
    main()
