"""Simple Filer regression checks; all submissions stay intercepted.

Run with the existing Playwright installation: python website/simple-filer.spec.py
Uses an ephemeral loopback server and the installed Chromium browser.

REWRITTEN 24 October 2026 for the one-door design. The earlier version of this
file tested a second door: a homepage button that set a window flag and jumped
the form to the short questions, a `?route=simple_filer` deep link, and "Not sure"
sending the visitor to the full form. A visitor who took that door and then
pressed "Tell Us About Your Situation" stayed stuck on the short question,
because that button only scrolls. The firm simplified it: every button opens the
same first question, the short questions follow only when individual tax is the
only service picked, and "Not sure" offers a choice. What these tests pin is that
the path is decided by what was ANSWERED and never by which button was pressed.
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
FIRST = 'What can we help'
Q_INCOME = 'Besides W-2s'
Q_SCHEDULES = 'itemize'
FULL_FORM = 'Which of these apply'


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
        self.offsite = []
        self.context = self.browser.new_context(service_workers='block')
        self.context.route('**/*', self.intercept)
        self.page = self.context.new_page()
        # A failure should fail in seconds, not sit out the 30-second default.
        self.page.set_default_timeout(5000)
        self.page.goto(self.url)

    def tearDown(self):
        self.context.close()

    def intercept(self, route):
        request = route.request
        if request.method not in ('GET', 'HEAD'):
            self.posts.append(request.post_data)
            route.fulfill(status=200, content_type='application/json',
                          headers={'access-control-allow-origin': '*'}, body='{"ok":true}')
        elif urlparse(request.url).netloc == urlparse(self.url).netloc:
            route.continue_()
        else:
            self.offsite.append(request.url)
            route.abort()

    # ---- helpers ---------------------------------------------------------
    def question(self):
        return self.page.locator('.wiz-q').inner_text()

    def cont(self):
        self.page.locator('#intakeForm button[type=submit]').click()

    def step(self, value):
        self.page.locator(f'label.chip:has(input[value="{value}"])').click()
        self.cont()

    def back(self):
        self.page.locator('[data-back]').click()

    def to_income_question(self):
        self.step('individual_tax')
        self.assertIn(Q_INCOME, self.question())

    def seed(self, answers, current):
        self.page.evaluate(
            '([a, c]) => sessionStorage.setItem("satc_intake_v1", JSON.stringify({answers:a, currentId:c}))',
            [answers, current])
        self.page.reload()

    def answers(self):
        return self.page.evaluate('JSON.parse(sessionStorage.getItem("satc_intake_v1")).answers')

    def on_likely_fit(self):
        return self.page.locator('[data-likely-fit]').count() == 1

    def on_not_sure(self):
        return self.page.locator('[data-not-sure]').count() == 1

    # ---- one door --------------------------------------------------------
    def test_every_door_opens_the_same_first_question(self):
        doors = ['a.btn.gold[href="#intake"]', 'a.nav-cta[href="#intake"]',
                 '#simple-filer a.btn[href="#intake"]']
        for sel in doors:
            with self.subTest(door=sel):
                self.page.goto(self.url)
                self.page.locator(sel).first.click()
                self.assertIn(FIRST, self.question())

    def test_band_then_general_button_is_not_a_second_path(self):
        """The reported bug: take the $100 door, then press the general button."""
        self.page.locator('#simple-filer a.btn[href="#intake"]').click()
        self.page.locator('a.btn.gold[href="#intake"]').click()
        self.assertIn(FIRST, self.question())

    def test_there_is_no_route_flag_or_deep_link(self):
        self.assertEqual(self.page.evaluate('typeof window.SATC_ENTER_SIMPLE_FILER'), 'undefined')
        self.assertEqual(self.page.evaluate('typeof window.__SATC_ROUTE'), 'undefined')
        for suffix in ('?route=simple_filer', '#route=simple_filer'):
            with self.subTest(suffix=suffix):
                self.page.goto(self.url + suffix)
                self.assertIn(FIRST, self.question())
                self.assertEqual(self.page.locator('input[name=sf_other_income]').count(), 0)

    # ---- who is asked ----------------------------------------------------
    def test_short_questions_only_follow_individual_tax_alone(self):
        steps = self.page.evaluate(
            'INTAKE_STEPS.filter(s => s.id.startsWith("sf_")).map(s => ({id:s.id,question:s.question,help:s.help}))')
        self.assertEqual([s['id'] for s in steps], ['sf_other_income', 'sf_schedules'])
        self.assertIn('itemiz', steps[1]['question'].lower())
        self.assertIn('standard deduction', steps[1]['help'].lower())
        for picks in (['business_tax'], ['individual_tax', 'bookkeeping'], ['tax_resolution']):
            with self.subTest(picks=picks):
                self.page.goto(self.url)
                self.page.evaluate('sessionStorage.clear()')
                self.page.reload()
                for value in picks:
                    self.page.locator(f'label.chip:has(input[value="{value}"])').click()
                self.cont()
                self.assertNotIn(Q_INCOME, self.question())

    # ---- the three answers -----------------------------------------------
    def test_yes_other_income_goes_straight_to_the_full_form(self):
        self.to_income_question()
        self.step('yes')
        self.assertIn(FULL_FORM, self.question())
        self.assertFalse(self.on_likely_fit() or self.on_not_sure())

    def test_itemizing_yes_goes_to_the_full_form_and_is_kept(self):
        self.to_income_question()
        self.step('no')
        self.assertIn(Q_SCHEDULES, self.question().lower())
        self.step('yes')  # a W-2 filer planning itemized deductions answers Yes
        self.assertIn(FULL_FORM, self.question())
        self.assertEqual(self.answers()['sf_schedules'], 'yes')

    def test_not_sure_offers_two_choices_and_quotes_nothing(self):
        for first, second in [('unsure', None), ('no', 'unsure')]:
            with self.subTest(first=first, second=second):
                self.page.goto(self.url)
                self.page.evaluate('sessionStorage.clear()')
                self.page.reload()
                self.to_income_question()
                self.step(first)
                if second:
                    self.step(second)
                self.assertTrue(self.on_not_sure())
                panel = self.page.locator('[data-not-sure]').inner_text()
                self.assertNotRegex(panel, r'\$|Simple Filer|Price confirmed')
                self.assertEqual(self.page.locator('#nsFull').count(), 1)
                self.assertEqual(self.page.locator('#nsReach').count(), 1)

    def test_not_sure_full_form_then_back_does_not_repeat_the_screen(self):
        self.to_income_question()
        self.step('unsure')
        self.page.locator('#nsFull').click()
        self.assertIn(FULL_FORM, self.question())
        self.back()
        self.assertIn(Q_INCOME, self.question())
        self.cont()
        self.assertIn(FULL_FORM, self.question())

    def test_not_sure_reach_out_goes_to_contact_and_back_returns(self):
        self.to_income_question()
        self.step('unsure')
        self.page.locator('#nsReach').click()
        self.assertEqual(self.page.locator('input[name=name]').count(), 1)
        self.back()
        self.assertTrue(self.on_not_sure())

    # ---- the likely fit --------------------------------------------------
    def test_no_and_no_shows_the_likely_fit_with_the_exact_disclaimer(self):
        self.to_income_question()
        self.step('no')
        self.step('no')
        self.assertTrue(self.on_likely_fit())
        text = self.page.locator('[data-likely-fit]').inner_text()
        self.assertIn('Price confirmed upon review.', text)
        self.assertRegex(text, r'\$100')

    def test_a_changed_answer_shows_the_right_screen_again(self):
        self.to_income_question()
        self.step('no')
        self.step('no')
        self.page.locator('#lfFull').click()
        self.assertIn(FULL_FORM, self.question())
        self.back()
        self.assertIn(Q_SCHEDULES, self.question().lower())
        self.step('yes')
        self.assertIn(FULL_FORM, self.question())
        self.assertFalse(self.on_likely_fit())

    # ---- existing answers are never erased -------------------------------
    def test_partial_business_intake_never_reaches_the_short_questions(self):
        self.step('business_tax')
        self.step('s_corp')
        self.step('employees')
        previous = self.answers()
        self.page.goto(self.url)
        self.page.locator('#simple-filer a.btn[href="#intake"]').click()
        self.assertEqual(self.page.locator('input[name=sf_other_income]').count(), 0)
        for key, value in previous.items():
            self.assertEqual(self.answers()[key], value)

    def test_prior_rental_answer_blocks_the_shortcut_and_can_be_corrected(self):
        self.seed({'services': ['individual_tax'], 'individual_complexity': ['rentals'],
                   'sf_other_income': 'no'}, 'sf_schedules')
        self.step('no')
        self.assertFalse(self.on_likely_fit())
        self.assertIn(FULL_FORM, self.question())
        self.page.locator('label.chip:has(input[value="rentals"])').click()   # untick
        self.page.locator('label.chip:has(input[value="w2"])').click()
        self.back()
        self.assertIn(Q_SCHEDULES, self.question().lower())
        self.cont()
        self.assertTrue(self.on_likely_fit())

    def test_compatible_answers_contact_and_notes_survive_the_shortcut(self):
        seed = {'services': ['individual_tax'], 'individual_complexity': ['w2', 'multistate'],
                'urgency': 'no', 'notes': 'Synthetic note retained',
                'contact': {'name': 'Synthetic Prospect', 'email': 'review@example.invalid',
                            'phone': '', 'preferred': '', 'location': '', 'consent': True}}
        self.seed(seed, 'services')
        self.cont()
        self.step('no')
        self.step('no')
        self.assertTrue(self.on_likely_fit())
        self.page.locator('#lfGo').click()
        self.assertEqual(self.page.locator('input[name=name]').input_value(), seed['contact']['name'])
        self.back()
        self.assertTrue(self.on_likely_fit())
        self.page.locator('#lfGo').click()
        self.cont()
        self.page.locator('[data-restart]').wait_for()
        self.assertEqual(len(self.posts), 1)
        fields = dict(re.findall('name="([^"]+)"\r\n\r\n(.*?)\r\n--', self.posts[0], re.S))
        answers = json.loads(fields['_json'])
        for key, value in seed.items():
            self.assertEqual(answers[key], value)
        self.assertEqual(answers['sf_other_income'], 'no')
        self.assertEqual(answers['sf_schedules'], 'no')
        self.assertNotIn('price', answers)

    # ---- housekeeping ----------------------------------------------------
    def test_the_banned_phrase_is_not_in_the_form(self):
        self.seed({}, 'contact')
        self.assertNotRegex(self.page.locator('.consent').inner_text().lower(), 'engagement letter')

    def test_phone_width_has_no_horizontal_overflow_on_the_new_screens(self):
        self.page.set_viewport_size({'width': 390, 'height': 900})
        self.to_income_question()
        self.step('unsure')
        self.assertTrue(self.on_not_sure())
        self.assertLessEqual(*self.page.evaluate('[document.documentElement.scrollWidth, innerWidth]'))
        self.page.locator('#nsFull').click()
        self.back()
        self.page.goto(self.url)
        self.page.evaluate('sessionStorage.clear()')
        self.page.reload()
        self.to_income_question()
        self.step('no')
        self.step('no')
        self.assertTrue(self.on_likely_fit())
        width, inner = self.page.evaluate('[document.documentElement.scrollWidth, innerWidth]')
        self.assertLessEqual(width, inner + 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
