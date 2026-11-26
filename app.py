import os, csv, io, sqlite3, secrets, calendar
from datetime import UTC, date, datetime
from flask import Flask, request, redirect, url_for, render_template, flash, g, Response, abort

BASE=os.path.dirname(__file__)
DEFAULT_CATS=['Makanan','Transportasi','Belanja','Tagihan','Kesehatan','Lainnya']
def create_app(test_config=None):
    app=Flask(__name__, template_folder='templates')
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(16), DATABASE_PATH=os.environ.get('DATABASE_PATH',os.path.join(BASE,'data','expenses.sqlite3')))
    if test_config: app.config.update(test_config)
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']),exist_ok=True)
    def db():
        if 'db' not in g:
            g.db=sqlite3.connect(app.config['DATABASE_PATH']); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON')
        return g.db
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection is not None: connection.close()
    app.teardown_appcontext(close_db)
    def init():
        d=db(); d.executescript('''CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,created_at TEXT NOT NULL); CREATE UNIQUE INDEX IF NOT EXISTS category_name ON categories(name COLLATE NOCASE); CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT,expense_date TEXT NOT NULL,category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,amount INTEGER NOT NULL CHECK(amount>0),description TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL); CREATE INDEX IF NOT EXISTS expense_date ON expenses(expense_date);''')
        for n in DEFAULT_CATS: d.execute('INSERT OR IGNORE INTO categories(name,created_at) VALUES(?,?)',(n,datetime.now(UTC).isoformat()))
        d.commit()
    with app.app_context(): init()
    def parse_form():
        errs={}; ds=request.form.get('expense_date','').strip(); amount=request.form.get('amount','').strip(); cid=request.form.get('category_id','').strip(); desc=request.form.get('description','').strip()
        try:
            parsed = datetime.strptime(ds,'%Y-%m-%d')
            if parsed.strftime('%Y-%m-%d') != ds: raise ValueError
        except (ValueError,TypeError): errs['expense_date']='Tanggal wajib dan harus berformat YYYY-MM-DD'
        try:
            if not amount.isdigit() or int(amount)<=0: raise ValueError
            av=int(amount)
        except ValueError: errs['amount']='Nominal harus bilangan bulat lebih besar dari 0'; av=0
        try: cv=int(cid); cat=db().execute('SELECT id FROM categories WHERE id=?',(cv,)).fetchone()
        except ValueError: cat=None; cv=0
        if not cat: errs['category_id']='Pilih kategori yang tersedia'
        if len(desc)>500: errs['description']='Keterangan maksimal 500 karakter'
        return errs, {'expense_date':ds,'amount':amount,'category_id':cid,'description':desc}, (ds,av,cv,desc)
    @app.template_filter('idr')
    def idr(v): return 'Rp' + f'{int(v):,}'.replace(',','.')
    @app.route('/')
    def home(): return redirect(url_for('expenses',date=request.args.get('date',date.today().isoformat())))
    @app.route('/expenses')
    def expenses():
        selected=request.args.get('date',date.today().isoformat()); rows=db().execute('SELECT e.*,c.name category FROM expenses e JOIN categories c ON c.id=e.category_id WHERE e.expense_date=? ORDER BY e.expense_date DESC,e.id DESC',(selected,)).fetchall(); total=sum(r['amount'] for r in rows); return render_template('list.html',rows=rows,total=total,selected=selected)
    @app.route('/expenses/new',methods=['GET'])
    def new_expense(): return render_template('form.html',item=None,categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall(),errors={},form={'expense_date':date.today().isoformat(),'amount':'','category_id':'','description':''})
    @app.route('/expenses',methods=['POST'])
    def add_expense():
        errors,form,vals=parse_form()
        if errors: return render_template('form.html',item=None,categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall(),errors=errors,form=form),400
        now=datetime.now(UTC).isoformat(); db().execute('INSERT INTO expenses(expense_date,amount,category_id,description,created_at,updated_at) VALUES(?,?,?,?,?,?)',(*vals[:3],vals[3],now,now)); db().commit(); flash('Pengeluaran tersimpan'); return redirect(url_for('expenses',date=vals[0]),303)
    @app.route('/expenses/<int:eid>/edit')
    def edit_expense(eid):
        item=db().execute('SELECT * FROM expenses WHERE id=?',(eid,)).fetchone()
        if not item: abort(404)
        return render_template('form.html',item=item,categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall(),errors={},form=dict(item))
    @app.route('/expenses/<int:eid>',methods=['POST'])
    def update_expense(eid):
        if not db().execute('SELECT id FROM expenses WHERE id=?',(eid,)).fetchone(): abort(404)
        errors,form,vals=parse_form()
        if errors: return render_template('form.html',item={'id':eid},categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall(),errors=errors,form=form),400
        db().execute('UPDATE expenses SET expense_date=?,amount=?,category_id=?,description=?,updated_at=? WHERE id=?',(*vals,datetime.now(UTC).isoformat(),eid)); db().commit(); return redirect(url_for('expenses',date=vals[0]),303)
    @app.route('/expenses/<int:eid>/delete',methods=['POST'])
    def delete_expense(eid):
        item=db().execute('SELECT e.*, c.name category FROM expenses e JOIN categories c ON c.id=e.category_id WHERE e.id=?',(eid,)).fetchone()
        if not item: abort(404)
        if request.form.get('confirm')!='yes': return render_template('confirm_delete.html',item=item)
        db().execute('DELETE FROM expenses WHERE id=?',(eid,)); db().commit()
        return redirect(url_for('expenses'))
    @app.route('/categories',methods=['GET','POST'])
    def categories():
        if request.method=='POST':
            n=request.form.get('name','').strip(); err='Nama kategori wajib diisi' if not n else ('Nama kategori maksimal 100 karakter' if len(n)>100 else '')
            if not err and db().execute('SELECT 1 FROM categories WHERE name=? COLLATE NOCASE',(n,)).fetchone(): err='Nama kategori sudah digunakan'
            if err: flash(err,'error'); return render_template('categories.html',categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall()),400
            db().execute('INSERT INTO categories(name,created_at) VALUES(?,?)',(n,datetime.now(UTC).isoformat())); db().commit(); return redirect(url_for('categories'),303)
        return render_template('categories.html',categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall())
    @app.route('/categories/<int:cid>',methods=['POST'])
    def update_category(cid):
        if not db().execute('SELECT 1 FROM categories WHERE id=?',(cid,)).fetchone(): abort(404)
        n=request.form.get('name','').strip()
        if not n or len(n)>100 or db().execute('SELECT 1 FROM categories WHERE name=? COLLATE NOCASE AND id<>?',(n,cid)).fetchone(): flash('Nama kategori kosong, terlalu panjang, atau sudah digunakan','error'); return redirect(url_for('categories'))
        db().execute('UPDATE categories SET name=? WHERE id=?',(n,cid)); db().commit(); return redirect(url_for('categories'))
    @app.route('/categories/<int:cid>/delete',methods=['POST'])
    def delete_category(cid):
        if not db().execute('SELECT 1 FROM categories WHERE id=?',(cid,)).fetchone(): abort(404)
        if db().execute('SELECT 1 FROM expenses WHERE category_id=?',(cid,)).fetchone(): flash('Kategori masih digunakan oleh transaksi dan tidak dapat dihapus','error'); return redirect(url_for('categories'))
        db().execute('DELETE FROM categories WHERE id=?',(cid,)); db().commit(); return redirect(url_for('categories'))
    @app.route('/reports/daily')
    def daily():
        d=request.args.get('date',date.today().isoformat())
        try:
            parsed=datetime.strptime(d,'%Y-%m-%d')
            if parsed.strftime('%Y-%m-%d') != d: raise ValueError
        except (ValueError,TypeError): abort(400)
        rows=db().execute('SELECT e.*,c.name category FROM expenses e JOIN categories c ON c.id=e.category_id WHERE expense_date=?',(d,)).fetchall(); return render_template('daily.html',selected=d,rows=rows,total=sum(x['amount'] for x in rows))
    @app.route('/reports/monthly')
    def monthly():
        m=request.args.get('month',date.today().strftime('%Y-%m'))
        try:
            parsed=datetime.strptime(m,'%Y-%m')
            if parsed.strftime('%Y-%m') != m: raise ValueError
        except (ValueError,TypeError): abort(400)
        rows=db().execute("SELECT c.name category,SUM(e.amount) total FROM expenses e JOIN categories c ON c.id=e.category_id WHERE substr(e.expense_date,1,7)=? GROUP BY c.id ORDER BY c.name",(m,)).fetchall(); return render_template('monthly.html',selected=m,rows=rows,total=sum(x['total'] for x in rows))
    @app.route('/export.csv')
    def export_csv():
        q='SELECT e.expense_date,c.name,e.amount,e.description FROM expenses e JOIN categories c ON c.id=e.category_id'; args=[]; month=request.args.get('month'); f=request.args.get('date_from'); t=request.args.get('date_to')
        if month:
            try: datetime.strptime(month,'%Y-%m'); q+=' WHERE substr(e.expense_date,1,7)=?'; args.append(month)
            except ValueError: abort(400)
        elif f or t:
            try: datetime.strptime(f,'%Y-%m-%d'); datetime.strptime(t,'%Y-%m-%d')
            except (ValueError,TypeError): abort(400)
            if f>t: abort(400)
            q+=' WHERE e.expense_date BETWEEN ? AND ?'; args += [f,t]
        rows=db().execute(q+' ORDER BY e.expense_date,e.id',args).fetchall(); out=io.StringIO(newline=''); w=csv.writer(out); w.writerow(['tanggal','kategori','nominal','keterangan']); w.writerows([tuple(r) for r in rows]); return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=pengeluaran.csv'})
    return app
app=create_app()
if __name__=='__main__': app.run(host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT',5000)),debug=False)
