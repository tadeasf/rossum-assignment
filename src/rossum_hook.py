import base64
import json
import requests
import xml.dom.minidom
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_xml_from_data(annotation_data):
    """
    Create XML from annotation data according to the required format.
    
    Args:
        annotation_data (dict): The annotation data from Rossum API
    
    Returns:
        str: XML string in the required format
    """
    # Log the annotation data structure to understand what we're working with
    logger.info(f"Annotation data structure: {json.dumps(annotation_data)[:500]}...")
    
    # Create the XML document structure
    doc = xml.dom.minidom.getDOMImplementation().createDocument(None, "InvoiceRegisters", None)
    root = doc.documentElement
    
    # Create the main structure
    invoices = doc.createElement("Invoices")
    root.appendChild(invoices)
    
    payable = doc.createElement("Payable")
    invoices.appendChild(payable)
    
    # Try to extract field values based on the actual structure we're seeing in logs
    extracted_values = {}
    
    # The structure seems to have a "content" list with sections
    if "content" in annotation_data and isinstance(annotation_data["content"], list):
        for section in annotation_data["content"]:
            if "children" in section and isinstance(section["children"], list):
                for child in section["children"]:
                    schema_id = child.get("schema_id", "")
                    content_value = ""
                    
                    if "content" in child and isinstance(child["content"], dict) and "value" in child["content"]:
                        content_value = child["content"]["value"]
                    
                    # Map schema_id to our field names
                    if schema_id == "document_id":
                        extracted_values["InvoiceNumber"] = content_value
                    elif schema_id == "date_issue":
                        extracted_values["InvoiceDate"] = content_value
                    elif schema_id == "date_due":
                        extracted_values["DueDate"] = content_value
                    elif schema_id == "amount_total":
                        extracted_values["TotalAmount"] = content_value
                    elif schema_id == "iban":
                        extracted_values["Iban"] = content_value
                    elif schema_id == "amount_due":
                        extracted_values["Amount"] = content_value
                    elif schema_id == "currency":
                        extracted_values["Currency"] = content_value
                    elif schema_id == "sender_name":
                        extracted_values["Vendor"] = content_value
                    elif schema_id == "sender_address":
                        extracted_values["VendorAddress"] = content_value
    
    logger.info(f"Extracted values from structure: {extracted_values}")
    
    # Use extracted values directly, even if empty
    fields = {
        "InvoiceNumber": extracted_values.get("InvoiceNumber", ""),
        "InvoiceDate": extracted_values.get("InvoiceDate", ""),
        "DueDate": extracted_values.get("DueDate", ""),
        "TotalAmount": extracted_values.get("TotalAmount", ""),
        "Notes": "",
        "Iban": extracted_values.get("Iban", ""),
        "Amount": extracted_values.get("Amount", ""),
        "Currency": extracted_values.get("Currency", "").upper() if extracted_values.get("Currency") else "",
        "Vendor": extracted_values.get("Vendor", ""),
        "VendorAddress": extracted_values.get("VendorAddress", "")
    }
    
    # Format dates if available
    try:
        if fields["InvoiceDate"]:
            # Handle multiple date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y"]:
                try:
                    date_obj = datetime.strptime(fields["InvoiceDate"], fmt)
                    fields["InvoiceDate"] = date_obj.strftime("%Y-%m-%dT00:00:00")
                    break
                except ValueError:
                    continue
    except Exception as e:
        logger.error(f"Error formatting invoice date: {e}")
    
    try:
        if fields["DueDate"]:
            # Handle multiple date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y"]:
                try:
                    date_obj = datetime.strptime(fields["DueDate"], fmt)
                    fields["DueDate"] = date_obj.strftime("%Y-%m-%dT00:00:00")
                    break
                except ValueError:
                    continue
    except Exception as e:
        logger.error(f"Error formatting due date: {e}")
    
    # Create and append elements
    for field_name, field_value in fields.items():
        element = doc.createElement(field_name)
        text = doc.createTextNode(str(field_value) if field_value is not None else "")
        element.appendChild(text)
        payable.appendChild(element)
    
    # Create details section
    details = doc.createElement("Details")
    payable.appendChild(details)
    
    # Search for line items in the annotation data
    line_items_data = []
    if "content" in annotation_data and isinstance(annotation_data["content"], list):
        for section in annotation_data["content"]:
            if "children" in section and isinstance(section["children"], list):
                for child in section["children"]:
                    # Look for line_items schema_id
                    if child.get("schema_id") == "line_items" and "children" in child:
                        for line_item in child.get("children", []):
                            item_data = {"amount": "", "quantity": "", "description": ""}
                            if "children" in line_item:
                                for field in line_item["children"]:
                                    schema_id = field.get("schema_id", "")
                                    if schema_id == "item_amount_total" and "content" in field:
                                        item_data["amount"] = field["content"].get("value", "")
                                    elif schema_id == "item_quantity" and "content" in field:
                                        item_data["quantity"] = field["content"].get("value", "")
                                    elif schema_id == "item_desc" and "content" in field:
                                        item_data["description"] = field["content"].get("value", "")
                            line_items_data.append(item_data)
    
    logger.info(f"Extracted {len(line_items_data)} line items")
    
    # If no line items found, still create at least one empty detail
    if not line_items_data:
        line_items_data = [{"amount": "", "quantity": "", "description": ""}]
        logger.warning("No line items found in annotation data")
    
    # Add line items to the details section
    for item_data in line_items_data:
        detail = doc.createElement("Detail")
        details.appendChild(detail)
        
        item_fields = {
            "Amount": item_data.get("amount", ""),
            "AccountId": "",
            "Quantity": item_data.get("quantity", ""),
            "Notes": item_data.get("description", "")
        }
        
        for field_name, field_value in item_fields.items():
            element = doc.createElement(field_name)
            text = doc.createTextNode(str(field_value) if field_value is not None else "")
            element.appendChild(text)
            detail.appendChild(element)
    
    # Return the XML as a properly indented string
    # Use toprettyxml for proper indentation
    pretty_xml = doc.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    
    # Fix potential issues with empty elements (convert <Notes></Notes> to <Notes/>)
    # Only if needed to match expected format
    pretty_xml = pretty_xml.replace("<Notes></Notes>", "<Notes/>")
    pretty_xml = pretty_xml.replace("<AccountId></AccountId>", "<AccountId/>")
    
    return pretty_xml

