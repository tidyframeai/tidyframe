/**
 * Utility functions for CSV file handling and template generation
 */

export interface SampleDataRow {
  name: string;
  email?: string;
  phone?: string;
  address?: string;
}

export const generateSampleCSV = (includeOptionalColumns = true): string => {
  const headers = includeOptionalColumns 
    ? ['name', 'email', 'phone', 'address']
    : ['name'];
    
  const sampleRows: SampleDataRow[] = [
    {
      name: 'John Smith',
      email: 'john.smith@email.com',
      phone: '555-0123',
      address: '123 Main St, Anytown, USA'
    },
    {
      name: 'Jane Doe',
      email: 'jane.doe@email.com',
      phone: '555-0124',
      address: '456 Oak Ave, Somewhere, USA'
    },
    {
      name: 'ABC Corporation',
      email: 'contact@abc.com',
      phone: '555-0125',
      address: '789 Business Blvd, Corporate City, USA'
    },
    {
      name: 'Sarah Johnson',
      email: 'sarah.j@email.com',
      phone: '555-0126',
      address: '321 Pine St, Hometown, USA'
    },
    {
      name: 'XYZ Trust',
      email: 'info@xyztrust.com',
      phone: '555-0127',
      address: '654 Trust Lane, Financial District, USA'
    }
  ];

  let csvContent = headers.join(',') + '\n';
  
  sampleRows.forEach(row => {
    const values = headers.map(header => {
      const value = row[header as keyof SampleDataRow] || '';
      // Escape commas and quotes in CSV values
      return value.includes(',') || value.includes('"') 
        ? `"${value.replace(/"/g, '""')}"` 
        : value;
    });
    csvContent += values.join(',') + '\n';
  });

  return csvContent;
};

export const downloadCSVFile = (content: string, filename: string): void => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const validateCSVHeaders = (csvText: string): { isValid: boolean; message?: string; detectedHeaders?: string[]; selectedColumn?: string } => {
  try {
    const firstLine = csvText.split('\n')[0];
    const headers = firstLine.split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''));
    
    // Check for required columns in priority order
    const hasNameColumn = headers.includes('name');
    const hasParseStringColumn = headers.includes('parse_string');

    // Determine which column will be used (first match in priority order)
    let selectedColumn: string | undefined;
    if (hasNameColumn) {
      selectedColumn = 'name';
    } else if (hasParseStringColumn) {
      selectedColumn = 'parse_string';
    }

    if (!selectedColumn) {
      return {
        isValid: false,
        message: 'Missing required column: Your file must contain a column named "name" or "parse_string".',
        detectedHeaders: headers
      };
    }
    
    return {
      isValid: true,
      detectedHeaders: headers,
      selectedColumn
    };
  } catch {
    return {
      isValid: false,
      message: 'Unable to read file headers. Please ensure your file is properly formatted.'
    };
  }
};

export const REQUIRED_COLUMNS = ['name', 'parse_string'] as const;
export const OPTIONAL_COLUMNS = ['email', 'phone', 'address'] as const;