from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional


class EntryForm(FlaskForm):
    date = StringField('Data', validators=[DataRequired()])
    description = StringField('Descrição', validators=[DataRequired()])
    category = StringField('Categoria', validators=[DataRequired()])
    amount = DecimalField('Valor', validators=[DataRequired(), NumberRange(min=0.01)])
    type = SelectField('Tipo', choices=[('', 'Selecione...'), ('despesa', 'Despesa'), ('receita', 'Receita')], 
                      validators=[DataRequired()])
    installments = IntegerField('Parcelas', validators=[Optional(), NumberRange(min=1)], default=1)

class GoalForm(FlaskForm):
    name = StringField('Nome da Meta', validators=[DataRequired()])
    target_amount = DecimalField('Valor Alvo', validators=[DataRequired(), NumberRange(min=0.01)])
    current_amount = DecimalField('Valor Atual', validators=[Optional(), NumberRange(min=0)])
    target_date = StringField('Data Limite', validators=[DataRequired()])
    # forms.py

class EditGoalForm(FlaskForm):
    goal_name = StringField('Nome da Meta', validators=[DataRequired()])
    target_amount = DecimalField('Valor Alvo', validators=[DataRequired()])
    current_amount = DecimalField('Valor Atual')
    target_date = StringField('Data Limite', validators=[DataRequired()])
