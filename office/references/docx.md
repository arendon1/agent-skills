# DOCX Generation Guide

## Key Concepts

The `docx` package uses a builder pattern:

* **Document**: Root container.
* **Section**: Contains pages.
* **Paragraph**: Line/block of text.
* **TextRun**: Formatted text.
* **Table**: Grid of TableRow -> TableCell -> Paragraph.

## Basic Structure

```typescript
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx';

const doc = new Document({
  sections: [{
    children: [
      new Paragraph({
        text: 'Monthly Report',
        heading: HeadingLevel.HEADING_1,
      }),
      new Paragraph({
        children: [
          new TextRun('This is a '),
          new TextRun({ text: 'bold', bold: true }),
        ],
      }),
    ],
  }],
});
```

## Tables

```typescript
import { Table, TableRow, TableCell, Paragraph, WidthType } from 'docx';

const table = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  rows: [
    new TableRow({
      children: [
        new TableCell({ children: [new Paragraph('Header 1')] }),
        new TableCell({ children: [new Paragraph('Header 2')] }),
      ],
    }),
  ],
});
```

## Images

```typescript
import { ImageRun } from 'docx';
import { readFileSync } from 'fs';

const imageBuffer = readFileSync('logo.png');
new Paragraph({
  children: [
    new ImageRun({
      data: imageBuffer,
      transformation: { width: 200, height: 100 },
      type: 'png',
    }),
  ],
});
```

## Export Patterns

```typescript
// Node.js
import { writeFileSync } from 'fs';
const buffer = await Packer.toBuffer(doc);
writeFileSync('document.docx', buffer);

// Browser
const blob = await Packer.toBlob(doc);
saveAs(blob, 'document.docx');
```
