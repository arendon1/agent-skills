# Cloudflare Workers Integration

## DOCX Endpoint Example

```typescript
import { Hono } from 'hono';
import { Document, Packer, Paragraph } from 'docx';

const app = new Hono();

app.get('/invoice', async (c) => {
  const doc = new Document({ /* ... */ });
  const buffer = await Packer.toBuffer(doc);
  
  return new Response(buffer, {
    headers: {
      'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'Content-Disposition': 'attachment; filename="invoice.docx"',
    },
  });
});
```

## PDF (Browser Rendering)

For complex layouts, use `@cloudflare/puppeteer` to print HTML to PDF.

```typescript
import puppeteer from '@cloudflare/puppeteer';

export default {
  async fetch(request, env) {
    const browser = await puppeteer.launch(env.BROWSER);
    const page = await browser.newPage();
    await page.setContent('<h1>Hello World</h1>');
    const pdf = await page.pdf({ format: 'A4' });
    await browser.close();
    
    return new Response(pdf, {
      headers: { 'Content-Type': 'application/pdf' }
    });
  }
};
```
