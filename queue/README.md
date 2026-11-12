# Post queue

A scheduled ChatGPT task writes 1-3 new JSON files here per run.

Use a unique filename for each post, e.g. `20261112-120000-01.json`.

```json
{
  "title": "«Спартак» объявил о переходе полузащитника",
  "body": "Текст пародийной новости на русском языке длиной 120–3200 символов...",
  "source_url": "https://example.org/real-original-sports-story",
  "source_name": "Sport.ru"
}
```

The source URL is a **real** news article. The generated story is fictional.
Never edit a sent file. Deduplication is based on filenames and source URLs.
