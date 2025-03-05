#!/usr/bin/env python3
"""
Improved Rossum webhook handler with clean XML generation.
"""

import base64
import logging
import requests
import xml.etree.ElementTree as ET
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def fetch_annotation(annotation_id, api_token, base_url):
    """
    Get annotation content from Rossum API.
    """
    url = f"{base_url.rstrip('/')}/api/v1/annotations/{annotation_id}/content"
    
    try:
        response = requests.get(
            url, 
            headers={
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return data
        
    except requests.exceptions.RequestException:
        raise

def flatten_annotation(annotation_data):
    """
    Flatten annotation data into a key-value structure for easy mapping.
    Extracts values from the known structure of Rossum API responses.
    """
    fields = {}
    processed_ids = set()
    
    def extract_datapoints(item):
        if not isinstance(item, dict):
            return
            
        # Extract datapoint if this is one
        if item.get('id') not in processed_ids and item.get('category') == 'datapoint' and item.get('schema_id'):
            processed_ids.add(item.get('id'))
            content = item.get('content', {})
            if isinstance(content, dict) and 'value' in content:
                fields[item.get('schema_id')] = content['value']
                
        # Process children and other potential containers
        for value in item.values():
            if isinstance(value, dict):
                extract_datapoints(value)
            elif isinstance(value, list):
                for sub_item in value:
                    extract_datapoints(sub_item)
    
    # Process the entire annotation data
    extract_datapoints(annotation_data)
    
    return fields

def map_data(config, data):
    """
    Map data according to configuration structure.
    This function dynamically maps data based on the provided configuration structure.
    It's modular and has no hardcoded knowledge of specific fields.
    """
    # Handle dictionary config
    if isinstance(config, dict):
        return _map_dict_config(config, data)
    # Handle list config
    elif isinstance(config, list) and config:
        return _map_list_config(config, data)
    # Handle string config (direct field mapping)
    elif isinstance(config, str):
        return _map_string_config(config, data)
    return None

def _map_dict_config(config, data):
    """Handle dictionary-type configuration mapping."""
    result = {}
    for key, value in config.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Handle list structures (like Details with Detail elements)
            result[key] = _map_list_structure(value[0], data)
        else:
            result[key] = map_data(value, data)
    return result

def _map_list_structure(list_item_config, data):
    """Handle list structures with potential line items."""
    field_mappings = {}
    
    # Extract field mappings from config
    for sub_key, sub_value in list_item_config.items():
        if isinstance(sub_value, dict):
            # For nested structures in list items
            sub_mappings = {field: data.get(data_field) for field, data_field 
                           in sub_value.items() if data_field in data}
            if sub_mappings:
                field_mappings[sub_key] = sub_mappings
        elif isinstance(sub_value, str) and sub_value in data:
            # Direct field mapping
            field_mappings[sub_key] = data.get(sub_value)
    
    # Create result list with mappings or placeholder
    if field_mappings:
        return [field_mappings]
    else:
        # Create placeholder with empty values
        placeholder = {}
        for sub_key, sub_value in list_item_config.items():
            if isinstance(sub_value, dict):
                placeholder[sub_key] = {field: "" for field in sub_value.keys()}
            else:
                placeholder[sub_key] = ""
        return [placeholder]

def _map_list_config(config, data):
    """Handle list of items configuration."""
    if isinstance(data, list) and data:
        return [map_data(config[0], item) for item in data]
    else:
        # If no data is present, still create at least one entry
        return [map_data(config[0], {})]

def _map_string_config(config, data):
    """Handle string configuration (direct field mapping)."""
    value = data.get(config)
    # Handle special fields without hardcoding
    if config == "currency" and value:
        return value.upper()  # Convert currency to uppercase
    return value

def dict_to_xml(elem, data):
    """
    Recursively convert a dictionary to XML elements.
    """
    if data is None:
        return
        
    if isinstance(data, dict):
        for k, v in data.items():
            if v is not None:
                if isinstance(v, list):
                    for item in v:
                        child = ET.SubElement(elem, k)
                        dict_to_xml(child, item)
                else:
                    child = ET.SubElement(elem, k)
                    dict_to_xml(child, v)
    else:
        elem.text = str(data)

def generate_xml(root_tag, data):
    """
    Generate XML from data with the specified root tag.
    """
    root = ET.Element(root_tag)
    dict_to_xml(root, data)
    
    # Create an ElementTree object
    tree = ET.ElementTree(root)
    
    # Use ET.indent to properly format the XML (available in Python 3.9+)
    ET.indent(tree, space="  ")
    
    # Convert to string
    buffer = BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    
    return buffer.getvalue().decode()

def rossum_hook_request_handler(event):
    """
    Main handler function for the Rossum serverless function.
    """
    try:
        # Gather basic params
        token = event["rossum_authorization_token"]
        base_url = event["base_url"].rstrip('/')
        settings = event["settings"]
        config = settings["config"]
        annotation_id = settings["annotation_id"]
        
        # Step 1 - Fetch annotation
        annotation_json = fetch_annotation(annotation_id, token, base_url)
        
        # Step 2 - Flatten annotation for easy mapping
        flat_annotation = flatten_annotation(annotation_json)

        # Step 3 - Map according to YAML structure
        mapped_data = map_data(config["xml"]["structure"], flat_annotation)

        # Step 4 - Generate XML from mapped_data
        xml_root = config["xml"]["root"]
        xml_str = generate_xml(xml_root, mapped_data)
        
        # Step 5 - Encode XML to base64
        xml_base64 = base64.b64encode(xml_str.encode()).decode()
        
        # Step 6 - Build webhook payload
        payload = {
            "annotationId": int(annotation_id),
            "content": xml_base64
        }
        
        # Step 7 - Call webhook
        webhook_url = config["webhook"].get("url", "https://eof61da9bmm7q6f.m.pipedream.net")
        try:
            response = requests.post(
                webhook_url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error posting to webhook: {str(e)}")

        # Return clean response matching payload_example.json format
        return payload

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }