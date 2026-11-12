import io
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import footportal as f


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class PortalTests(unittest.TestCase):
    def test_rss_parser(self):
        xml = b'''<?xml version="1.0"?><rss><channel><item>
        <title>Zenit &amp; Loko</title><link>https://example.com/news?a=1</link>
        <description>&lt;b&gt;Game&lt;/b&gt; happened</description>
        <pubDate>Thu, 12 Nov 2026 10:00:00 +0000</pubDate></item></channel></rss>'''
        with patch.object(f.urllib.request, 'urlopen', return_value=FakeResponse(xml)):
            news = f.read_feed('Test', 'https://example.com/rss')
        self.assertEqual(len(news), 1)
        self.assertEqual(news[0]['title'], 'Zenit & Loko')
        self.assertEqual(news[0]['description'], 'Game happened')
        self.assertEqual(news[0]['published'].hour, 10)

    def test_atom_parser(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <title>News</title><link rel="alternate" href="https://example.com/atom-1" />
        <summary>Some summary</summary><updated>2026-11-12T11:00:00Z</updated>
        </entry></feed>'''
        with patch.object(f.urllib.request, 'urlopen', return_value=FakeResponse(xml)):
            news = f.read_feed('Test', 'https://example.com/rss')
        self.assertEqual(news[0]['url'], 'https://example.com/atom-1')
        self.assertEqual(news[0]['published'].hour, 11)

    def test_render_safe_html(self):
        msg = f.make_message({'title': '<Гол & триумф>', 'body': 'Привет <мир> & всем'},
                             {'url': 'https://test.ru/f?x=1&y=2', 'source': 'Sport.ru'})
        self.assertIn('&lt;Гол &amp; триумф&gt;', msg)
        self.assertIn('&lt;мир&gt;', msg)
        self.assertIn('href="https://test.ru/f?x=1&amp;y=2"', msg)

    def test_canonical_duplicates(self):
        self.assertEqual(f.canonical_url('https://EXAMPLE.org/test/?utm=a'), 'https://example.org/test')

    def test_generation_response_schema(self):
        response = {'output': [{'content': [{'type': 'output_text', 'text': json.dumps({
            'title': 'Главный тренер ушел в отставку',
            'body': 'Сегодня ' * 35})}]}]}
        item = {'source': 'Test', 'title': 'Any', 'description': 'Hi', 'url': 'https://example.com'}
        with patch.object(f, 'http_json', return_value=response) as req:
            obj = f.generate_news(item, [], 'dummy', 'gpt-6-luna')
            self.assertEqual(obj['title'], 'Главный тренер ушел в отставку')
            self.assertEqual(req.call_args[0][0], f.OPENAI_ENDPOINT)
            self.assertEqual(req.call_args[0][1]['model'], 'gpt-6-luna')

    def test_publish_channel(self):
        with patch.object(f, 'http_json', return_value={'ok': True}) as req:
            f.publish('Text', 'dummy', '@footportal2')
            payload = req.call_args[0][1]
            self.assertEqual(payload['chat_id'], '@footportal2')
            self.assertEqual(payload['parse_mode'], 'HTML')

    def test_run_posts_and_remembers(self):
        candidate = {'url': 'https://example.com/n1', 'title': 'Sport news', 'description': '', 'source': 'Example', 'published': datetime.now(timezone.utc)}
        local_state = {'posted_urls': [], 'recent_titles': []}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'dummy', 'TELEGRAM_BOT_TOKEN': 'dummy', 'DRY_RUN': '0'}), \
             patch.object(f, 'get_candidates', return_value=[candidate]), \
             patch.object(f, 'load_state', return_value=local_state), \
             patch.object(f, 'save_state') as save, \
             patch.object(f, 'generate_news', return_value={'title': 'Победа Криволовского', 'body': 'День игры', 'mode': 'test'}), \
             patch.object(f, 'publish') as publish:
            self.assertEqual(f.run(), 0)
            publish.assert_called_once()
            save.assert_called_once()
            self.assertEqual(local_state['posted_urls'], ['https://example.com/n1'])


if __name__ == '__main__':
    unittest.main()
