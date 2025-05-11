# Predicate Device Relationships Visualizer

A React application for visualizing FDA 510(k) predicate device relationships.

## Overview

This frontend application provides a user interface for:
- Searching FDA devices by K-number
- Visualizing predicate device relationships in an interactive graph
- Displaying detailed information about devices

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)
- Running backend API server (on port 8002)

### Setup and Running

1. **Install dependencies**:
   ```
   npm install
   ```

2. **Start the development server**:
   ```
   npm start
   ```
   This runs the app in development mode at [http://localhost:3000](http://localhost:3000)

3. **Build for production**:
   ```
   npm run build
   ```
   Builds the app for production to the `build` folder.

## Usage

1. Enter a K-number (e.g., K191907) in the search box
2. View the device information and predicate relationships graph
3. Interact with the graph:
   - Hover over nodes to see device details
   - Click on nodes to focus on that device
   - Use the zoom controls to adjust the view

## Development Notes

- The app uses a proxy to communicate with the backend API (see `package.json`)
- D3.js is used for graph visualization
- Tailwind CSS for styling

## Troubleshooting

If you encounter any issues:
1. Ensure the backend API is running on port 8002
2. Check browser console for errors
3. Verify that MongoDB is properly configured and running

## Available Scripts

- `npm start`: Runs the app in development mode
- `npm test`: Launches the test runner
- `npm run build`: Builds the app for production
