import React, { useEffect, useState, useMemo, useRef } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { checkDeviceExists, fetchDevice, saveDevice } from './services/api';
import PredicateGraph from './components/PredicateGraph';
// eslint-disable-next-line no-unused-vars
import DeviceDetails from './components/DeviceDetails';
import KNumberSearch from './components/KNumberSearch';
import './App.css';

// Create a query client
const queryClient = new QueryClient();

// Sample K-number
const DEFAULT_K_NUMBER = 'K191907';

// Add a constant for maximum number of explored nodes
const MAX_EXPLORED_NODES = 25;

function DeviceViewer() {
  const [devices, setDevices] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState('Initializing...');
  const [currentKNumber, setCurrentKNumber] = useState(DEFAULT_K_NUMBER);
  const [exploredNodes, setExploredNodes] = useState([DEFAULT_K_NUMBER]);
  const [toast, setToast] = useState({ show: false, message: '', type: 'error' });

  // Add a ref to track if data has already been loaded
  const dataLoadedRef = useRef(false);

  // Display toast notification
  const showToast = (message, type = 'error') => {
    setToast({ show: true, message, type });
    setTimeout(() => {
      setToast({ show: false, message: '', type: 'error' });
    }, 3000);
  };

  // Handle search for a new K-number
  const handleSearch = async (kNumber) => {
    // Don't reload if we're already processing this node or it's the current node
    if (isLoading || kNumber === currentKNumber) {
      return;
    }

    try {
      // Set loading state
      setIsLoading(true);
      setError(null);
      
      // Check if device exists in MongoDB
      setLoadingStatus(`Checking MongoDB for existing data for ${kNumber}...`);
      let checkResult;
      try {
        checkResult = await checkDeviceExists(kNumber);
      } catch (err) {
        console.warn('MongoDB check failed, proceeding to fetch from FDA API:', err);
        checkResult = { exists: false, error: err.message };
      }
      
      // Fetch device data
      let deviceData;
      try {
        if (checkResult.exists) {
          setLoadingStatus(`Fetching device data for ${kNumber} from MongoDB...`);
          deviceData = await fetchDevice(kNumber);
        } else {
          setLoadingStatus(`Fetching device data for ${kNumber} from FDA API...`);
          deviceData = await fetchDevice(kNumber);
          
          // Save to MongoDB
          try {
            setLoadingStatus(`Saving device data for ${kNumber} to MongoDB...`);
            await saveDevice(deviceData);
          } catch (err) {
            console.warn('Failed to save to MongoDB, but proceeding with displayed data:', err);
          }
        }
      } catch (err) {
        // Handle 404 errors with a toast notification
        if (err.response && err.response.status === 404) {
          showToast(`Couldn't find any device with the K-number ${kNumber}`);
          setIsLoading(false);
          return;
        }
        
        // Handle other errors
        throw err;
      }
      
      // Handle potentially undefined predicate_devices
      if (!deviceData.predicate_devices) {
        deviceData.predicate_devices = [];
      }
      
      // Update devices state
      setDevices(prev => ({ ...prev, [kNumber]: deviceData }));
      
      // Reset explored nodes to just this new one
      setExploredNodes([kNumber]);
      
      // Update current K-number
      setCurrentKNumber(kNumber);
    } catch (err) {
      console.error(`Error fetching device data for ${kNumber}:`, err);
      setError(err.message || `Failed to load device data for ${kNumber}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle predicate node click
  const handlePredicateClick = async (predicateId) => {
    // Don't reload if we're already processing this node or it's the current node
    if (isLoading || predicateId === currentKNumber) {
      return;
    }

    try {
      // Set loading state without changing current view yet
      setIsLoading(true);
      
      // Load the predicate device if needed
      // If we already have the device data, no need to fetch it again
      if (!devices[predicateId]) {
        // First check if the device exists in MongoDB
        setLoadingStatus(`Checking MongoDB for existing data for ${predicateId}...`);
        let checkResult;
        try {
          checkResult = await checkDeviceExists(predicateId);
        } catch (err) {
          console.warn('MongoDB check failed, proceeding to fetch from FDA API:', err);
          checkResult = { exists: false, error: err.message };
        }
        
        // Fetch device data
        let deviceData;
        try {
          if (checkResult.exists) {
            setLoadingStatus(`Fetching device data for ${predicateId} from MongoDB...`);
            deviceData = await fetchDevice(predicateId);
          } else {
            setLoadingStatus(`Fetching device data for ${predicateId} from FDA API...`);
            deviceData = await fetchDevice(predicateId);
            
            // Save to MongoDB
            try {
              setLoadingStatus(`Saving device data for ${predicateId} to MongoDB...`);
              await saveDevice(deviceData);
            } catch (err) {
              console.warn('Failed to save to MongoDB, but proceeding with displayed data:', err);
            }
          }
        } catch (err) {
          // Handle 404 errors with a toast notification
          if (err.response && err.response.status === 404) {
            showToast(`Couldn't find any device with the K-number ${predicateId}`);
            setIsLoading(false);
            return;
          }
          
          // Handle other errors
          throw err;
        }
        
        // Handle potentially undefined predicate_devices
        if (!deviceData.predicate_devices) {
          deviceData.predicate_devices = [];
        }
        
        // Update devices state with new data in a single batch update
        setDevices(prev => ({ ...prev, [predicateId]: deviceData }));
      }
      
      // Add to explored nodes if it's not already there
      if (!exploredNodes.includes(predicateId)) {
        if (exploredNodes.length >= MAX_EXPLORED_NODES) {
          setExploredNodes(prev => [...prev.slice(-MAX_EXPLORED_NODES + 1), predicateId]);
        } else {
          setExploredNodes(prev => [...prev, predicateId]);
        }
      }
      
      // Only after all data fetching is complete, update the current K-number
      setCurrentKNumber(predicateId);
    } catch (err) {
      console.error(`Error fetching device data for ${predicateId}:`, err);
      setError(err.message || `Failed to load device data for ${predicateId}`);
    } finally {
      // Only turn off loading after everything is complete
      setIsLoading(false);
    }
  };

  // Reset graph to initial state
  const resetGraph = () => {
    setExploredNodes([DEFAULT_K_NUMBER]);
    setCurrentKNumber(DEFAULT_K_NUMBER);
  };

  // Retry loading
  const handleRetry = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fetch device data for current K-number
      setLoadingStatus(`Fetching device data for ${currentKNumber}...`);
      const deviceData = await fetchDevice(currentKNumber);
      
      // Handle potentially undefined predicate_devices
      if (!deviceData.predicate_devices) {
        deviceData.predicate_devices = [];
      }
      
      // Update devices state
      setDevices(prev => ({ ...prev, [currentKNumber]: deviceData }));
    } catch (err) {
      console.error(`Error fetching device data:`, err);
      setError(err.message || `Failed to load device data`);
    } finally {
      setIsLoading(false);
    }
  };

  // Load initial device data - Use a ref to prevent duplicate loads
  useEffect(() => {
    // Skip if data is already loaded
    if (dataLoadedRef.current) {
      return;
    }

    const initializeGraph = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // First check if the device exists in MongoDB
        setLoadingStatus(`Checking MongoDB for existing data for ${DEFAULT_K_NUMBER}...`);
        let checkResult;
        try {
          checkResult = await checkDeviceExists(DEFAULT_K_NUMBER);
        } catch (err) {
          console.warn('MongoDB check failed, proceeding to fetch from FDA API:', err);
          checkResult = { exists: false, error: err.message };
        }
        
        // Fetch device data
        let deviceData;
        try {
          if (checkResult.exists) {
            setLoadingStatus(`Fetching device data for ${DEFAULT_K_NUMBER} from MongoDB...`);
            deviceData = await fetchDevice(DEFAULT_K_NUMBER);
          } else {
            setLoadingStatus(`Fetching device data for ${DEFAULT_K_NUMBER} from FDA API...`);
            deviceData = await fetchDevice(DEFAULT_K_NUMBER);
            
            // Save to MongoDB
            try {
              setLoadingStatus(`Saving device data for ${DEFAULT_K_NUMBER} to MongoDB...`);
              await saveDevice(deviceData);
            } catch (err) {
              console.warn('Failed to save to MongoDB, but proceeding with displayed data:', err);
            }
          }
        } catch (err) {
          // Handle 404 errors with a toast message, then try with a fallback K-number
          if (err.response && err.response.status === 404) {
            showToast(`Couldn't find any device with the K-number ${DEFAULT_K_NUMBER}`);
            // For initial load, we should try another K-number instead of failing completely
            setIsLoading(false);
            return;
          }
          throw err;
        }
        
        // Handle potentially undefined predicate_devices
        if (!deviceData.predicate_devices) {
          deviceData.predicate_devices = [];
        }
        
        // Mark as loaded BEFORE state updates to prevent race conditions
        dataLoadedRef.current = true;
        
        // Batch state updates - do this in a single update to prevent rerenders
        setDevices({ [DEFAULT_K_NUMBER]: deviceData });
      } catch (err) {
        console.error(`Error fetching initial device data:`, err);
        setError(err.message || `Failed to load initial device data`);
      } finally {
        setIsLoading(false);
      }
    };
    
    initializeGraph();
  }, []);

  // Build graph data
  const buildGraphData = useMemo(() => {
    // If we have no data yet, return empty
    if (Object.keys(devices).length === 0) {
      return { nodes: [], links: [], currentNode: null };
    }

    const nodeMap = new Map();
    const links = [];

    // First add all explored nodes and their predicates
    exploredNodes.forEach(nodeId => {
      const device = devices[nodeId];
      if (device) {
        // Add the node if it's not in the map
        if (!nodeMap.has(nodeId)) {
          nodeMap.set(nodeId, {
            id: nodeId,
            name: nodeId,
            group: nodeId === currentKNumber ? 1 : 2, // Current node is group 1, others are group 2
            device
          });
        }

        // Add all predicate nodes even if they haven't been explored yet
        device.predicate_devices.forEach(predicateId => {
          // Add the link
          links.push({
            source: nodeId,
            target: predicateId,
            value: 1
          });
          
          // Add the predicate node if it's not already in the map
          if (!nodeMap.has(predicateId)) {
            // If we have data for this predicate, use it, otherwise create a placeholder
            const predicateDevice = devices[predicateId];
            nodeMap.set(predicateId, {
              id: predicateId,
              name: predicateId,
              group: predicateId === currentKNumber ? 1 : 3, // Group 3 for unexplored predicates
              device: predicateDevice || null // May be null if we haven't loaded it yet
            });
          }
        });
      }
    });

    // Convert map to array
    const nodesArray = Array.from(nodeMap.values());

    return {
      nodes: nodesArray,
      links,
      currentNode: devices[currentKNumber]
    };
  }, [devices, exploredNodes, currentKNumber]);

  if (isLoading && Object.keys(devices).length === 0) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-blue-500 border-t-transparent mx-auto"></div>
          <p className="mt-4 text-gray-600 text-sm">{loadingStatus}</p>
        </div>
      </div>
    );
  }

  if (error && Object.keys(devices).length === 0) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 px-4 py-3 rounded relative max-w-lg" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
          <button 
            className="mt-3 bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded transition-colors duration-150"
            onClick={handleRetry}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Toast Notification */}
      {toast.show && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md shadow-md animate-fade-in-out z-50 max-w-sm">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-red-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p>{toast.message}</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Predicate Device Relationship Graph</h1>
        <KNumberSearch 
          onSearch={handleSearch}
          isLoading={isLoading}
        />
      </div>
      
      <div className="mb-4 flex items-center">
        <button
          onClick={resetGraph}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md shadow-sm transition-colors duration-150"
          disabled={isLoading}
        >
          Reset Graph
        </button>
        
        {isLoading ? (
          <div className="ml-4 text-gray-600 flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent mr-2"></div>
            <span className="text-sm">{loadingStatus}</span>
          </div>
        ) : (
          <div className="ml-4 text-sm text-gray-600">
            Explored devices: {exploredNodes.length}
          </div>
        )}
      </div>
      
      {error && !toast.show ? (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md shadow-sm mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="font-medium">Error: {error}</p>
              <button
                onClick={handleRetry}
                className="mt-2 text-sm bg-red-500 hover:bg-red-600 text-white py-1 px-3 rounded-md transition-colors duration-150"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      ) : null}
      
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="lg:w-3/4 transition-all duration-300">
          <PredicateGraph
            graphData={buildGraphData}
            onPredicateClick={handlePredicateClick}
            isLoading={isLoading}
            currentKNumber={currentKNumber}
            exploredNodes={exploredNodes}
          />
        </div>
        
        {buildGraphData.currentNode && (
          <div className="lg:w-1/4 transition-all duration-300">
            <div className="bg-white p-4 rounded-lg shadow-sm h-auto border border-gray-100">
              <h2 className="text-lg font-bold text-gray-800 mb-4 pb-2 border-b border-gray-100">Device Details</h2>
              <div className="space-y-2">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">K-Number</span>
                  <span className="font-medium">{currentKNumber}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">Device Name</span>
                  <span className="font-medium">{buildGraphData.currentNode.device_name || 'N/A'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">Applicant</span>
                  <span className="font-medium">{buildGraphData.currentNode.applicant || 'N/A'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">Decision Date</span>
                  <span className="font-medium">{buildGraphData.currentNode.decision_date || 'N/A'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">Decision</span>
                  <span className="font-medium">{buildGraphData.currentNode.decision_description || 'N/A'}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 uppercase">Predicate Devices</span>
                  <span className="font-medium">
                    {buildGraphData.currentNode.predicate_devices && buildGraphData.currentNode.predicate_devices.length > 0
                      ? buildGraphData.currentNode.predicate_devices.join(', ')
                      : 'None'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <DeviceViewer />
      </div>
    </QueryClientProvider>
  );
}

export default App;
