# Post queue

The scheduled task creates **1–3 ordinary fictional sports news posts** per run and may additionally create **0 or more** character comment microarticles on suitable occasions. Comment posts do not count toward the 1–3 ordinary news posts.

Use a unique filename for every post, e.g. `20261112-120000-01.json`.

## Ordinary news
```json
{
  "title": "«Спартак» объявил о переходе полузащитника",
  "body": "Текст пародийной новости на русском языке длиной 120–3200 символов...",
  "source_url": "https://example.org/real-original-sports-story",
  "source_name": "Sport.ru"
}
```
The source URL must be a verified real sports article. The story is fictional.

## Extra fictional character comment

```json
{
  "kind": "commentary",
  "speaker": "ivan-vyatkin",
  "title": "Вяткин: «Это вообще как должно работать?»",
  "body": "«Это вообще как должно работать? Здесь должен идти развёрнутый разговорный монолог в один–три крупных абзаца, а не десяток отдельных сообщений... »\n\nПовод для комментария: реакция на конкретное спортивное событие.",
  "source_url": "https://example.org/real-verified-sports-article",
  "source_name": "Sports.ru"
}
```

Valid speaker IDs: `ivan-vyatkin`, `nikita-filatov`. Their **work-in-progress fictional** profiles live in `lore/characters.json`.

**Editorial format:** a catchy exact direct quote from the character in the title; the same phrase must appear verbatim within the quoted speech in `body`; after the speech, outside quotation marks, add the precise original news context on a separate line beginning `Повод для комментария:`. Comments may be longer and more emotional than the short dry news; `body` is still limited to **3200 characters** and the full Telegram message to 4096.

**Deduplication:** ordinary news deduplicates by normalized `source_url`; comments deduplicate by `speaker + source_url`, allowing both fictional characters to comment on the same article, even if it was already the source of an ordinary news post. File name dedup applies to all posts. Don't edit sent files. Commentaries on fictional lore events must refer to a post already confirmed in `data/sent.json` and use its real verified article URL as `source_url`. No fake sources or invented Telegram links.

This repo is public. Never add raw personal chat histories, private messages, or purported genuine quotes from real people here.
