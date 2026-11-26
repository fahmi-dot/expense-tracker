import os, sqlite3, tempfile
from app import create_app

def test_qa_probe():
    fd, path = tempfile.mkstemp(suffix='.sqlite3'); os.close(fd); os.unlink(path)
    app = create_app({'TESTING': True, 'DATABASE_PATH': path, 'SECRET_KEY': 'x'})
    c = app.test_client()
    base = {'expense_date':'2026-02-28','amount':'1000','category_id':'1','description':'Kopi, "pagi" ☕\nbaris'}
    print('add=', c.post('/expenses', data=base).status_code)
    for label, data in [('zero',{**base,'amount':'0'}), ('negative',{**base,'amount':'-1'}), ('fraction',{**base,'amount':'1.2'}), ('bad_calendar_date',{**base,'expense_date':'2026-02-30'}), ('noncanonical_date',{**base,'expense_date':'2026-2-3'}), ('missing_category',{**base,'category_id':'999'})]:
        print(label + '=', c.post('/expenses', data=data).status_code)
    with sqlite3.connect(path) as db: print('count_after_invalid=', db.execute('select count(*) from expenses').fetchone()[0])
    print('csv=', repr(c.get('/export.csv').data.decode()))
    print('used_category_delete=', c.post('/categories/1/delete', follow_redirects=True).status_code)
    print('missing_expense_delete=', c.post('/expenses/999/delete').status_code)
    print('missing_category_update=', c.post('/categories/999', data={'name':'X'}).status_code)
    print('missing_category_delete=', c.post('/categories/999/delete').status_code)
    for url in ['/reports/daily?date=notdate','/reports/monthly?month=2026-99','/expenses?date=notdate']:
        print(url + '=', c.get(url).status_code)
    os.unlink(path)
