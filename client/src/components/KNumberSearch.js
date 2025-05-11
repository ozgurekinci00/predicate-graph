import React, { useState, useEffect } from 'react';

const KNumberSearch = ({ onSearch, isLoading }) => {
  const [kNumber, setKNumber] = useState('');
  const [error, setError] = useState('');
  const [showToast, setShowToast] = useState(false);

  // Show toast when error changes
  useEffect(() => {
    if (error) {
      setShowToast(true);
      const timer = setTimeout(() => {
        setShowToast(false);
      }, 3000); // Hide toast after 3 seconds
      
      return () => clearTimeout(timer);
    }
  }, [error]);

  const validateKNumber = (value) => {
    // K-numbers start with "K" followed by 6 digits
    const kNumberPattern = /^K\d{6}$/;
    return kNumberPattern.test(value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Normalize the input: uppercase the K and trim whitespace
    const normalizedKNumber = kNumber.trim().toUpperCase();
    
    if (!validateKNumber(normalizedKNumber)) {
      setError('Please enter a valid K-number (K followed by 6 digits)');
      return;
    }
    
    setError('');
    onSearch(normalizedKNumber);
  };

  const handleChange = (e) => {
    setKNumber(e.target.value);
    // Clear error when user starts typing again
    if (error) setError('');
  };

  return (
    <>
      {/* Toast notification */}
      {showToast && error && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md shadow-md animate-fade-in-out z-50 max-w-sm">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-red-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p>{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-center justify-end">
        <div className="relative">
          <input
            type="text"
            value={kNumber}
            onChange={handleChange}
            placeholder="Search K-number"
            className="w-44 px-3 py-2 text-sm border border-gray-200 rounded-l-md focus:outline-none"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          className={`px-3 py-2 text-sm w-20 h-9 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none shadow-sm transition-colors duration-150 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin h-4 w-4 text-white mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </span>
          ) : (
            'Search'
          )}
        </button>
      </form>
    </>
  );
};

export default KNumberSearch; 