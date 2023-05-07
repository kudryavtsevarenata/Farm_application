from flask import Flask, render_template, url_for, flash, redirect, request
import pymysql
from forms import LoginForm
import bcrypt
from conf import host, user, password, db_name

app = Flask(__name__)
connection = pymysql.connect(host = host, user = user, port=3306, password= password, database = db_name, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()
is_less_limit = dict()
app.config['SECRET_KEY'] = 'super_long_and_secret_key'
session = dict()

@app.route('/')
def index():
    apts = "SELECT * FROM apteka"
    cursor.execute(apts)
    result = cursor.fetchall()
    return render_template('main_page.html', query=result, session=session)

@app.route('/single/<int:apt_id>', methods=['GET', 'POST'])
def single_page(apt_id):
    name_apt = "select name_apt from apteka where id_apt = %s"
    cursor.execute(name_apt, (apt_id,))
    name_apt = cursor.fetchall()
    lecs = "select l.id_lec, l.lec_name, l.form, a.kolichestvo from lecarstvo as l " + \
    "join assort as a on l.id_lec = a.id_lec where id_apt = " + str(apt_id) + ";"
    cursor.execute(lecs)
    lecs = cursor.fetchall()
    return render_template('single_apt.html', query=lecs, name_apt=name_apt, session=session)


@app.route('/lec/<int:lec_id>', methods=['GET', 'POST'])
def lec_page(lec_id):
    inf_about_ingr = "select l.lec_name, i.name_ingr, r.kolich_vesh, ps.psevd from receptura as r " + \
    "join ingredient as i using (id_ingr) join lecarstvo as l using (id_lec) left join pseudonim as ps using(id_lec) where id_lec = %s"
    cursor.execute(inf_about_ingr, (lec_id, ))
    inf_about_ingr = cursor.fetchall()
    pseudonims = "select * from lecarstvo join pseudonim using(id_lec) where id_lec = %s"
    cursor.execute(pseudonims, (lec_id, ))
    pseudonims = cursor.fetchall()
    return render_template('single_lec.html', session=session,inf_about_ingr=inf_about_ingr, pseudonims=pseudonims)


@app.route('/log', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        user = "SELECT * FROM user_table WHERE name = %s"
        cursor.execute(user, (form.username.data, ))
        user = cursor.fetchone()
        if user:
            passw = user['password']
            hashAndSalt = bcrypt.hashpw(passw.encode(), bcrypt.gensalt())
            # print(hashAndSalt)
            valid = bcrypt.checkpw(form.password.data.encode(), passw.encode())
            if user and valid:
                session['logged_in'] = True
                session['id'] = user['id']
                session['name'] = user['name']
                session['adm'] = user['is_admin']
                session['id_apt'] = user['id_main_apt']
                name_user = user['name']
                flash(f'Вы вошли под именем: {name_user}', category='success')
                return redirect(url_for('farm_page', apt_id = session['id_apt']))
            else:
                flash(f'Имя или пароль неверны! Попробуйте снова', category='danger')
        else:
            flash(f'Имя или пароль неверны! Попробуйте снова', category='danger')
    return render_template('log.html', form=form, session=session)

@app.route('/logout')
def logout_page():
    session.clear()
    flash(f'Вы вышли', category='danger')
    return redirect(url_for('index'))


@app.route('/farm-page/<int:apt_id>', methods=['GET', 'POST'])
def farm_page(apt_id):
    lecs = "select *, " + \
        "DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo as l using(id_lec) " + \
        "join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s"
    cursor.execute(lecs, (apt_id, ))
    lecs = cursor.fetchall()
    for lec in lecs:
        if lec['kolichestvo'] < lec['min_limit']:
            is_less_limit[lec['id_lec']] = False
        else:
            is_less_limit[lec['id_lec']] = True
    counter = 0
    s = list(request.form.values())
    ids = request.form.keys()
    if bool(ids):
        if (next(reversed(ids)) == 'sell_lec'):
            for i in ids:
                if i != 'sell_lec':
                    decr = "update assort join apteka using(id_apt) set kolichestvo = kolichestvo - %s where id_lec = %s and id_apt = %s;"
                    cursor.execute(decr, (s[counter], i[4], apt_id))
                    counter += 1
                    connection.commit()
        

    #for elem in request.args.to_dict():
    #    if elem != 'sell_lec':
    #        print("id", end=": ")
    #        print(elem[4])
    #        print(request.args.get(elem))
    #        decr = "update assort join apteka using(id_apt) set kolichestvo = kolichestvo - %s where id_lec = %s and id_apt = %s;"
    #        cursor.execute(decr, (request.args.get(elem), elem[4], apt_id))
    name_apt = "select name_apt from apteka where id_apt = %s"
    cursor.execute(name_apt, (apt_id, ))
    name_apt = cursor.fetchall()
    lecs = "select *, " + \
        "DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo as l using(id_lec) " + \
        "join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s"
    cursor.execute(lecs, (apt_id, ))
    lecs = cursor.fetchall()
    # print(is_less_limit)
    
    prov = "select *, " + \
        "DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo as l using(id_lec) " + \
        "join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s"
    cursor.execute(prov, (apt_id, ))
    prov = cursor.fetchall()
    for p in prov:
        if p['kolichestvo'] < p['min_limit'] and is_less_limit[p['id_lec']] == True:
            insertion = "Insert into zayavka (id_lec, kolich) values(%s, %s)"
            cursor.execute(insertion, (p['id_lec'], p['min_limit'] * 2))
            connection.commit()
            id_last_zayav = "select * from zayavka where id_lec = %s order by id_zayav desc limit 1;"
            cursor.execute(id_last_zayav, (p['id_lec'],))
            id_last_zayav = cursor.fetchone()
            insertion_in_zayav_assort = "insert into zayavka_assort(id_zayav, id_asort) values (%s, %s)"
            cursor.execute(insertion_in_zayav_assort, (id_last_zayav['id_zayav'], p['id_asort']))
            connection.commit()
            flash('Автоматически создана заявка', category='success')
        if (p['kolichestvo'] == 0):
            num_asort = p['id_asort']
            updating_asort = "select * from zayavka_assort join zayavka using(id_zayav) join lecarstvo using(id_lec) join assort using(id_asort) where id_asort = %s;"
            cursor.execute(updating_asort, (num_asort, ))
            updating_asort = cursor.fetchone()
            updating_lec = "update assort set kolichestvo = %s, data_partii = %s where id_lec = %s"
            cursor.execute(updating_lec, (updating_asort['kolich'], updating_asort['data_partii_z'], p['id_lec']))
            connection.commit()
            deleting = "delete from zayavka_assort where id_zayav = %s"
            cursor.execute(deleting, (updating_asort['id_zayav'], ))
            connection.commit()
            deleting = "delete from zayavka where id_zayav = %s"
            cursor.execute(deleting, (updating_asort['id_zayav'], ))
            connection.commit()
            flash('Ассортимент автоматически обновлен', category='success')
            return redirect(url_for('farm_page', apt_id = session['id_apt']))
    connection.commit()
    return render_template('farm_page.html', session=session, name_apt=name_apt, lecs=lecs)


@app.route('/farm-out-of-days/<int:apt_id>', methods=['GET', 'POST'])
def out_of_days(apt_id):
    lecs = "select *, " + \
        " DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo " + \
            "as l using(id_lec) join apteka as ap using(id_apt) where " + \
            "DATE_ADD(a.data_partii, Interval l.srok day) <= current_date() and id_apt = %s"
    cursor.execute(lecs, (apt_id, ))
    lecs = cursor.fetchall()
    is_pressed = request.form.keys()
    if (bool(is_pressed)):
        for lec in lecs:
            id_assort = lec['id_asort']
            deleting = "delete from assort where id_asort = %s;"
            cursor.execute(deleting, (id_assort, ))
            connection.commit()
            flash('Записи о просроченных партиях удалены', category='success')
    name_apt = "select name_apt from apteka where id_apt = %s"
    cursor.execute(name_apt, (apt_id, ))
    name_apt = cursor.fetchall()
    lecs = "select a.kolichestvo, a.data_partii, l.lec_name, l.id_lec, l.srok, l.min_limit, " + \
        "l.form, DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo " + \
            "as l using(id_lec) join apteka as ap using(id_apt) where " + \
            "DATE_ADD(a.data_partii, Interval l.srok day) <= current_date() and id_apt = %s"
    cursor.execute(lecs, (apt_id, ))
    lecs = cursor.fetchall()
    return render_template('out_days_page.html', session=session, name_apt=name_apt, lecs=lecs)


@app.route('/patients')
def patients_page():
    patients = "select * from all_patient_info;"
    cursor.execute(patients)
    patients = cursor.fetchall()
    return render_template('patients.html', session=session, patients=patients)


@app.route('/diag/<int:id_pat>', methods=['GET', 'POST'])
def diag_page(id_pat):
    diag = "select p.surname, p.name, p.fathername, dp.diag_type, d.name_diag, p.birth_data, " + \
        "timestampdiff(year, p.birth_data, current_date() ) as age from patient as p join diagnoz_patient " + \
        "as dp using(id_pac) join diagnoz as d using (id_diag) where id_pac = %s"
    cursor.execute(diag, (id_pat, ))
    diag = cursor.fetchall()
    recept_lec = "select * from recept join sost_recept using(id_recept) join lecarstvo " + \
        "using(id_lec) join vrach using(id_doc) where id_pac = %s"
    cursor.execute(recept_lec, (id_pat, ))
    recept_lec = cursor.fetchall()
    lgot_info = "select * from all_patient_info join lgot_patient using (id_pac) join lgota using(id_lgot) where id_pac = %s;"
    cursor.execute(lgot_info, (id_pat, ))
    lgot_info = cursor.fetchall()
    return render_template('diag_page.html', session=session, diag=diag, recept_lec=recept_lec, lgot_info=lgot_info)


@app.route('/zayav/<int:id_apt>')
def zayav_page(id_apt):
    zayav = "select * from zayavka_assort join zayavka using (id_zayav) join lecarstvo using(id_lec)" + \
         "join assort using (id_asort) join apteka using(id_apt) where id_apt = %s"
    cursor.execute(zayav, (id_apt,))
    zayav = cursor.fetchall()
    return render_template('zayav_page.html', session=session, zayav=zayav)


@app.route('/otch/<int:id_apt>')
def otch_page(id_apt): 
    otch = "select * from uchet join apteka join lecarstvo where uchet.id_apt_uch = apteka.id_apt and uchet.id_lec_uch = lecarstvo.id_lec and id_apt = %s  order by sell_date desc;"
    cursor.execute(otch, (id_apt, ))
    otch = cursor.fetchall()
    return render_template('otch_page.html', session=session, otch=otch)

@app.route('/adding/<int:id_apt>', methods=['GET', 'POST'])
def adding_page(id_apt):
    s = list(request.form.values())
    if bool(s):
        for i in range(0, len(s)):
            if 'on' in s[i]:
                id_adding = s[i][2]
                count = s[i + 1]
                print(id_adding, count)
                insertion = "insert into assort(id_apt, id_lec, kolichestvo, data_partii) values (%s, %s, %s, current_date());"
                cursor.execute(insertion, (session['id_apt'], id_adding, count))
                connection.commit()
        return redirect(url_for('farm_page', apt_id = session['id_apt']))
    assort_ids = "select * from assort where id_apt = %s;"
    cursor.execute(assort_ids, (id_apt, ))
    assort_ids = cursor.fetchall()
    list_lec = list()
    for elem in assort_ids:
        list_lec.append(elem['id_lec'])
    condition = "where "
    for i in range(0, len(list_lec)):
        if i != len(list_lec) - 1:
            condition = condition + " id_lec != " + str(list_lec[i]) + " and "
        else:
            condition = condition + " id_lec != " + str(list_lec[i]) + ";"
    opp_lec = "select * from lecarstvo " + condition
    cursor.execute(opp_lec)
    opp_lec = cursor.fetchall()
    return render_template('adding_lec.html', session=session, opp_lec=opp_lec)


@app.route('/del/<int:id_apt>', methods=['GET', 'POST'])
def del_page(id_apt):
    s = list(request.form.values())
    if bool(s):
        for i in range(0, len(s)):
            if 'on' in s[i]:
                id_del = s[i][2]
                deleting = "delete from assort where id_apt = %s and id_lec = %s;"
                cursor.execute(deleting, (session['id_apt'], id_del))
                connection.commit()
        return redirect(url_for('farm_page', apt_id = session['id_apt']))
    opp_lec = "select * " + \
        " from assort join lecarstvo using(id_lec) " + \
        "join apteka using(id_apt) where id_apt = %s"
    cursor.execute(opp_lec, (id_apt, ))
    opp_lec = cursor.fetchall()
    return render_template('deleting_lec.html', session=session, opp_lec=opp_lec)



@app.route('/sell_lec_for_pat/<int:id_pat>', methods=['GET', 'POST'])
def sell_lec_pat(id_pat):
    lecs = "select *, " + \
        "DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo as l using(id_lec) " + \
        "join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s"
    cursor.execute(lecs, (session['id_apt'], ))
    lecs = cursor.fetchall()
    for lec in lecs:
        if lec['kolichestvo'] < lec['min_limit']:
            is_less_limit[lec['id_lec']] = False
        else:
            is_less_limit[lec['id_lec']] = True
    counter = 0
    s = list(request.form.values())
    ids = request.form.keys()
    if bool(ids):
        print(ids)
        print(s)
        if (next(reversed(ids)) == 'sell_lec_for_pat'):
            for i in ids:
                if i != 'sell_lec_for_pat':
                    decr = "update assort join apteka using(id_apt) set kolichestvo = kolichestvo - %s where id_lec = %s and id_apt = %s;"
                    cursor.execute(decr, (s[counter], i[4], session['id_apt']))
                    counter += 1
                    connection.commit()
            flash('Продажа совершена', category='success')
    recepts = "select * from patient join recept using (id_pac) join sost_recept using(id_recept) where end_recept_date >= current_date() and id_pac = %s;"
    cursor.execute(recepts, (id_pat, ))
    recepts = cursor.fetchall()
    condition = " and ("
    for i in range(0, len(recepts)):
        id_lec = recepts[i]['id_lec']
        if i == len(recepts) - 1:
            condition += " id_lec = " + str(id_lec) + ");" 
        else:
            condition += " id_lec = " + str(id_lec) + " or "
    lecs = "select *, DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo " + \
    " as l using(id_lec) join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s" + condition
    cursor.execute(lecs, (session['id_apt'], ) )
    lecs = cursor.fetchall()

    prov = "select *, " + \
        "DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo as l using(id_lec) " + \
        "join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) > current_date() and id_apt = %s"
    cursor.execute(prov, (session['id_apt'], ))
    prov = cursor.fetchall()
    for p in prov:
        if p['kolichestvo'] < p['min_limit'] and is_less_limit[p['id_lec']] == True:
            insertion = "Insert into zayavka (id_lec, kolich) values(%s, %s)"
            cursor.execute(insertion, (p['id_lec'], p['min_limit'] * 2))
            connection.commit()
            id_last_zayav = "select * from zayavka where id_lec = %s order by id_zayav desc limit 1;"
            cursor.execute(id_last_zayav, (p['id_lec'],))
            id_last_zayav = cursor.fetchone()
            insertion_in_zayav_assort = "insert into zayavka_assort(id_zayav, id_asort) values (%s, %s)"
            cursor.execute(insertion_in_zayav_assort, (id_last_zayav['id_zayav'], p['id_asort']))
            connection.commit()
            flash('Автоматически создана заявка', category='success')
        if (p['kolichestvo'] == 0):
            num_asort = p['id_asort']
            updating_asort = "select * from zayavka_assort join zayavka using(id_zayav) join lecarstvo using(id_lec) join assort using(id_asort) where id_asort = %s;"
            cursor.execute(updating_asort, (num_asort, ))
            updating_asort = cursor.fetchone()
            updating_lec = "update assort set kolichestvo = %s, data_partii = %s where id_lec = %s"
            cursor.execute(updating_lec, (updating_asort['kolich'], updating_asort['data_partii_z'], p['id_lec']))
            connection.commit()
            deleting = "delete from zayavka_assort where id_zayav = %s"
            cursor.execute(deleting, (updating_asort['id_zayav'], ))
            connection.commit()
            deleting = "delete from zayavka where id_zayav = %s"
            cursor.execute(deleting, (updating_asort['id_zayav'], ))
            connection.commit()
            flash('Ассортимент автоматически обновлен', category='success')
            return redirect(url_for('sell_lec_pat', id_pat=id_pat))
    connection.commit()
    return render_template('sell_lec_for_pat.html', session=session, lecs=lecs, recept=recepts[0])


@app.route('/quer<int:param>')
def query_page(param):
    q = str()
    if param == 1:
        q = "select * from patient join lgot_patient using (id_pac) join lgota using(id_lgot);"
    elif param == 2:
        q = "select * from lecarstvo where id_lec not in (select id_lec from pseudonim);"
    elif param == 3:
        q = "select *, DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo " + \
            " as l using(id_lec) join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) >= current_date() and id_apt = 1;"
    elif param == 4:
        q = "select * from vrach where id_doc in (select id_doc from recept);"
    elif param == 5:
        q = "select *, DATE_ADD(a.data_partii, Interval l.srok day) as dat from assort as a join lecarstvo " + \
            " as l using(id_lec) join apteka as ap using(id_apt) where DATE_ADD(a.data_partii, Interval l.srok day) < current_date() and id_apt = 1;"
    elif param == 6:
        q = "select SUM(kolichestvo) as s from assort where id_apt = 1;"
    elif param == 7:
        q = "select * from patient join diagnoz_patient using(id_pac) join diagnoz using(id_diag) where diag_type = 'сопутствующий';"
    elif param == 8:
        q = "select * from lecarstvo where form = 'ампулы';"
    elif param == 9:
        q = "select * from apteka where tip_apt = 'муниципальная';"
    else:
        q = "select * from zayavka_assort join zayavka using (id_zayav) join lecarstvo using(id_lec)" + \
         "join assort using (id_asort) join apteka using(id_apt) where id_apt = 1"
    cursor.execute(q)
    q = cursor.fetchall()
    return render_template('zapros.html', q = q, param=param)



if __name__ == "__main__":
    app.run(debug=True)