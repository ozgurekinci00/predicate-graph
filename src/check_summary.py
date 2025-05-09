#!/usr/bin/env python3
"""
Script to examine the FDA website structure for 510(k) summaries.
"""

import requests
from bs4 import BeautifulSoup
import re

# K-number to check
KNUMBER = "K971744"

def main():
    """Main function to examine website structure."""
    url = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={KNUMBER}"
    print(f"Fetching {url}...")
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for links
    print("\nLinks of interest:")
    links = soup.find_all('a')
    summary_links = []
    
    for link in links:
        if not link.has_attr('href'):
            continue
            
        href = link['href']
        text = link.text.strip().lower()
        
        # Look for links that might point to PDFs or summaries
        if ('summary' in text or 'pdf' in text or 'statement' in text or 
            'predicate' in text or '510(k)' in text):
            print(f"Link text: '{link.text.strip()}', href: '{href}'")
            summary_links.append(href)
    
    # Look for tables - the summary info might be in a table
    print("\nTables:")
    tables = soup.find_all('table')
    print(f"{len(tables)} tables found")
    
    # Check specific tables for predicate info
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"\nTable {i+1}: {len(rows)} rows")
        
        # Check if this table might contain predicate info
        predicate_rows = []
        for row in rows:
            row_text = row.text.lower()
            if 'predicate' in row_text or '510(k)' in row_text or 'substantially equivalent' in row_text:
                cells = row.find_all(['td', 'th'])
                cell_text = [cell.text.strip() for cell in cells]
                predicate_rows.append(cell_text)
                print(f"  Potential predicate info: {' | '.join(cell_text)}")
    
    # Look for forms
    print("\nForms:")
    forms = soup.find_all('form')
    print(f"{len(forms)} forms found")
    
    # Check for iframes (which might embed PDFs)
    print("\nIframes:")
    iframes = soup.find_all('iframe')
    print(f"{len(iframes)} iframes found")
    for iframe in iframes:
        if iframe.has_attr('src'):
            print(f"  iframe src: {iframe['src']}")
    
    # Check for structured data
    print("\nText containing 'predicate':")
    predicate_elements = soup.find_all(text=re.compile(r'predicate', re.IGNORECASE))
    for element in predicate_elements:
        print(f"  {element.strip()}")
    
    # Check for sections that might contain summary or statement
    print("\nText containing 'summary' or 'statement':")
    summary_elements = soup.find_all(text=re.compile(r'summary|statement', re.IGNORECASE))
    for element in summary_elements[:10]:  # Limit to first 10 to avoid too much output
        print(f"  {element.strip()}")

if __name__ == "__main__":
    main() 