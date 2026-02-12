# PPTX Generation Guide

## Key Concepts (`pptxgenjs`)

* **Presentation**: `new pptxgen()`.
* **Slide**: `pptx.addSlide()`.
* **Units**: Inches by default.

## Basic Structure

```typescript
import pptxgen from 'pptxgenjs';

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_16x9';

const slide = pptx.addSlide();
slide.addText('Title', { x: 0.5, y: 0.5, fontSize: 24, bold: true });
```

## Advanced Elements

### Bullet Points

```typescript
slide.addText([
  { text: 'Point 1', options: { bullet: true } },
  { text: 'Point 2', options: { bullet: true } },
], { x: 0.5, y: 1.5, w: 8 });
```

### Tables

```typescript
const data = [
  ['Header 1', 'Header 2'],
  ['Value 1', 'Value 2'],
];
slide.addTable(data, { x: 0.5, y: 2.5, w: 9 });
```

### Charts

```typescript
slide.addChart(pptx.ChartType.bar, [
  { name: 'Series 1', labels: ['Q1', 'Q2'], values: [10, 20] }
], { x: 0.5, y: 4, w: 8, h: 3 });
```

## Export Patterns

```typescript
// Node.js
await pptx.writeFile({ fileName: 'presentation.pptx' });

// Browser/Worker (Get Buffer)
const arrayBuffer = await pptx.write({ outputType: 'arraybuffer' });
```
