// "Manual" layout (If needed, e.g. if the user gave specific layout requirements)

#set document(
  title: "Document Title",
  author: "Your Name",
  date: auto,
)

#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm),
  numbering: "1",
)

#set text(size: 11pt)
#set par(justify: true)
#set heading(numbering: "1.")

// Title page
#align(center)[
  #text(size: 24pt, weight: "bold")[Document Title]

  #v(1cm)
  #text(size: 14pt)[Your Name]

  #v(0.5cm)
  #datetime.today().display()
]

#pagebreak()

// Table of contents
#outline(title: "Table of Contents", indent: auto)

#pagebreak()

// Main content
= Introduction
Your introduction text...

= Methods
...

= Results
...

= Conclusion
...

#pagebreak()

// Bibliography
#bibliography("refs.bib", title: "References", style: "ieee")
