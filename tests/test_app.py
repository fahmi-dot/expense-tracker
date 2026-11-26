import os, pytest, sqlite3
from app import create_app

@pytest.fixture
def client():
    db_path = 'data/test.sqlite3'
    app = create_app({'TESTING': True, 'DATABASE_PATH': db_path, 'SECRET_KEY': 'test'})
    with app.test_client() as client:
        with app.app_context(): pass
        yield client
    if os.path.exists(db_path): os.remove(db_path)

def test_categories(client):
    rv = client.get('/categories')
    assert b'Makanan' in rv.data
    client.post('/categories', data={'name': 'Hiburan'})
    assert b'Hiburan' in client.get('/categories').data
    rv = client.post('/categories', data={'name': 'Hiburan'})
    assert rv.status_code == 400

def test_expenses(client):
    client.post('/expenses', data={'expense_date':'2026-11-26', 'amount':'50000', 'category_id':'1', 'description':'Nasi Padang'})
    rv = client.get('/expenses?date=2026-11-26')
    assert b'50.000' in rv.data
    assert b'Nasi Padang' in rv.data
    client.post('/expenses', data={'expense_date':'2026-11-26', 'amount':'-10', 'category_id':'1'}, follow_redirects=True)
    assert b'Nominal harus bilangan bulat lebih besar dari 0' in client.post('/expenses', data={'expense_date':'2026-11-26', 'amount':'-10', 'category_id':'1'}).data

def test_reports(client):
    client.post('/expenses', data={'expense_date':'2026-11-26', 'amount':'1000', 'category_id':'1', 'description':'x'})
    client.post('/expenses', data={'expense_date':'2026-11-27', 'amount':'2000', 'category_id':'2', 'description':'y'})
    assert b'1.000' in client.get('/reports/daily?date=2026-11-26').data
    assert b'3.000' in client.get('/reports/monthly?month=2026-11').data

def test_qa_regressions(client):
    base = {'expense_date':'2026-02-28','amount':'1000','category_id':'1'}
    assert client.post('/expenses', data={**base, 'expense_date':'2026-2-3'}).status_code == 400
    assert client.post('/expenses', data=base).status_code == 303
    assert client.post('/expenses/999/delete').status_code == 404
    assert client.post('/categories/999', data={'name':'X'}).status_code == 404
    assert client.post('/categories/999/delete').status_code == 404
    assert client.get('/reports/daily?date=notdate').status_code == 400
    assert client.get('/reports/monthly?month=2026-99').status_code == 400
    assert client.get('/reports/monthly?month=2026-2').status_code == 400
    response = client.post('/expenses/1/delete')
    assert response.status_code == 200 and b'Batal' in response.data
    assert client.get('/expenses?date=2026-02-28').status_code == 200
    assert client.post('/expenses/1/delete', data={'confirm':'yes'}).status_code == 302
    assert client.get('/expenses/1/edit').status_code == 404

def test_export(client):
    client.post('/expenses', data={'expense_date':'2026-11-26', 'amount':'1500', 'category_id':'1', 'description':'csv-test'})
    rv = client.get('/export.csv')
    assert b'csv-test' in rv.data
    assert b'tanggal,kategori,nominal,keterangan' in rv.data
