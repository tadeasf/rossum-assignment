#!/usr/bin/env python3
"""
Script to validate the XML from payload.json against the expected schema.
This reads the base64-encoded content from payload.json, decodes it,
and verifies it matches the expected XML structure.
"""

import sys
import json
import base64
import xml.dom.minidom
import argparse

# Expected XML structure - the elements and their hierarchy we expect to see
EXPECTED_XML_ELEMENTS = [
    'InvoiceRegisters',
    'InvoiceRegisters/Invoices',
    'InvoiceRegisters/Invoices/Payable',
    'InvoiceRegisters/Invoices/Payable/InvoiceNumber',
    'InvoiceRegisters/Invoices/Payable/InvoiceDate',
    'InvoiceRegisters/Invoices/Payable/DueDate',
    'InvoiceRegisters/Invoices/Payable/TotalAmount',
    'InvoiceRegisters/Invoices/Payable/Notes',
    'InvoiceRegisters/Invoices/Payable/Iban',
    'InvoiceRegisters/Invoices/Payable/Amount',
    'InvoiceRegisters/Invoices/Payable/Currency',
    'InvoiceRegisters/Invoices/Payable/Vendor',
    'InvoiceRegisters/Invoices/Payable/VendorAddress',
    'InvoiceRegisters/Invoices/Payable/Details',
    'InvoiceRegisters/Invoices/Payable/Details/Detail',
    'InvoiceRegisters/Invoices/Payable/Details/Detail/Amount',
    'InvoiceRegisters/Invoices/Payable/Details/Detail/AccountId',
    'InvoiceRegisters/Invoices/Payable/Details/Detail/Quantity',
    'InvoiceRegisters/Invoices/Payable/Details/Detail/Notes'
]

def load_payload_json(file_path):
    """
    Load and parse the payload.json file
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)

def decode_base64_content(payload_data):
    """
    Extract and decode base64 content from payload data
    """
    # Check if content field exists
    if 'content' not in payload_data:
        print("Error: No 'content' field found in payload.json")
        sys.exit(1)
    
    try:
        # Get the base64 encoded content
        base64_content = payload_data['content']
        
        # Decode the base64 content to get the XML
        xml_content = base64.b64decode(base64_content).decode('utf-8')
        return xml_content
    except Exception as e:
        print(f"Error decoding base64 content: {e}")
        sys.exit(1)

def get_element_structure(dom):
    """Extract element structure from DOM"""
    result = []
    
    def process_node(node, depth=0, path=""):
        if node.nodeType == node.ELEMENT_NODE:
            current_path = f"{path}/{node.nodeName}" if path else node.nodeName
            result.append(current_path)
            for child in node.childNodes:
                process_node(child, depth + 1, current_path)
    
    # Start with the document element
    process_node(dom.documentElement)
    return result

def validate_xml_structure(xml_content):
    """
    Validate XML structure against expected elements
    """
    try:
        # Parse the XML
        dom = xml.dom.minidom.parseString(xml_content)
        
        # Get the actual element structure
        actual_elements = get_element_structure(dom)
        
        # Convert to sets for comparison
        actual_set = set(actual_elements)
        expected_set = set(EXPECTED_XML_ELEMENTS)
        
        # Check for missing elements
        missing = expected_set - actual_set
        if missing:
            print("Missing elements in XML:", missing)
            return False
        
        # Check for any unexpected elements in the core structure
        # Note: We're only checking the core structure, not every detail element
        # as there can be multiple detail elements
        unexpected = set()
        for elem in actual_set:
            # If element doesn't start with any expected paths
            if not any(elem == expected or elem.startswith(expected + '/Detail') 
                       for expected in expected_set):
                unexpected.add(elem)
        
        if unexpected:
            print("Unexpected elements in XML:", unexpected)
            return False
        
        return True
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return False

def validate_currency_uppercase(xml_content):
    """Check if Currency element contains uppercase value"""
    try:
        dom = xml.dom.minidom.parseString(xml_content)
        currency_elements = dom.getElementsByTagName('Currency')
        
        if currency_elements:
            currency_value = currency_elements[0].firstChild.nodeValue
            if currency_value and currency_value.upper() != currency_value:
                print(f"Warning: Currency value '{currency_value}' is not uppercase")
                return False
        return True
    except Exception as e:
        print(f"Error checking currency: {e}")
        return False

def validate_xml_indentation(xml_content):
    """Check if XML is properly indented"""
    try:
        # Parse, then regenerate with pretty printing to check indentation
        dom = xml.dom.minidom.parseString(xml_content)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Compare structure (ignoring whitespace differences)
        original_lines = [line.strip() for line in xml_content.splitlines() if line.strip()]
        pretty_lines = [line.strip() for line in pretty_xml.splitlines() if line.strip()]
        
        # If the lengths are very different, indentation is likely wrong
        if abs(len(original_lines) - len(pretty_lines)) > 3:
            print("Warning: XML doesn't appear to be properly indented")
            print(f"Original has {len(original_lines)} non-empty lines, properly indented would have {len(pretty_lines)}")
            return False
        return True
    except Exception as e:
        print(f"Error checking indentation: {e}")
        return False

def print_xml_data(xml_content, max_lines=20):
    """Print the beginning of the XML content"""
    lines = xml_content.splitlines()
    print("\n=== XML CONTENT (first few lines) ===")
    for i, line in enumerate(lines):
        if i < max_lines:
            print(line)
        else:
            print(f"... (showing {max_lines} of {len(lines)} lines)")
            break

def main():
    parser = argparse.ArgumentParser(description='Validate XML from payload.json against expected schema')
    parser.add_argument('--payload', default='payload.json', help='Path to payload.json file')
    parser.add_argument('--show-xml', action='store_true', help='Show the decoded XML content')
    parser.add_argument('--verbose', action='store_true', help='Show verbose output')
    
    args = parser.parse_args()
    
    print(f"Loading payload data from {args.payload}...")
    payload_data = load_payload_json(args.payload)
    
    print("Extracting and decoding base64 content...")
    xml_content = decode_base64_content(payload_data)
    
    if args.show_xml or args.verbose:
        print_xml_data(xml_content)
    
    print("\n=== VALIDATING XML STRUCTURE ===")
    structure_valid = validate_xml_structure(xml_content)
    print(f"XML structure valid: {structure_valid}")
    
    print("\n=== VALIDATING CURRENCY FORMAT ===")
    currency_valid = validate_currency_uppercase(xml_content)
    print(f"Currency format valid: {currency_valid}")
    
    print("\n=== VALIDATING XML INDENTATION ===")
    indentation_valid = validate_xml_indentation(xml_content)
    print(f"XML indentation valid: {indentation_valid}")
    
    # Overall validation result
    overall_valid = structure_valid and currency_valid and indentation_valid
    print("\n=== VALIDATION RESULT ===")
    print(f"Overall validation: {'PASSED' if overall_valid else 'FAILED'}")
    
    return 0 if overall_valid else 1

if __name__ == "__main__":
    sys.exit(main()) 