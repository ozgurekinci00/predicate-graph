import React, { useRef, useEffect, useState, useMemo } from 'react';
import * as d3 from 'd3';

const PredicateGraph = ({ graphData, onPredicateClick, isLoading, currentKNumber, exploredNodes }) => {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [renderKey, setRenderKey] = useState(0);
  const initialRenderRef = useRef(true);
  
  // Extract dependency values to fix ESLint warnings
  const nodeIds = useMemo(() => {
    return graphData?.nodes?.map(n => n.id) || [];
  }, [graphData?.nodes]);
  
  const linkPaths = useMemo(() => {
    return graphData?.links?.map(l => `${l.source}-${l.target}`) || [];
  }, [graphData?.links]);
  
  // Memoize the graph data to prevent unnecessary recalculations
  const memoizedGraphData = useMemo(() => graphData, [
    // Only depend on the actual data, not loading state
    JSON.stringify(nodeIds),
    JSON.stringify(linkPaths),
    currentKNumber,
    graphData
  ]);
  
  // When loading finishes and data changes, update the render key to trigger a clean render
  useEffect(() => {
    if (!isLoading && graphData?.nodes) {
      setRenderKey(prev => prev + 1);
    }
  }, [isLoading, graphData?.nodes]);
  
  useEffect(() => {
    // On initial mount, delay rendering until we have data
    if (initialRenderRef.current && (!memoizedGraphData?.nodes || memoizedGraphData.nodes.length === 0)) {
      return;
    }
    
    // Skip rendering during loading states, but allow first render on initial load
    if (isLoading && renderKey > 0 && !initialRenderRef.current) {
      return;
    }
    
    if (!memoizedGraphData || !memoizedGraphData.nodes || memoizedGraphData.nodes.length === 0) {
      return;
    }
    
    // No longer first render
    if (initialRenderRef.current) {
      initialRenderRef.current = false;
    }
    
    // Store containerRef.current in a variable to use in cleanup
    const containerElement = containerRef.current;
    
    // Clear any existing graph
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    // Set up dimensions
    const width = 800;
    const height = 600;
    const nodeRadius = 40;
    
    // Destructure graph data
    const { nodes, links } = memoizedGraphData;
    
    // Set up the SVG
    svg.attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);
    
    // Create a container for zoomable content
    const g = svg.append("g")
      .attr("class", "zoom-container");
    
    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 3]) // Allow zooming from 0.1x to 3x
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    
    svg.call(zoom);
    
    // Initial zoom to fit all content (can be adjusted based on node count)
    const initialScale = Math.max(0.5, 1 - (nodes.length * 0.05));
    svg.call(zoom.transform, d3.zoomIdentity.translate(width/2, height/2).scale(initialScale).translate(-width/2, -height/2));
    
    // Add zoom controls - fixed to the SVG container, not affected by zoom
    const zoomControls = d3.select(containerRef.current)
      .insert("div", "svg")
      .attr("class", "zoom-controls absolute top-4 right-4 z-10")
      .style("pointer-events", "all");
    
    // Create a control panel for zoom buttons
    const controlPanel = zoomControls.append("div")
      .attr("class", "flex flex-col bg-white bg-opacity-80 rounded p-1");
    
    // Zoom buttons row
    const zoomRow = controlPanel.append("div")
      .attr("class", "flex mb-1");
    
    // Zoom in button
    zoomRow.append("button")
      .attr("class", "w-8 h-8 shadow hover:bg-gray-100 rounded mr-1 flex items-center justify-center text-xl font-normal")
      .text("+")
      .on("click", () => {
        svg.transition().duration(300).call(zoom.scaleBy, 1.3);
      });
    
    // Zoom out button
    zoomRow.append("button")
      .attr("class", "w-8 h-8 shadow hover:bg-gray-100 rounded flex items-center justify-center text-xl font-normal")
      .text("-")
      .on("click", () => {
        svg.transition().duration(300).call(zoom.scaleBy, 0.7);
      });
    
    // Reset view button
    controlPanel.append("button")
      .attr("class", "w-full h-8 shadow hover:bg-gray-100 rounded text-xs font-normal")
      .text("Reset View")
      .on("click", () => {
        svg.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(width/2, height/2).scale(initialScale).translate(-width/2, -height/2)
        );
      });
      
    // Define arrow markers for the links
    g.append("defs").selectAll("marker")
      .data(["arrow"]) // Unique marker ID
      .enter().append("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", nodeRadius + 12) // Position at the edge of the node
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");
    
    // Set up the simulation
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(200))
      .force("charge", d3.forceManyBody().strength(-1500))
      .force("center", d3.forceCenter(width / 2, height / 2));
    
    // Add the links with arrows
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("path")
      .data(links)
      .join("path")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2)
      .attr("fill", "none")
      .attr("marker-end", "url(#arrow)"); // Add the arrow marker
    
    // Add the nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));
    
    // Add circles for the nodes
    node.append("circle")
      .attr("r", nodeRadius)
      .attr("fill", d => {
        if (d.id === currentKNumber) return "#2563eb"; // Current node in blue
        if (exploredNodes.includes(d.id)) return "#10b981"; // Explored nodes in green
        return "#6b7280"; // Unexplored nodes in gray
      })
      .attr("stroke", d => d.id === currentKNumber ? "#fbbf24" : "#fff") // Highlight current node
      .attr("stroke-width", d => d.id === currentKNumber ? 4 : 2)
      .style("cursor", "pointer"); // All nodes are clickable in the expanded graph
    
    // Add labels to the nodes
    node.append("text")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("fill", "white")
      .style("font-weight", "bold")
      .style("font-size", "12px")
      .style("cursor", "pointer")
      .text(d => d.name);
    
    // Create a tooltip
    const tooltip = d3.select("body").append("div")
      .attr("class", "tooltip")
      .style("position", "absolute")
      .style("visibility", "hidden")
      .style("background-color", "rgba(0, 0, 0, 0.8)")
      .style("color", "white")
      .style("padding", "8px")
      .style("border-radius", "4px")
      .style("font-size", "12px")
      .style("pointer-events", "none")
      .style("z-index", 1000);
    
    // Add click event to nodes
    node.on("click", (event, d) => {
      if (!isLoading && onPredicateClick) {
        // Don't change the appearance during loading - we'll handle that with the overlay
        onPredicateClick(d.id);
      }
    });

    // Add hover effect for predicate nodes
    node.on("mouseover", function(event, d) {
      // Highlight the node
      d3.select(this).select("circle")
        .transition()
        .duration(200)
        .attr("stroke", "#fbbf24")
        .attr("stroke-width", 4);
      
      // Show tooltip
      let tooltipText = `K-Number: ${d.id}`;
      if (d.id === currentKNumber) {
        tooltipText += " (Current Focus)";
      }
      
      tooltip
        .style("visibility", "visible")
        .html(isLoading ? "Loading..." : tooltipText)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px");
    })
    .on("mousemove", function(event) {
      tooltip
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 28) + "px");
    })
    .on("mouseout", function(event, d) {
      // Remove highlight, except for current node
      const isCurrentNode = d.id === currentKNumber;
      d3.select(this).select("circle")
        .transition()
        .duration(200)
        .attr("stroke", isCurrentNode ? "#fbbf24" : "#fff")
        .attr("stroke-width", isCurrentNode ? 4 : 2);
      
      // Hide tooltip
      tooltip.style("visibility", "hidden");
    });
    
    // Set up the tick function to update positions
    simulation.on("tick", () => {
      // Update link paths
      link.attr("d", d => {
        // Create a curved path between nodes
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy);
        
        // Calculate the endpoint slightly before the target node
        // to prevent the arrowhead from overshooting the node
        const endPointRatio = (dr - nodeRadius) / dr;
        const endX = d.source.x + dx * endPointRatio;
        const endY = d.source.y + dy * endPointRatio;
        
        return `M${d.source.x},${d.source.y} L${endX},${endY}`;
      });
      
      // Update node positions
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
    
    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
    
    // Initial simulation run
    simulation.alpha(1).restart();
    
    // Clean up
    return () => {
      simulation.stop();
      tooltip.remove();
      // Remove zoom controls when component unmounts using the stored reference
      if (containerElement) {
        d3.select(containerElement).select(".zoom-controls").remove();
      }
    };
  }, [memoizedGraphData, onPredicateClick, exploredNodes, currentKNumber, renderKey, isLoading]);
  
  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="w-full h-[600px] border border-gray-100 rounded-lg bg-white shadow-sm flex items-center justify-center">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="mt-4 text-gray-500">No graph data available</p>
        </div>
      </div>
    );
  }
  
  return (
    <div ref={containerRef} className="graph-container relative bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
      {isLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-80 flex items-center justify-center z-20">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      )}
      
      {/* Tip tooltip */}
      <div className="absolute top-4 left-4 p-2 text-xs bg-white bg-opacity-90 rounded shadow-sm border border-gray-50 z-10">
        <p className="text-gray-600">Tip: Use mouse wheel to zoom, drag to pan. Use controls to reset view.</p>
      </div>
      
      <svg ref={svgRef} className="w-full h-full" />
      
      {/* Information about the node colors */}
      <div className="absolute bottom-4 right-4 bg-white bg-opacity-80 rounded p-2 text-xs shadow-sm border border-gray-100">
        <div className="flex items-center mb-1">
          <div className="w-3 h-3 rounded-full bg-blue-600 mr-2"></div>
          <span>Current Device</span>
        </div>
        <div className="flex items-center mb-1">
          <div className="w-3 h-3 rounded-full bg-green-600 mr-2"></div>
          <span>Explored Device</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-gray-600 mr-2"></div>
          <span>Unexplored Device</span>
        </div>
        
        {/* Added instruction about clicking nodes */}
        <div className="mt-2 text-xs text-gray-500">
          <em>Click nodes to explore their predicates</em>
        </div>
      </div>
    </div>
  );
};

export default React.memo(PredicateGraph); 