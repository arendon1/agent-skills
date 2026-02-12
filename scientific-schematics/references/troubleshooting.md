# Troubleshooting

## Common Issues

### AI Generation
*   **Overlapping Text**: Increase iterations (`--iterations 2`) to let the AI refine spacing.
*   **Bad Connections**: Be more specific in your prompt about direction ("top to bottom", "arrow from A to B").

### Quality Checks
*   **False Positive Overlaps**: Adjust threshold or check `overlap_report.json`.
*   **Accessibility Failures**: Use "colorblind-friendly" in prompt. Switch to Okabe-Ito palette.

### Technical
*   **Visual Report Failed**: Check Pillow/Matplotlib installation. Ensure disk space.
*   **Start-up Error**: Verify `OPENROUTER_API_KEY` is set.
