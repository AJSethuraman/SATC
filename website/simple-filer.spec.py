"""Focused Simple Filer regression checks; all submissions stay intercepted.

Run with the existing Playwright installation: python website/simple-filer.spec.py
Uses an ephemeral loopback server and the installed Chromium browser.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
import json
import re
import unittest

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class SimpleFilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(HERE)))
        Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.posts = []
        self.context = self.browser.new_context(service_workers='block')
        self.context.route('**/*', self.intercept)
        self.page = self.context.new_page()
        self.page.goto(self.url)

    def tearDown(self):
        self.context.close()

    def intercept(self, route):
        request = route.request
        if request.method not in ('GET', 'HEAD'):
            self.posts.append(request.post_data)
            route.fulfill(status=200, content_type='application/json', body='{"ok":true}')
        elif urlparse(request.url).netloc == urlparse(self.url).netloc:
            route.continue_()
        else:
            route.abort()

    def step(self, value):
        self.page.locator(f'label.chip:has(input[value="{value}"])').click()
        self.page.locator('#intakeForm button[type=submit]').click()

    def short_route(self, second='no'):
        self.page.locator('#sfStart').click()
        self.step('no')
        self.step(second)

    def answers(self):
        return self.page.evaluate('JSON.parse(sessionStorage.getItem("satc_intake_v1")).answers')

    def assert_full_route(self):
        self.assertEqual(self.page.locator('[data-likely-fit], #lfGo').count(), 0)
        self.assertIn('What can we help', self.page.locator('.wiz-q').inner_text())

    def test_url_route_uses_real_boundaries_and_survives_reload(self):
        self.assertNotIn(b'\x08', (HERE / 'intake-config.js').read_bytes())
        for suffix in ('?route=simple_filer', '#route=simple_filer',
                       '?source=home&route=simple_filer#intake', '?route=simple_filer&source=home'):
            with self.subTest(suffix=suffix):
                self.page.goto(self.url + suffix)
                self.assertEqual(self.page.locator('input[name=sf_other_income]').count(), 3)
                self.page.reload()
                self.assertEqual(self.page.locator('input[name=sf_other_income]').count(), 3)
        for suffix in ('?route=simple_filer_extra', '?route=simple_filer-extra', '?otherroute=simple_filer'):
            with self.subTest(suffix=suffix):
                self.page.goto(self.url + suffix)
                self.assert_full_route()

    def test_itemizing_is_in_the_existing_second_question(self):
        steps = self.page.evaluate('INTAKE_STEPS.filter(s => s.id.startsWith("sf_")).map(s => ({id:s.id,question:s.question,help:s.help}))')
        self.assertEqual([s['id'] for s in steps], ['sf_other_income', 'sf_schedules'])
        self.assertIn('itemiz', steps[1]['question'].lower())
        self.assertIn('standard deduction', steps[1]['help'].lower())
        self.short_route('yes')  # A W-2 filer planning itemized deductions answers Yes.
        self.assert_full_route()
        self.assertEqual(self.answers()['sf_schedules'], 'yes')

    def test_uncertain_or_other_income_answers_use_full_form(self):
        for first, second in [('yes', None), ('unsure', None), ('no', 'unsure')]:
            with self.subTest(first=first, second=second):
                self.page.locator('#sfStart').click()
                self.step(first)
                if second:
                    self.step(second)
                self.assert_full_route()

    def test_partial_business_intake_cannot_take_shortcut(self):
        self.step('business_tax')
        self.step('s_corp')
        self.step('employees')
        previous = self.answers()
        self.short_route()
        self.assert_full_route()
        for key, value in previous.items():
            self.assertEqual(self.answers()[key], value)

    def test_partial_rental_intake_cannot_take_shortcut(self):
        self.step('individual_tax')
        self.step('rentals')
        previous = self.answers()
        self.short_route()
        self.assert_full_route()
        for key, value in previous.items():
            self.assertEqual(self.answers()[key], value)

    def test_user_can_correct_prior_rental_answer(self):
        self.step('individual_tax')
        self.step('rentals')
        self.short_route()
        self.assert_full_route()
        self.page.locator('#intakeForm button[type=submit]').click()
        self.page.locator('label.chip:has(input[value="rentals"])').click()
        self.step('w2')
        self.short_route()
        self.assertEqual(self.page.locator('[data-likely-fit]').count(), 1)

    def test_compatible_answers_contact_and_notes_survive_shortcut(self):
        seed = {'services': ['individual_tax'], 'individual_complexity': ['w2', 'multistate'],
                'urgency': 'no', 'notes': 'Synthetic note retained',
                'contact': {'name': 'Synthetic Prospect', 'email': 'review@example.invalid',
                            'phone': '', 'preferred': '', 'location': '', 'consent': True}}
        self.page.evaluate('(answers) => sessionStorage.setItem("satc_intake_v1", JSON.stringify({answers,currentId:"services"}))', seed)
        self.page.reload()
        self.short_route()
        self.assertEqual(self.page.locator('[data-likely-fit]').count(), 1)
        self.assertIn('Price confirmed upon review', self.page.locator('[data-likely-fit]').inner_text())
        self.page.locator('#lfGo').click()
        self.assertEqual(self.page.locator('input[name=name]').input_value(), seed['contact']['name'])
        self.page.locator('[data-back]').click()
        self.assertEqual(self.page.locator('[data-likely-fit]').count(), 1)
        self.page.locator('#lfGo').click()
        self.page.locator('#intakeForm button[type=submit]').click()
        self.page.locator('[data-restart]').wait_for()
        self.assertEqual(len(self.posts), 1)
        fields = dict(re.findall('name="([^"]+)"\r\n\r\n(.*?)\r\n--', self.posts[0], re.S))
        answers = json.loads(fields['_json'])
        for key, value in seed.items():
            self.assertEqual(answers[key], value)
        self.assertEqual(answers['sf_other_income'], 'no')
        self.assertEqual(answers['sf_schedules'], 'no')
        self.assertNotIn('price', answers)


if __name__ == '__main__':
    unittest.main(verbosity=2)
