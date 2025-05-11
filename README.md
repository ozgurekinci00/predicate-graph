# Predicate Relationships Graph

A comprehensive tool for visualizing predicate device relationships from FDA 510(k) medical device clearances.

## Project Overview

This application extracts and visualizes predicate device relationships from FDA 510(k) medical device clearances by:

1. **Data Retrieval**: Fetches device information from the OpenFDA API and extracts predicate device relationships from associated PDF summaries
2. **Data Storage**: Caches device and relationship data in MongoDB for faster access
3. **Visualization**: Presents an interactive directed graph showing the predicate relationships between medical devices

## System Architecture

The project consists of two main components:

### Backend (FastAPI)
- Provides a REST API for device data retrieval and predicate extraction
- Connects to the OpenFDA API for device metadata
- Parses PDF documents to extract predicate device relationships
- Stores data in MongoDB for caching and performance

### Frontend (React)
- User-friendly interface for searching devices by K-number
- Interactive D3.js visualization of predicate device relationships
- Detailed device information display

## Requirements

- Python 3.8+
- Node.js 14+
- MongoDB (local or remote)
- Dependencies listed in `requirements.txt` (backend) and `client/package.json` (frontend)

## Getting Started

### Quick Start

The easiest way to run the entire application is with the provided script:

```bash
chmod +x start.sh
./start.sh
```

This will:
- Check for and kill any processes using ports 8002 (backend) and 3000 (frontend)
- Start the FastAPI backend server on port 8002
- Start the React frontend on port 3000
- Provide colored terminal output showing the status of both services

Access the application at: http://localhost:3000

### Manual Setup

1. **MongoDB Setup** (choose one option):

   **Option A: Local MongoDB** (default fallback if no .env file)
   - Install MongoDB on your local machine: [MongoDB Installation Guide](https://docs.mongodb.com/manual/installation/)
   - Start the MongoDB service
   
   **Option B: Remote MongoDB**
   - Create a MongoDB Atlas account: [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Set up a cluster and get your connection URI

2. **Environment Configuration**:
   Create a `.env` file in the root directory:
   ```
   # MongoDB Configuration
   MONGODB_URI=mongodb+srv://username:password@your-cluster.mongodb.net/?retryWrites=true&w=majority
   MONGODB_DB=predicate_relationships
   MONGODB_DEVICES_COLLECTION=devices
   
   # API Configuration
   PORT=8002
   ```

   > **Note:** If no `.env` file is present, the application defaults to a local MongoDB instance at `mongodb://localhost:27017`.

3. **Start Backend Manually**:
   ```bash
   cd src
   python main.py
   ```

4. **Start Frontend Manually**:
   ```bash
   cd client
   npm install
   npm start
   ```

## Backend API Endpoints

### Get Device Information and Predicate Relationships

```
GET /api/device/{k_number}
```

#### Path Parameters:
- `k_number`: The K-number of the FDA 510(k) device (e.g., K191907)

#### Response:
```json
{
  "k_number": "K191907",
  "applicant": "Opsens Inc.",
  "decision_date": "2020-01-02",
  "decision_description": "Substantially Equivalent",
  "device_name": "OptoWire III",
  "product_code": "DQX",
  "sortable_date": "2020-01-02T00:00:00.000Z",
  "statement_or_summary": "Summary",
  "predicate_devices": [
    "K152991",
    "K142598"
  ]
}
```

### Check if a Device Exists in the Database

```
GET /api/device/check/{k_number}
```

### Health Check

```
GET /api/health
```

## Frontend Features

- **Device Search**: Enter any valid K-number to search for a device
- **Interactive Graph**: Visualize predicate relationships with an interactive directed graph
- **Device Information**: View detailed information about each device
- **Responsive Design**: Works on desktop and mobile devices

## Development Notes

- The application automatically handles PDF retrieval and parsing
- MongoDB is used for caching to improve performance on subsequent queries
- The frontend communicates with the backend via a proxy configuration

## Troubleshooting

If you encounter issues:
1. Check that MongoDB is running and accessible
2. Verify that both frontend and backend servers are running (ports 3000 and 8002)
3. Check the terminal output for specific error messages
4. Ensure you have the required Python and Node.js versions 
