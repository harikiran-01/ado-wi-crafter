from .ado_wi_api_utils import log, AdoWiManager
from datetime import datetime
from operator import itemgetter


def _get_templatized_wi(wi_map, template_responses):
    """ Returns a new map with TEMPLATE_WI_VALUE in value or formattable_str in exp
    replaced with actual template value """
    TEMPLATE_WI_VALUE = 'TEMPLATE_WI_VALUE'
    return {field: template_responses[field] if val == TEMPLATE_WI_VALUE else 
    {template_responses[field]: next(iter(val.values()))} 
        if next(iter(val.keys())) == TEMPLATE_WI_VALUE
        else val for field, val in wi_map.items()}


def _reduce_exp(wi_data, exp):
    """ Reduces "{formattable_str:[]}" to the value of following expression based on data type of each element:
        str -> str
        int -> value of cell corresponding to the column number indexed from 0 for each row
        dict -> recursively formats str with %s replaced by elements of [] and returns the formatted value """
    for formattable_str, format_list in exp.items():
        final_val_list = [_reduce_exp(wi_data, item) if isinstance(item, dict) 
                          else wi_data[item] if isinstance(item, int) else item
                          for item in format_list]
        return formattable_str % tuple(final_val_list)


def _get_formatted_skel(wi_skel, wi_data):
    return {field: _reduce_exp(wi_data, exp) if isinstance(exp, dict) else exp
                      for field, exp in wi_skel.items()}


def craft_wis(ado_config, craft_config, wis_data):
    """ Crafts new WI's by receiving a list of lists with each WI data """
    log.info(f'WI Crafter started at {datetime.now()}')
    ado_wi_manager = AdoWiManager(ado_config)
    wi_type, wi_skel, wi_rels_skel, templ_wi_id = itemgetter('wi type',
                                                             'wi skeleton',
                                                             'wi rels skeleton',
                                                             'template wi id')(craft_config)
    wi_ref_skel = ado_wi_manager.get_wi_ref_map(wi_skel)
    wi_ref_templ_skel = _get_templatized_wi(wi_ref_skel, ado_wi_manager.get_wi_response(templ_wi_id))
    wi_ref_rels_skel = ado_wi_manager.get_wi_ref_rels(wi_rels_skel)
    for wi_data in wis_data:
        new_wi_map = _get_formatted_skel(wi_ref_templ_skel, wi_data)
        new_wi_rels = []
        for wi_ref_rel_skel in wi_ref_rels_skel:
            new_wi_rel = _get_formatted_skel(wi_ref_rel_skel, wi_data)
            new_wi_rels.append(new_wi_rel)
        ado_wi_manager.create_wi(new_wi_map, new_wi_rels, wi_type)
        log.info('\n')
        
