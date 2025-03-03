#!/usr/bin/env python3
import requests
import json
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_annotations(api_token, base_url, limit=30):
    """
    List annotations from Rossum API.
    """
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    # Make sure base_url doesn't end with a slash
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    url = f"{base_url}/api/v1/annotations?limit={limit}&ordering=-created_at"
    logger.info(f"Listing annotations from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Error listing annotations: {response.status_code} - {response.text}")
    
    data = response.json()
    
    # Log the structure of the response
    logger.info(f"API response structure: {list(data.keys())}")
    logger.info(f"Number of results in response: {len(data.get('results', []))}")
    
    if 'results' in data and data['results']:
        # Log the first result to understand structure
        first_result = data['results'][0]
        logger.info(f"First result keys: {list(first_result.keys())}")
        
        # Show document field structure if exists
        if 'document' in first_result:
            logger.info(f"Document field type: {type(first_result['document'])}")
            if isinstance(first_result['document'], dict):
                logger.info(f"Document field keys: {list(first_result['document'].keys())}")
            elif isinstance(first_result['document'], str):
                logger.info(f"Document field value: {first_result['document']}")
    
    return data.get("results", [])

def get_annotation_content(annotation_id, api_token, base_url):
    """
    Get annotation content from Rossum API.
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

def find_annotation_by_document_id(document_id, api_token, base_url):
    """
    Find the annotation ID for a specific document ID.
    """
    annotations = get_annotations(api_token, base_url)
    
    logger.info(f"Found {len(annotations)} recent annotations")
    
    # Debug the structure of the first annotation to understand the format
    if annotations:
        logger.info(f"First annotation structure sample: {json.dumps(annotations[0])[:200]}...")
    
    # First, try direct document ID match
    for annotation in annotations:
        # Make sure annotation is a dictionary
        if not isinstance(annotation, dict):
            logger.warning(f"Unexpected annotation format (not a dict): {type(annotation)}")
            continue
            
        # Handle different possible structures for document ID
        doc_id = None
        ann_id = annotation.get("id")
        
        # Try different paths to find document ID
        if "document" in annotation:
            if isinstance(annotation["document"], dict):
                doc_id = annotation["document"].get("id")
            elif isinstance(annotation["document"], str):
                # If document is a URL, extract ID from the URL
                doc_id = annotation["document"].split("/")[-1] if "/" in annotation["document"] else annotation["document"]
                
        logger.info(f"Checking annotation {ann_id} with document ID {doc_id}")
        
        if doc_id and str(doc_id) == str(document_id):
            logger.info(f"Found direct match! Annotation ID: {ann_id} for document ID: {document_id}")
            return ann_id
    
    logger.info("No direct match found, checking document content...")
    
    # Then check content of each annotation
    for annotation in annotations:
        # Make sure annotation is a dictionary
        if not isinstance(annotation, dict):
            continue
            
        ann_id = annotation.get("id")
        
        try:
            logger.info(f"Fetching content for annotation {ann_id}")
            content = get_annotation_content(ann_id, api_token, base_url)
            
            # Check content for document_id field
            if "content" in content and isinstance(content["content"], list):
                for section in content["content"]:
                    if "children" in section and isinstance(section["children"], list):
                        for child in section["children"]:
                            schema_id = child.get("schema_id", "")
                            content_value = ""
                            
                            if "content" in child and isinstance(child["content"], dict) and "value" in child["content"]:
                                content_value = child["content"]["value"]
                            
                            if schema_id == "document_id" and content_value == str(document_id):
                                logger.info(f"Found match in content! Annotation ID: {ann_id} has document ID: {document_id}")
                                return ann_id
        except Exception as e:
            logger.error(f"Error checking annotation {ann_id}: {str(e)}")
    
    logger.warning(f"No annotation found for document ID: {document_id}")
    return None

def main():
    if len(sys.argv) < 4:
        print("Usage: python find_annotation.py <document_id> <api_token> <base_url>")
        sys.exit(1)
    
    document_id = sys.argv[1]
    api_token = sys.argv[2]
    base_url = sys.argv[3]
    
    try:
        print("\n=== SEARCHING FOR ANNOTATIONS ===")
        print(f"Document ID: {document_id}")
        print(f"Base URL: {base_url}")
        print("Retrieving annotations list...")
        
        # First try to find by document ID
        annotation_id = find_annotation_by_document_id(document_id, api_token, base_url)
        
        if annotation_id:
            print("\n=== MATCH FOUND ===")
            print(f"Document ID: {document_id}")
            print(f"Annotation ID: {annotation_id}")
            
            # Print example event for manual testing
            sample_event = {
                "request_id": "fdb4ade2-c0e2-425d-91aa-4e9d39d64952",
                "timestamp": "2025-03-03T16:36:15.498898Z",
                "hook": "https://test-company-tadeas.rossum.app/api/v1/hooks/603761",
                "action": "scheduled",
                "event": "invocation",
                "rossum_authorization_token": api_token,
                "base_url": base_url,
                "settings": {
                    "annotation_id": annotation_id
                },
                "secrets": {}
            }
            
            print("\n=== SAMPLE EVENT FOR TESTING ===")
            print(json.dumps(sample_event, indent=2))
            
        else:
            print("\n=== NO MATCH FOUND ===")
            print(f"Document ID: {document_id} not found in recent annotations")
            
            # List recent annotations to help the user
            annotations = get_annotations(api_token, base_url, limit=5)
            print("\n=== RECENT ANNOTATIONS ===")
            for ann in annotations:
                ann_id = ann.get("id", "Unknown")
                doc_ref = "Unknown"
                
                if "document" in ann:
                    if isinstance(ann["document"], dict):
                        doc_ref = ann["document"].get("id", "Unknown")
                    elif isinstance(ann["document"], str):
                        doc_ref = ann["document"].split("/")[-1] if "/" in ann["document"] else ann["document"]
                
                print(f"Annotation ID: {ann_id}, Document Reference: {doc_ref}")
            
            # Suggest manual approach
            print("\n=== NEXT STEPS ===")
            print("1. Check if your document ID is correct")
            print("2. Try using one of the recent annotation IDs directly")
            print("3. Check the Rossum UI to find the correct annotation ID")
            
            # Print example event with manual annotation ID placeholder
            sample_event = {
                "request_id": "fdb4ade2-c0e2-425d-91aa-4e9d39d64952",
                "timestamp": "2025-03-03T16:36:15.498898Z",
                "hook": "https://test-company-tadeas.rossum.app/api/v1/hooks/603761",
                "action": "scheduled",
                "event": "invocation",
                "rossum_authorization_token": api_token,
                "base_url": base_url,
                "settings": {
                    "annotation_id": "REPLACE_WITH_ANNOTATION_ID"
                },
                "secrets": {}
            }
            
            print("\n=== SAMPLE EVENT TEMPLATE ===")
            print(json.dumps(sample_event, indent=2))
            
    except Exception as e:
        print(f"Error: {str(e)}")
        # Print stack trace for debugging
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 