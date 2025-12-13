# Sample Documents Directory

This directory contains sample documents for testing the document retrieval system.

## Structure

- `financial_reports/` - Sample financial documents and reports
- `technical_docs/` - Technical documentation and guides  
- `policies/` - Company policies and procedures
- `research/` - Research papers and articles

## Usage

The document retriever tool will automatically create a sample database with test documents if none exists. You can add your own documents by:

1. Adding files to the appropriate subdirectories
2. Using the `DocumentRetriever.add_document()` method programmatically
3. Importing documents through the evaluation tools

## File Formats Supported

- Plain text (.txt)
- Markdown (.md)
- JSON documents with structured content
- CSV files (converted to text descriptions)

Note: The system currently works with text content. For other formats, content should be extracted to text first.