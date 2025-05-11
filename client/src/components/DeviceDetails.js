import React from 'react';

const DeviceDetails = ({ device }) => {
  if (!device) {
    return (
      <div className="p-4 bg-white rounded-lg shadow-md">
        <p className="text-gray-500">No device selected</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        {device.k_number}
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Device Name</h3>
            <p className="mt-1 text-gray-900">{device.device_name || 'N/A'}</p>
          </div>
          
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Applicant</h3>
            <p className="mt-1 text-gray-900">{device.applicant || 'N/A'}</p>
          </div>
          
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Product Code</h3>
            <p className="mt-1 text-gray-900">{device.product_code || 'N/A'}</p>
          </div>
        </div>
        
        <div>
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Decision Date</h3>
            <p className="mt-1 text-gray-900">{device.decision_date || 'N/A'}</p>
          </div>
          
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Decision</h3>
            <p className="mt-1 text-gray-900">{device.decision_description || 'N/A'}</p>
          </div>
          
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-500">Document Type</h3>
            <p className="mt-1 text-gray-900">{device.statement_or_summary || 'N/A'}</p>
          </div>
        </div>
      </div>
      
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-2">Predicate Devices</h3>
        {device.predicate_devices && device.predicate_devices.length > 0 ? (
          <ul className="mt-1 pl-5 list-disc text-gray-900">
            {device.predicate_devices.map(predicateId => (
              <li key={predicateId} className="mb-1">
                <span className="font-medium">{predicateId}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-gray-500">No predicate devices found</p>
        )}
      </div>
    </div>
  );
};

export default DeviceDetails; 