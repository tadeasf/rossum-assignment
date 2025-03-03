# Rossum XML Exporter

A serverless hook for Rossum that generates XML export data from Rossum annotations and posts it to an external API.

## Features

- Automatically processes Rossum annotation data into a standardized XML format
- Base64 encodes XML content for secure transmission
- Supports posting data to external endpoints
- Includes comprehensive testing tools for validating XML format and API integration

## Recent Fixes

- **XML Formatting**: Fixed XML indentation to ensure proper formatting with standardized two-space indentation
- **Currency Formatting**: Ensured currency codes are always converted to uppercase (e.g., "NOK" instead of "nok")
- **Base64 Encoding**: Added extra validation to ensure XML is properly formatted before base64 encoding

## Setup

### Prerequisites

- Python 3.12 or newer
- [Rye](https://rye.astral.sh/) for dependency management
- Rossum API credentials

### Environment Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/tadeasfort/rossum-assignment.git
   cd rossum-assignment
   ```

2. Set up environment with Rye:
   ```bash
   rye sync
   ```

3. Copy .env.example to .env and fill in your credentials.

## Available Commands

### Authentication

Authenticate with Rossum API and save token (alternative to setting ROSSUM_API_TOKEN directly):

```bash
rye run login
```

### Deployment

Deploy the hook to Rossum's serverless platform:

```bash
rye run deploy
```

This will deploy the function defined in `src/rossum_hook.py` with the name "XML EXPORTER".

### Triggering the Hook

Trigger the deployed hook with an annotation ID:

```bash
rye run trigger [hook_id]
```

If no hook_id is provided, it will use the DEFAULT_FUNCTION_NAME from your .env file.

This command generates a `payload.json` file containing the base64-encoded XML export, which can be used for testing.

## Testing

Due to Rossum serverless limitations (hooks can only call pre-approved public APIs), this project includes special testing tools to validate functionality locally.

### Testing Workflow

1. First, trigger the hook to generate a payload:
   ```bash
   rye run trigger [hook_id]
   ```

2. Validate the XML structure and format:
   ```bash
   rye run test-xml-format
   ```
   This validates that:
   - XML structure matches the expected schema
   - Currency values are uppercase
   - XML is properly indented
   - Base64 encoding/decoding works correctly

3. Test sending the payload to a PostBin endpoint:
   ```bash
   rye run test-postbin [postbin_url]
   ```
   
   For debugging with verbose output:
   ```bash
   rye run test-postbin-debug [postbin_url]
   ```

## XML Format

The XML follows this structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<InvoiceRegisters>
  <Invoices>
    <Payable>
      <InvoiceNumber>...</InvoiceNumber>
      <InvoiceDate>...</InvoiceDate>
      <DueDate>...</DueDate>
      <TotalAmount>...</TotalAmount>
      <Notes/>
      <Iban>...</Iban>
      <Amount>...</Amount>
      <Currency>...</Currency>
      <Vendor>...</Vendor>
      <VendorAddress>...</VendorAddress>
      <Details>
        <Detail>
          <Amount>...</Amount>
          <AccountId/>
          <Quantity>...</Quantity>
          <Notes></Notes>
        </Detail>
        <!-- Additional line items... -->
      </Details>
    </Payable>
  </Invoices>
</InvoiceRegisters>
```

## Payload Format

When the hook is triggered it generates annotationId and content. You can use them to test the XML format and posting to an external API (you can have a look in payload_example.json) and create payload.json file pasting your output into it.

## Limitations and Workarounds

- **Rossum API Restrictions**: Rossum serverless functions can only call pre-approved public APIs. Our testing approach works around this by:
  1. Generating the payload locally
  2. Testing XML structure independently
  3. Using PostBin for testing HTTP posting capability

- **XML Validation**: The `test-xml-format` tool ensures that the generated XML meets the required structure and formatting standards without needing an external service.

## Troubleshooting

- If authentication fails, try running `rye run login` to refresh your token
- Ensure your .env file contains the correct credentials
- Check the logs after running commands for detailed error messages

## License

GPL-3.0
