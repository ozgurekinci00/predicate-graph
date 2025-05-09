# Predicate Relationships Graph

This project creates a graph of predicate device relationships from FDA 510(k) clearance data. 

## Overview

The FDA's 510(k) process allows medical device manufacturers to demonstrate that their device is "substantially equivalent" to one or more predicate devices already legally marketed in the United States. Each submission includes information about the device and references to predicate devices.

This application:

1. Fetches device data from the [OpenFDA API](https://open.fda.gov/apis/device/510k/)
2. Extracts K-numbers and device information
3. Processes the data to build a graph of predicate relationships
4. Retrieves and parses PDF summaries for device submissions

## Project Structure

```
.
├── data/           # Directory for storing fetched and processed data
│   └── pdfs/       # Directory for storing downloaded PDF summaries
├── docs/           # Documentation
├── src/            # Source code
│   ├── api.py          # API interaction functions
│   ├── config.py       # Configuration settings
│   ├── main.py         # Main application entry point
│   ├── processors.py   # Data processing functions
│   ├── pdf_utils.py    # PDF retrieval and parsing utilities
│   └── test_fetch.py   # Test script for API functionality
└── requirements.txt    # Project dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Predicate_Relationships_Graph
   ```

2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Testing

To test the API access and fetch a small number of records:

```
python3 -m src.main --max-records 10
```

### Fetch All K-numbers by Date Range

To fetch all K-numbers from the FDA API using date-based filtering (the optimal approach):

```
python3 -m src.main --fetch-by-date --batch-size 1000 --year-chunk 1
```

This command will fetch all 510(k) records by dividing the date range into yearly chunks, which overcomes the 26,000 record skip limitation of the OpenFDA API.

### Advanced Date Range Options

You can customize the date range and chunk size:

```
python3 -m src.main --fetch-by-date --start-year 2000 --end-year 2023 --year-chunk 2
```

This will fetch records from 2000 to 2023, dividing the range into 2-year chunks.

### Process Existing Batch Files

If you've already fetched the data in batches, you can process them to extract K-numbers:

```
python3 -m src.main --process-batches
```

### Using an API Key

For higher rate limits, you can provide an FDA API key:

```
python3 -m src.main --fetch-by-date --api-key YOUR_API_KEY
```

### PDF Functionality

The application can check for, download, and parse PDF summary documents for K-numbers:

- **Test PDF retrieval:** `python -m src.main --pdf-test`
  - Runs a test on sample K-numbers (K970904, K011958, K231101)

- **Check for PDF summaries for specific K-numbers:** `python -m src.main --check-pdfs --pdf-knumbers K970904 K011958 K231101`
  - Checks for PDF summaries for the specified K-numbers

- **Check from a JSON file:** `python -m src.main --check-pdfs --pdf-input-file knumbers.json`
  - Uses K-numbers from a JSON file

- **Check existence without downloading:** `python -m src.main --check-pdfs --pdf-knumbers K970904 K011958 --pdf-no-download`
  - Only checks if PDFs exist without downloading them

- **Parse PDFs without saving to disk:** `python -m src.main --check-pdfs --pdf-knumbers K970904 K011958 --pdf-parse-only`
  - Downloads and parses PDFs but does not save them to disk (useful for batch processing)

- **Limit the number of PDFs to check:** `python -m src.main --check-pdfs --pdf-input-file knumbers.json --pdf-limit 100`
  - Only checks the first 100 K-numbers in the input file

- **Save PDF check results:** `python -m src.main --check-pdfs --pdf-knumbers K970904 K011958 --pdf-output-file results.json`
  - Saves the results of PDF checks to a JSON file

## Data Files

The application generates the following data files:

- `all_knumbers_TIMESTAMP.json`: All unique K-numbers extracted from the data
- `all_devices_info_TIMESTAMP.json`: Processed device information for all records
- `data/pdfs/`: Directory containing downloaded PDF summaries
- PDF check results (if saved with `--pdf-output-file`)

## API Limitations and Solutions

The OpenFDA API has a limitation that prevents fetching beyond 26,000 records using standard pagination with the `skip` parameter. This application overcomes this limitation by:

1. Using date-based filtering to break the fetch into smaller chunks
2. Implementing pagination within each date range
3. Automatically handling retries and error recovery

This approach successfully retrieves all 171,589 K-numbers from the FDA database.

## PDF Summary Documents

FDA 510(k) summary documents are available as PDFs on the FDA website. The naming convention for these PDFs follows a pattern based on the K-number's year:

- K-numbers from 2000-2001 (K00xxxx, K01xxxx): `pdf/Kxxxxxx.pdf`
- K-numbers from 2002-2009 (K02xxxx-K09xxxx): `pdf2/Kxxxxxx.pdf` through `pdf9/Kxxxxxx.pdf`
- K-numbers from 2010+ (K10xxxx+): `pdf10/Kxxxxxx.pdf`, `pdf11/Kxxxxxx.pdf`, etc.

Not all K-numbers have associated PDF summaries, particularly for older submissions. This application provides functionality to check for the existence of these PDFs, download them, and parse their content.

## License

[MIT License](LICENSE)

## MongoDB Support

The application now uses MongoDB to store device data, which is essential for building the predicate relationship graph.

### Setup MongoDB

1. Install MongoDB on your system following the [official documentation](https://docs.mongodb.com/manual/installation/).
2. Start the MongoDB service.
3. The application will automatically connect to MongoDB running on localhost with default settings.

### MongoDB Usage

The application provides several commands for working with MongoDB:

```
# Check MongoDB connection status and view sample data
python -m src.main --mongodb-status

# Import devices from a JSON file into MongoDB
python -m src.main --import-to-mongodb data/all_devices_info_TIMESTAMP.json

# Fetch new devices from FDA API and save to MongoDB
python -m src.main --fetch-by-date --api-key YOUR_API_KEY
```

### Configuration

MongoDB connection settings can be configured using environment variables:

- `MONGODB_URI`: MongoDB connection URI (default: `mongodb://localhost:27017/`)
- `MONGODB_DB`: Database name (default: `predicate_relationships`) 