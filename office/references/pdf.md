# PDF Generation Guide

## Key Concepts (`pdf-lib`)

* **PDFDocument**: The file.
* **PDFPage**: Single page.
* **Coordinates**: Origin is **BOTTOM-LEFT**.
* **Units**: Points (72 pts = 1 inch).

## Basic Usage

```typescript
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';

const pdfDoc = await PDFDocument.create();
const page = pdfDoc.addPage([612, 792]); // Letter

// Embed fonts
const helvetica = await pdfDoc.embedFont(StandardFonts.Helvetica);

// Draw text
page.drawText('Hello World', {
  x: 50,
  y: 750, // Top of page
  size: 24,
  font: helvetica,
  color: rgb(0, 0, 0),
});
```

## Shapes & Images

```typescript
// Rectangle
page.drawRectangle({
  x: 50, y: 600, width: 200, height: 100,
  borderColor: rgb(0, 0, 0),
  color: rgb(0.9, 0.9, 0.9),
});

// Image (fetch bytes first)
const image = await pdfDoc.embedPng(imageBytes);
page.drawImage(image, { x: 50, y: 500, width: 100, height: 50 });
```

## Form Filling

```typescript
const pdfDoc = await PDFDocument.load(existingPdfBytes);
const form = pdfDoc.getForm();
form.getTextField('name').setText('John Doe');
form.flatten(); // Make read-only
```

## Export Patterns

```typescript
// Get bytes (works everywhere)
const pdfBytes = await pdfDoc.save();
```
