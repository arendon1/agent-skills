# XLSX Generation Guide

## Key Concepts (`xlsx` / SheetJS)

* **Workbook**: Container for sheets.
* **Worksheet**: Single sheet (grid).
* **utils.aoa_to_sheet**: Array of Arrays -> Worksheet.
* **utils.json_to_sheet**: JSON Array -> Worksheet.
* **utils.book_new / book_append_sheet**: Create/Add sheets.

## From Array of Arrays

```typescript
import * as XLSX from 'xlsx';

const data = [
  ['Product', 'Price', 'Quantity', 'Total'],
  ['Widget A', 10, 5, { f: 'B2*C2' }],  // Formula
  ['Widget B', 15, 3, { f: 'B3*C3' }],
  ['', '', 'Grand Total:', { f: 'SUM(D2:D3)' }],
];

const ws = XLSX.utils.aoa_to_sheet(data);
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Sales');
```

## From JSON

```typescript
const invoices = [
  { id: 1, customer: 'Acme Corp', amount: 1500 },
  { id: 2, customer: 'Globex', amount: 2300 },
];
const ws = XLSX.utils.json_to_sheet(invoices);
```

## Formatting

```typescript
// Set column widths (characters)
ws['!cols'] = [
  { wch: 10 },  // Col A
  { wch: 20 },  // Col B
];
```

## Export Patterns

```typescript
// Node.js
XLSX.writeFile(workbook, 'report.xlsx');

// Browser/Workers (Get Buffer)
const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
```
