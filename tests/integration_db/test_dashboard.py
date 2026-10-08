"""Browser flows use the real FastAPI and disposable Supabase services."""
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright, expect

from .test_session_access import access, draft, ingest, packet

pytestmark = pytest.mark.database


def test_browser_registration_approval_login_and_authorized_history(access):
    a = access
    teacher, _, _ = a['register']('teacher', a['schools'][0])
    admin, _, admin_email = a['register']('admin')
    email = 'test-browser-'+uuid4().hex+'@example.com'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(a['url'])
        page.get_by_label('Email', exact=True).fill(email)
        page.get_by_label('Password', exact=True).fill('TEST-browser-password')
        page.get_by_role('button', name='Register', exact=True).click()
        expect(page.get_by_text(
            'Awaiting administrator approval', exact=True)).to_be_visible()
        uid = a['admin'].execute(
            'SELECT user_id FROM tlm.user_profiles WHERE email=%s', (email,)).fetchone()[0]
        # Track browser-created data for fixture cleanup.
        a['track_user'](uid)
        page.get_by_role('button', name='Log out', exact=True).click()
        page.get_by_label('Email', exact=True).fill(admin_email)
        page.get_by_label('Password', exact=True).fill(a['password'])
        page.get_by_role('button', name='Log in', exact=True).click()
        row = page.get_by_role('row').filter(has_text=email)
        row.get_by_label('Role').select_option('student')
        row.get_by_label('School').select_option(str(a['schools'][0]))
        row.get_by_label('Status').select_option('approved')
        row.get_by_role('button', name='Save').click()
        expect(row.get_by_text('Saved', exact=True)).to_be_visible()
        session = draft(teacher, a['schools'][0], [uid], a['devices'][:1])
        assert teacher.post('/v1/sessions/'+session +
                            '/start').status_code == 200
        assert ingest(a, packet(a['devices'][0], session)).status_code == 201
        page.get_by_role('button', name='Log out', exact=True).click()
        page.get_by_label('Email', exact=True).fill(email)
        page.get_by_label('Password', exact=True).fill('TEST-browser-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        page.get_by_role('button', name='Open', exact=True).click()
        expect(page.get_by_role(
            'cell', name='test_sensor: 42', exact=True)).to_be_visible()
        expect(page.get_by_role('heading', name='User access')).to_have_count(0)
        expect(page.get_by_role('button', name='Start',
               exact=True)).to_have_count(0)
        page.screenshot(path='var/dashboard-student.png', full_page=True)
        context.close()
        browser.close()


def test_teacher_browser_creates_starts_and_confirms_session(access):
    a = access
    _, _, teacher_email = a['register']('teacher', a['schools'][0])
    _, student, _ = a['register']('student', a['schools'][0])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(a['url'])
        page.get_by_label('Email', exact=True).fill(teacher_email)
        page.get_by_label('Password', exact=True).fill(a['password'])
        page.get_by_role('button', name='Log in', exact=True).click()
        page.get_by_label('Session name').fill('TEST browser group')
        page.get_by_label('Session school').select_option(str(a['schools'][0]))
        page.get_by_label('Students', exact=True).select_option(str(student))
        page.get_by_label('Devices', exact=True).select_option(
            str(a['devices'][0]))
        page.get_by_role('button', name='Create draft').click()
        page.get_by_role('button', name='Start', exact=True).click()
        expect(page.get_by_role('cell', name='active', exact=True)).to_be_visible()
        session = a['admin'].execute(
            'SELECT session_id FROM tlm.sessions WHERE school_id=%s', (a['schools'][0],)).fetchone()[0]
        expect(page.get_by_role(
            'cell', name='Awaiting packet', exact=True)).to_be_visible()
        assert ingest(a, packet(a['devices'][0],
                      str(session))).status_code == 201
        page.get_by_role('button', name='Refresh', exact=True).click()
        expect(page.get_by_role(
            'cell', name='Packet confirmed', exact=True)).to_be_visible()
        page.screenshot(path='var/dashboard-teacher.png', full_page=True)
        page.get_by_role('button', name='End', exact=True).click()
        expect(page.get_by_role('cell', name='ended', exact=True)).to_be_visible()
        browser.close()
