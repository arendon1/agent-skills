# Data Loading Reference

Load external data files to drive your document content.

## File Formats

### CSV
Load Comma Separated Values. Returns an array of arrays.
```typst
#let dataset = csv("data.csv")
#table(
    columns: dataset.first().len(),
    ..dataset.flatten()
)
```

### JSON
Load JavaScript Object Notation. Returns dictionaries and arrays.
```typst
#let conf = json("config.json")
#if conf.show_author [
  Author: #conf.author
]
```

### XML
Load XML data. Returns a dictionary structure.
```typst
#let book_data = xml("books.xml")
```

### YAML
Load YAML data. Returns dictionaries and arrays.
```typst
#let meta = yaml("metadata.yml")
```

### Raw Text
Read file content as a string.
```typst
#let notes = read("notes.txt")
```

## Embedding Files
Embed arbitrary files into the PDF output (Typst 0.13+).
```typst
#let _ = pdf.embed("supplementary_data.csv")
```

## Best Practices
*   Use data files to separate content from styling logic.
*   Combine with loop structures (`#for`) to generate repetitive document sections (e.g., invoices, catalogs).
