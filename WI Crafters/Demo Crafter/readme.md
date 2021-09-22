[[_TOC_]]
# Demo WI Crafter
This tool is an extension of [ado-wi-utils](../../ado_wi_utils/) package to demonstrate creation of WIs and acts as a template for Work Item Creation using the package.

### Overview
**Acronyms used**: WI(s) - Work Item(s), REL(s) - Work Item Relation(s), REF(s) - Reference(s)  
  
This tool helps to craft work items by fetching:  
- **static data** from api response of existing ADO work item template(designed specifically for providing a skeletal structure for the new work items).  
- **dynamic data** from a data source. Current setup in [data_utils.py](data_utils.py) utilizes excel as a data source with each row containing the additional dynamic data needed for the new work items.

**Note**: *Relations cannot be scraped from the api response, so they have to be provided explicity*

### Getting Started
The following setup illustrates a demo of this tool. 

Agenda of the demo: Create work items for tracking a task to search something on a Search Engine.

#### Configuration of tool
This tool uses [config.json](config.json) as the configuration data for creating WIs.  
Number of WIs = Number of rows in excel sheet.

**Note**: *The excel workbook must have only one sheet for the script to load data from the correct sheet.*  

The fields in the config file are defined as follows:  
- `ado api config` - Contains config of ADO API operations. The keys in this config are defined as follows:
  - `org` - The ADO organization
  - `proj` - The Project in ADO organization
  - `api version` - The version of API for REST calls
  - `user id` - User ID of the WI creator
  - `pat` - PAT of the WI creator
  - `wi headers` - headers for the WI API calls
  - `attch default name` - overrides attachment name with default name for attachments across WIs if value is not blank

- `data source config` - Contains config of the data source which contains WI values. The keys in this config are defined as follows:
  - `excel file path` - The file path of excel which contains data

- `wi craft config` - Contains config of skeletal WI details. The keys in this config are defined as follows:
  - `wi type` - Type of WI's to be created(Ex: Bug, Task, Feature etc)
  - `wi skeleton` - The signature of this variable is `{field: exp}`
    - `field` - display name of field in ADO WI. Crafter implicitly calls `get_wi_ref_map(wi_map)` in [ado_wi_api_utils.py](../../ado_wi_utils/ado_wi_api_utils.py) that accepts wi_map with display-named fields and returns wi_map with reference-named fields
    - `exp` - `{formattable_str: [formatting values]}` or `direct_str`
      - `formattable_str` - String containing `%s` as placeholder. If its equal to "TEMPLATE_WI_VALUE", the formattable_str is expected to be provided as value for the corresponding field in template WI. (This "TEMPLATE_WI_VALUE" is useful especially for populating "Description" field of WI's as it reduces the overhead of writing html/markup syntax from scratch and instead use the formatting already available in the template WI).
      - `[formatting values]` - list of int/string/dict<string,list> to replace occurence of `%s` with elements of list in order from start to end.  To support data grouping, the `[formatting values]` can nest `exp`.  
      Based on `[formatting values]` item datatype, `exp` gets reduced to the following expressions:  
      `String` -> String   
      `Integer` -> Value of cell in excel sheet corresponding to the column number indexed from 0 for each row in excel data  
      `exp` -> Recursively reduces `formattable_str` to a formatted string by replacing occurences of %s in the order of values in `[formatting values]`  
    - `direct_str` - The constant value of the WI field  
  - `wi rels skeleton` - The signature of this variable is `[{field: exp}]`. Its a list of maps for each relations. Each map must contain `wi_rel_type` and `wi_rel_url` as mandatory fields with `wi_rel_comment` as optional field

    - `wi_rel_type` - Attachments and WI links in ADO are termed as Relations. The relation type expects the display name of the relation ex: Parent, Child etc. Crafter implicitly calls `get_wi_ref_rels(wi_rels)` in [ado_wi_api_utils.py](../../ado_wi_utils/ado_wi_api_utils.py) that accepts wi_rels with display-named relation types and returns wi_map with reference-named relation types.

    - `wi_rel_url` - Accepts WI url for WI links such as (Parent, Duplicate, etc). If the relation type is file attachment, the wi_rel_url can either be the attachmentstore url of the file or the absolute filepath in the local machine. The tool detects a url by checking if `wi_rel_url` starts with 'http'. If the `wi_rel_url` doesn't start with 'http', its treated as a filepath and the file is automatically uploaded to attachmentstore and the resulting url is implicitly assigned to `wi_rel_url`
    - `wi_rel_comment` - Optional comment about the operation.

  - `template wi id` - The ID of a template work item in ADO with values set for at least all the fields where `exp` or first `formattable_str` is equal to "TEMPLATE_WI_VALUE" in `wi skeleton`.     


#### Running the tool
Run [main.py](main.py)
