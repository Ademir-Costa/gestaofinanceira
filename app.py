from forms import EditGoalForm  # lá no topo do app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from database import init_db, add_entry, get_entries, delete_entry, get_goals, update_goal, delete_goal, add_to_goal, add_goal 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import flash
import io
import sqlite3
from datetime import datetime
import os
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_wtf.csrf import CSRFProtect
from forms import EntryForm, GoalForm
from flask_wtf.csrf import generate_csrf
from flask_wtf.csrf import CSRFError




app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'sua_chave_secreta_aqui'
csrf = CSRFProtect(app)


# Configurações
DATABASE_PATH = 'instance/finance.db'

# Inicializa o banco de dados
init_db()
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,  # Adicionada esta linha
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            installments INTEGER DEFAULT 1
        )
    ''')
    
    # Cria tabela de metas (se já não existir)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            target_date TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def format_date_for_display(date_str):
    """Converte data do banco (YYYY-MM-DD) para DD/MM/AAAA"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return date_str

def format_date_for_db(date_str):
    """Converte data de DD/MM/AAAA para YYYY-MM-DD"""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return date_str

# Rotas principais
@app.route('/')
def index():
    try:
        entries = get_entries()
        formatted_entries = []
        
        for entry in entries:
            formatted_entry = list(entry)
            formatted_entry[1] = format_date_for_display(entry[1])
            formatted_entries.append(formatted_entry)
        
        current_month = datetime.now().strftime("%Y-%m")
        total_income = sum(e[3] for e in entries 
                          if e[4].lower() == 'receita' 
                          and e[1].startswith(current_month))
        total_expense = sum(e[3] for e in entries 
                           if e[4].lower() == 'despesa' 
                           and e[1].startswith(current_month))
        balance = total_income - total_expense
        
        return render_template('index.html', 
                            entries=formatted_entries[-10:],
                            total_income=total_income,
                            total_expense=total_expense,
                            balance=balance)
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('index.html', 
                            entries=[],
                            total_income=0,
                            total_expense=0,
                            balance=0)

@app.route('/add', methods=['GET', 'POST'])
def add_entry_route():
    form = EntryForm()
    
    if form.validate_on_submit():
        try:
            date = format_date_for_db(form.date.data)
            category = form.category.data.strip()
            amount = float(form.amount.data)
            entry_type = form.type.data.lower()
            installments = int(form.installments.data or 1)
            
            # Validações
            if not category:
                flash('Categoria não pode estar vazia!', 'danger')
                return redirect(url_for('add_entry_route'))
            
            if amount <= 0:
                flash('Valor deve ser positivo!', 'danger')
                return redirect(url_for('add_entry_route'))
            
            if entry_type not in ('receita', 'despesa'):
                flash('Tipo de entrada inválido!', 'danger')
                return redirect(url_for('add_entry_route'))
            
            add_entry(date, category, amount, entry_type, installments)
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('index'))
            
        except ValueError as e:
            flash(f'Erro nos dados: {str(e)}', 'danger')
    
    # Pass categories to template
    categories = {
        'receitas': ['Salário', 'Investimentos', 'Freelance', 'Outros'],
        'despesas': ['Alimentação', 'Transporte', 'Moradia', 'Lazer', 'Saúde', 'Educação', 'Outros']
    }
    
    return render_template('add_entry.html', form=form, categories=categories)

@app.route('/delete/<int:entry_id>')
def delete_entry_route(entry_id):
    delete_entry(entry_id)
    return redirect(url_for('index'))

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry_route(entry_id):
    # Conexão com o banco de dados
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Verificar se a entrada existe
        cursor.execute('SELECT id FROM entries WHERE id = ?', (entry_id,))
        if not cursor.fetchone():
            flash('Registro não encontrado!', 'danger')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            # Validação do token CSRF
            if not request.form.get('csrf_token') or request.form.get('csrf_token') != csrf._get_token():
                flash('Token de segurança inválido!', 'danger')
                return redirect(url_for('index'))
            
            try:
                # Processar e validar os dados do formulário
                date_str = request.form.get('date', '').strip()
                description = request.form.get('description', '').strip()
                category = request.form.get('category', '').strip()
                amount_str = request.form.get('amount', '0').strip()
                entry_type = request.form.get('type', '').lower()
                installments_str = request.form.get('installments', '1').strip()
                
                # Validações básicas
                if not all([date_str, description, category, amount_str, entry_type]):
                    flash('Todos os campos obrigatórios devem ser preenchidos!', 'danger')
                    return redirect(url_for('edit_entry_route', entry_id=entry_id))
                
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                    date = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    flash('Formato de data inválido! Use DD/MM/AAAA', 'danger')
                    return redirect(url_for('edit_entry_route', entry_id=entry_id))
                
                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        raise ValueError("Valor deve ser positivo")
                except ValueError:
                    flash('Valor monetário inválido!', 'danger')
                    return redirect(url_for('edit_entry_route', entry_id=entry_id))
                
                if entry_type not in ('receita', 'despesa'):
                    flash('Tipo de entrada inválido!', 'danger')
                    return redirect(url_for('edit_entry_route', entry_id=entry_id))
                
                try:
                    installments = max(1, int(installments_str))
                except ValueError:
                    installments = 1
                
                # Atualizar no banco de dados
                cursor.execute('''
                    UPDATE entries SET
                        date = ?,
                        description = ?,
                        amount = ?,
                        type = ?,
                        installments = ?,
                        category = ?
                    WHERE id = ?
                ''', (date, description, amount, entry_type, installments, category, entry_id))
                
                conn.commit()
                flash('Registro atualizado com sucesso!', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                conn.rollback()
                flash(f'Erro ao atualizar: {str(e)}', 'danger')
                return redirect(url_for('edit_entry_route', entry_id=entry_id))
        
        # Método GET - Carregar dados para edição
        cursor.execute('''
            SELECT id, date, description, amount, type, installments, category 
            FROM entries 
            WHERE id = ?
        ''', (entry_id,))
        entry = cursor.fetchone()
        
        if entry:
            entry_date = datetime.strptime(entry[1], "%Y-%m-%d").strftime("%d/%m/%Y")
            entry_data = {
                'id': entry[0],
                'date': entry_date,
                'description': entry[2],
                'amount': entry[3],
                'type': entry[4],
                'installments': entry[5],
                'category': entry[6]
            }
            
            return render_template('edit_entry.html', entry=entry_data)
        
        flash('Registro não encontrado!', 'danger')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()
            
@app.template_filter('to_date')
def to_date_filter(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except:
        return datetime.now().date()

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    try:
        # Obter o saldo atual
        entries = get_entries()
        current_month = datetime.now().strftime("%Y-%m")
        total_income = sum(e[3] for e in entries if e[4].lower() == 'receita' and e[1].startswith(current_month))
        total_expense = sum(e[3] for e in entries if e[4].lower() == 'despesa' and e[1].startswith(current_month))
        current_balance = total_income - total_expense
        
        # Processar formulário de feedback de meta
        if request.method == 'POST' and 'goal_feedback' in request.form:
            goal_id = request.form.get('goal_id')
            feedback = request.form.get('goal_feedback')
            
            if feedback == 'yes':
                flash('Parabéns por atingir sua meta! Continue com o bom trabalho!', 'success')
            else:
                flash('Considere revisar seus gastos para alcançar sua meta no próximo período.', 'warning')
            return redirect(url_for('goals'))
        
        # Obter e formatar metas
        goals_list = get_goals()
        formatted_goals = []
        today = datetime.now().date()
        
        for goal in goals_list:
            try:
                target_date = datetime.strptime(goal[4], "%Y-%m-%d").date()
                days_passed = (today - target_date).days if today > target_date else 0
                total_days = (target_date - today).days if target_date > today else 1
                progress_percentage = min(100, (goal[3] / goal[2]) * 100) if goal[2] > 0 else 0
                time_percentage = min(100, (1 - (days_passed / total_days)) * 100) if total_days > 0 else 100
                
                goal_dict = {
                    'id': goal[0],
                    'name': goal[1],
                    'target_amount': goal[2],
                    'current_amount': goal[3],
                    'target_date': target_date.strftime("%d/%m/%Y"),
                    'progress_percentage': progress_percentage,
                    'time_percentage': time_percentage,
                    'is_completed': goal[3] >= goal[2],
                    'is_behind': progress_percentage < time_percentage,
                    'balance_comparison': 'positive' if current_balance >= goal[2] else 'negative'
                }
                formatted_goals.append(goal_dict)
            except Exception as e:
                print(f"Erro ao formatar meta: {e}")
                continue
        
        return render_template('goals.html', 
                             goals=formatted_goals,
                             current_balance=current_balance)
    
    except Exception as e:
        flash(f'Erro ao carregar metas: {str(e)}', 'danger')
        return render_template('goals.html', goals=[], current_balance=0)
    
@app.route('/add_goal', methods=['POST'])
def add_goal_route():
    if request.method == 'POST':
        try:
            # Obter dados do formulário com fallback seguro
            name = request.form.get('goal_name', '').strip()
            target_amount = float(request.form.get('target_amount', 0))
            current_amount = float(request.form.get('current_amount', 0))
            target_date = request.form.get('target_date', '')
            
            # Validações
            if not name:
                flash('Nome da meta é obrigatório!', 'danger')
                return redirect(url_for('goals'))
                
            if target_amount <= 0:
                flash('Valor alvo deve ser positivo!', 'danger')
                return redirect(url_for('goals'))
                
            try:
                target_date = format_date_for_db(target_date)
            except ValueError:
                flash('Data inválida! Use o formato DD/MM/AAAA', 'danger')
                return redirect(url_for('goals'))
            
            # Adiciona a meta
            add_goal(name, target_amount, current_amount, target_date)
            flash('Meta adicionada com sucesso!', 'success')
            return redirect(url_for('goals'))
            
        except ValueError as e:
            flash(f'Erro nos dados: {str(e)}', 'danger')
    
    return redirect(url_for('goals'))

@app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    form = EditGoalForm()

    if form.validate_on_submit():
        try:
            name = form.goal_name.data.strip()
            target_amount = float(form.target_amount.data)
            current_amount = float(form.current_amount.data or 0)
            target_date = format_date_for_db(form.target_date.data)

            update_goal(goal_id, name, target_amount, current_amount, target_date)
            flash('Meta atualizada com sucesso!', 'success')
            return redirect(url_for('goals'))

        except Exception as e:
            flash(f'Erro ao atualizar meta: {str(e)}', 'danger')
            return redirect(url_for('edit_goal', goal_id=goal_id))

    # GET ou falha de validação — carregar meta e preencher campos
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
    goal = cursor.fetchone()
    conn.close()

    if goal:
        if request.method == 'GET':
            form.goal_name.data = goal[1]
            form.target_amount.data = goal[2]
            form.current_amount.data = goal[3]
            form.target_date.data = datetime.strptime(goal[4], "%Y-%m-%d").strftime("%d/%m/%Y")

        return render_template('edit_goal.html', form=form, goal_id=goal[0])

    flash('Meta não encontrada!', 'danger')
    return redirect(url_for('goals'))

@app.route('/delete_goal/<int:goal_id>')
def delete_goal_route(goal_id):
    delete_goal(goal_id)
    flash('Meta removida com sucesso!', 'success')
    return redirect(url_for('goals'))

from flask_wtf.csrf import generate_csrf  # já tá lá, mas só reforçando
from flask_wtf.csrf import generate_csrf  # já deve estar no topo

@app.route('/add_to_goal/<int:goal_id>', methods=['GET', 'POST'])
def add_to_goal_route(goal_id):
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            if amount <= 0:
                flash('Valor deve ser positivo!', 'danger')
                return redirect(url_for('add_to_goal_route', goal_id=goal_id))
            
            add_to_goal(goal_id, amount)
            flash(f'Valor de R$ {amount:.2f} adicionado à meta!', 'success')
            return redirect(url_for('goals'))
            
        except ValueError:
            flash('Valor inválido!', 'danger')

    # GET: buscar dados da meta
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM goals WHERE id = ?', (goal_id,))
    goal = cursor.fetchone()
    conn.close()

    if not goal:
        flash('Meta não encontrada!', 'danger')
        return redirect(url_for('goals'))

    return render_template('add_to_goal.html',
                           goal_id=goal_id,
                           goal_name=goal[0],
                           csrf_token=generate_csrf())  # ✅ Correto aqui

# Relatórios e gráficos
@app.route('/report')
def report():
    entries = get_entries()
    total_receitas = sum(entry[3] for entry in entries if entry[4] == 'receita')
    total_despesas = sum(entry[3] for entry in entries if entry[4] == 'despesa')
    saldo = total_receitas - total_despesas
    
    return render_template('report.html', 
                         total_receitas=total_receitas, 
                         total_despesas=total_despesas, 
                         saldo=saldo)
    
@app.route('/top_categories_chart/<category_type>')
def top_categories_chart(category_type):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Obter categorias ordenadas por valor total
        cursor.execute('''
            SELECT category, SUM(amount) as total 
            FROM entries 
            WHERE type = ? 
            GROUP BY category 
            ORDER BY total DESC 
            LIMIT 5
        ''', (category_type,))
        
        categories = []
        amounts = []
        
        for row in cursor.fetchall():
            categories.append(row[0])
            amounts.append(row[1])
        
        conn.close()
        
        # Criar gráfico horizontal
        plt.figure(figsize=(8, 4))
        colors = ['#28a745'] if category_type == 'receita' else ['#dc3545']
        plt.barh(categories[::-1], amounts[::-1], color=colors, alpha=0.7)
        plt.title(f'Top {category_type.capitalize()} por Categoria')
        plt.xlabel('Valor (R$)')
        plt.tight_layout()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=100, transparent=True)
        img.seek(0)
        plt.close()
        
        return send_file(img, mimetype='image/png')
        
    except Exception as e:
        print(f"Erro ao gerar gráfico de categorias: {e}")
        img = io.BytesIO()
        plt.figure(figsize=(8, 4))
        plt.text(0.5, 0.5, 'Erro ao gerar gráfico', ha='center')
        plt.savefig(img, format='png', transparent=True)
        img.seek(0)
        plt.close()
        return send_file(img, mimetype='image/png')

@app.route('/charts')
def charts():
    return render_template('charts.html')

@app.route('/monthly_balance_chart')
def monthly_balance_chart():
    try:
        entries = get_entries()
        monthly_data = {}
        
        for entry in entries:
            try:
                date = entry[1]
                month = date[:7]
                amount = entry[3]
                entry_type = entry[4]
                
                if month not in monthly_data:
                    monthly_data[month] = {'receita': 0, 'despesa': 0}
                
                monthly_data[month][entry_type] += amount
            except:
                continue
        
        months = sorted(monthly_data.keys())
        revenues = [monthly_data[month]['receita'] for month in months]
        expenses = [monthly_data[month]['despesa'] for month in months]
        
        plt.figure(figsize=(10, 5))
        plt.bar(months, revenues, label='Receitas', alpha=0.7)
        plt.bar(months, expenses, label='Despesas', alpha=0.7)
        plt.title('Balanço Mensal')
        plt.xlabel('Mês')
        plt.ylabel('Valor (R$)')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=100)
        img.seek(0)
        plt.close()
        
        return send_file(img, mimetype='image/png')
    except Exception as e:
        print(f"Erro ao gerar gráfico: {e}")
        img = io.BytesIO()
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, 'Erro ao gerar gráfico', ha='center')
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()
        return send_file(img, mimetype='image/png')

if __name__ == '__main__':
 # app.run(debug=True)
 
  port = int(os.environ.get("PORT", 8080)); app.run(host="0.0.0.0", port=port)
    
  