def get_annotation_content(annotation_id, api_token, base_url):
    """
    Get annotation content from Rossum API.
    
    Args:
        annotation_id (str): The annotation ID
        api_token (str): Rossum API token
        base_url (str): Base URL for the Rossum API
    
    Returns:
        dict: The annotation content data
    """
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    # Make sure base_url doesn't end with a slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    url = f"{base_url}/api/v1/annotations/{annotation_id}/content"
    logger.info(f"Requesting annotation content from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching annotation content: {response.status_code} - {response.text}")
    
    return response.json()

def prepare_postbin_payload(annotation_id, xml_content):
    """
    Prepare the PostBin payload with base64 encoded XML.
    
    Args:
        annotation_id (str): The original annotation ID
        xml_content (str): The XML content
    
    Returns:
        dict: The payload for PostBin
    """
    # Base64 encode the XML content
    base64_content = base64.b64encode(xml_content.encode("utf-8")).decode("utf-8")
    
    # Create the payload
    payload = {
        "annotationId": annotation_id,
        "content": base64_content
    }
    
    return payload

def rossum_hook_request_handler(event):
    """
    Main handler function for the Rossum serverless function.
    This specific function name is required by Rossum.
    
    Args:
        event (dict): The event data
    
    Returns:
        dict: The response data
    """
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get the authentication token from the event
        api_token = event.get("rossum_authorization_token")
        if not api_token:
            return {
                "status": "error",
                "message": "No authorization token provided in the event"
            }
        
        # Get the base URL from the event
        base_url = event.get("base_url")
        if not base_url:
            return {
                "status": "error",
                "message": "No base URL provided in the event"
            }
        
        # Get annotation ID from settings
        settings = event.get("settings", {})
        annotation_id = settings.get("annotation_id")
        if not annotation_id:
            return {
                "status": "error",
                "message": "No annotation_id provided in settings"
            }
        
        # Get annotation content
        annotation_data = get_annotation_content(annotation_id, api_token, base_url)
        
        # Convert to XML
        xml_content = create_xml_from_data(annotation_data)
        
        # Log the XML for debugging
        logger.info(f"Generated XML: {xml_content[:500]}...")
        
        # Prepare the PostBin payload
        payload = prepare_postbin_payload(annotation_id, xml_content)
        
        # Get webhook URL from settings if provided, otherwise use default PostBin
        webhook_url = settings.get("webhook_url", "https://www.postb.in/1741019582850-7957228925079")
        
        # Try to send directly to the webhook (might work from Rossum environment to Rossum webhook)
        success = False
        response_text = ""
        try:
            logger.info(f"Attempting to post directly to webhook: {webhook_url}")
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            success = response.status_code == 200
            response_text = response.text
            logger.info(f"Webhook response: {response.status_code} - {response_text}")
        except Exception as e:
            logger.warning(f"Error posting to webhook directly: {str(e)}")
        
        # Return response with the correct payload structure matching existing payload.json
        return {
            "status": "success",
            "message": "Successfully processed annotation and generated XML payload",
            "webhookUrl": webhook_url,
            "webhookSuccess": success,
            "webhookResponse": response_text,
            "instructionsText": "Use test_postbin.py to send this to a webhook",
            
            # Main output - this should match the structure in payload.json exactly
            "annotationId": payload["annotationId"],
            "content": payload["content"]
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing annotation: {str(e)}"
        } 