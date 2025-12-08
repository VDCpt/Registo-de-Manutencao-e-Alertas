# --- Dependências Necessárias: Flask, pandas, matplotlib, reportlab ---
# pip install Flask pandas matplotlib reportlab

# --- Importações Essenciais ---
from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
from typing import List, Dict
import io
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader

# =========================================================================
# I. LÓGICA DE DADOS (Baseado em models.py)
# =========================================================================

# --- Constantes para Alertas Padrão ---
TROCA_OLEO_KM = 15000
RODADOS_KM = 40000
INSPECAO_DIAS = 365 # 1 ano

class MaintenanceRecord:
    """Representa uma intervenção de manutenção efetuada."""
    def __init__(self, description: str, date: str, mileage: int, cost: float = 0.0):
        self.description = description
        self.date = datetime.strptime(date, '%Y-%m-%d')
        self.mileage = mileage
        self.cost = cost

    def to_dict(self):
        return {
            'description': self.description,
            'date': self.date.strftime('%Y-%m-%d'),
            'mileage': self.mileage,
            'cost': self.cost
        }

class Vehicle:
    """Representa o veículo do motorista e o histórico de manutenção."""
    def __init__(self, license_plate: str, initial_mileage: int):
        self.license_plate = license_plate
        self.current_mileage = initial_mileage
        self.records: List[MaintenanceRecord] = []
        self.alerts: Dict[str, str] = {}

    def update_mileage(self, new_mileage: int):
        if new_mileage >= self.current_mileage:
            self.current_mileage = new_mileage
            return True
        return False

    def add_record(self, record: MaintenanceRecord):
        self.records.append(record)
        self.records.sort(key=lambda r: r.date, reverse=True)
        self.check_alerts()
        self.update_mileage(record.mileage)

    def get_last_maintenance(self, description_keyword: str) -> MaintenanceRecord | None:
        relevant_records = [
            r for r in self.records 
            if description_keyword.lower() in r.description.lower()
        ]
        if not relevant_records:
            return None
        relevant_records.sort(key=lambda r: r.date, reverse=True)
        return relevant_records[0]

    def check_alerts(self):
        self.alerts = {}
        now = datetime.now()

        # --- 1. Troca de Óleo (Baseado em KM) ---
        last_oil = self.get_last_maintenance("óleo")
        if last_oil:
            next_oil_km = last_oil.mileage + TROCA_OLEO_KM
            km_left = next_oil_km - self.current_mileage
            if km_left <= 2000:
                self.alerts['Óleo'] = f"Atenção: Próxima troca prevista em {next_oil_km} km. Faltam {km_left:,} km."
            elif km_left < 0:
                 self.alerts['Óleo'] = f"URGENTE: Troca de óleo atrasada! Deveria ter sido feita há {-km_left:,} km."

        # --- 2. Inspeção (Baseado em Data) ---
        last_inspection = self.get_last_maintenance("inspeção")
        if last_inspection:
            next_inspection_date = last_inspection.date.replace(year=last_inspection.date.year + 1)
            days_left = (next_inspection_date - now).days

            if days_left <= 60:
                self.alerts['Inspeção'] = f"URGENTE: Inspeção obrigatória a aproximar-se. Prevista para {next_inspection_date.strftime('%Y-%m-%d')}. Faltam {days_left} dias."

    def to_full_dict(self):
        return {
            'license_plate': self.license_plate,
            'current_mileage': self.current_mileage,
            'records': [r.to_dict() for r in self.records],
            'alerts': self.alerts
        }

# =========================================================================
# II. GERAÇÃO DE PDF E GRÁFICOS (Baseado em pdf_generator.py)
# =========================================================================

def create_cost_chart(records: list) -> io.BytesIO:
    """Gera um gráfico de barras dos custos de manutenção por mês e devolve a imagem em memória."""
    df = pd.DataFrame([r.to_dict() for r in records])
    df['date'] = pd.to_datetime(df['date'])
    df['month_year'] = df['date'].dt.to_period('M')

    monthly_costs = df.groupby('month_year')['cost'].sum()
    
    fig, ax = plt.subplots(figsize=(8, 4))
    
    if monthly_costs.empty:
        ax.text(0.5, 0.5, 'Dados de Custo Indisponíveis', ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
        
    else:
        monthly_costs.plot(kind='bar', ax=ax, color='#1f77b4')
        ax.set_title('Custos de Manutenção Mensais (Últimos Registos)', fontsize=12)
        ax.set_xlabel('Mês/Ano', fontsize=10)
        ax.set_ylabel('Custo (€)', fontsize=10)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.grid(axis='y', linestyle='--', alpha=0.7)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_pdf_report(vehicle_data: dict, records: list) -> io.BytesIO:
    """Gera o relatório PDF completo com tabela e gráfico."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=50, leftMargin=50, 
                            topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    Story = []

    # Título e Info do Veículo
    Story.append(Paragraph("<b>Relatório de Logbook de Manutenção - Voz do Condutor</b>", styles['Title']))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph(f"<b>Matrícula:</b> {vehicle_data['license_plate']}", styles['Normal']))
    Story.append(Paragraph(f"<b>KM Atual:</b> {vehicle_data['current_mileage']:,} km", styles['Normal']))
    Story.append(Spacer(1, 12))

    # Tabela de Registos
    table_data = [['Data', 'KM', 'Descrição', 'Custo (€)']]
    for record in records:
        table_data.append([
            record.date.strftime('%Y-%m-%d'),
            f"{record.mileage:,}",
            record.description,
            f"{record.cost:.2f}"
        ])

    table = Table(table_data, colWidths=[60, 60, 260, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    Story.append(Paragraph("<b>Histórico de Intervenções</b>", styles['h2']))
    Story.append(Spacer(1, 6))
    Story.append(table)
    Story.append(Spacer(1, 24))

    # Gráfico de Custos
    chart_image_io = create_cost_chart(records)
    img = ImageReader(chart_image_io)
    
    Story.append(Paragraph("<b>Análise de Custos Mensais</b>", styles['h2']))
    Story.append(img)
    
    doc.build(Story)
    buffer.seek(0)
    return buffer

# =========================================================================
# III. SERVIDOR FLASK E ROTAS
# =========================================================================

app = Flask(__name__)

# --- Filtros Jinja para formatação ---
# Formata números com ponto como separador de milhar (padrão português)
def format_km(value):
    return f"{value:,}".replace(',', 'X').replace('.', ',').replace('X', '.')
def format_currency(value):
    return f"{value:.2f}".replace('.', ',')

app.jinja_env.filters['format_km'] = format_km
app.jinja_env.filters['format_currency'] = format_currency
# --- Fim dos Filtros ---


# Simulação de um banco de dados
VEHICLE_DB = {}

# Inicializa um veículo de exemplo
def initialize_db():
    global VEHICLE_DB
    test_car = Vehicle(license_plate="12-AA-34", initial_mileage=150000)
    
    # Registos iniciais (adaptar datas para ver o gráfico)
    test_car.add_record(MaintenanceRecord("Troca de óleo e filtro", "2025-10-01", 155000, 80.50))
    test_car.add_record(MaintenanceRecord("Revisão de 15.000km", "2025-05-20", 153000, 120.00))
    test_car.add_record(MaintenanceRecord("Troca dos 4 Pneus", "2024-11-15", 152000, 320.00))
    test_car.add_record(MaintenanceRecord("Inspeção Periódica Anual", "2025-01-10", 145000, 31.50))
    
    test_car.update_mileage(169000) # Atualiza KM atual
    test_car.check_alerts()
    
    VEHICLE_DB[test_car.license_plate] = test_car

initialize_db()

@app.route('/')
def dashboard():
    """Página principal que exibe o estado e os alertas."""
    car = VEHICLE_DB.get("12-AA-34") 
    if not car:
        return "Veículo não encontrado.", 404
        
    return render_template(
        'dashboard.html', 
        vehicle=car.to_full_dict(),
        alerts=car.alerts,
        records=car.records
    )

@app.route('/register', methods=['GET', 'POST'])
def register_maintenance():
    """Rota para registar uma nova intervenção."""
    car = VEHICLE_DB.get("12-AA-34") 

    if request.method == 'POST':
        try:
            description = request.form['description']
            date = request.form['date']
            mileage = int(request.form['mileage'])
            # Tratar o custo se estiver vazio
            cost = float(request.form.get('cost', 0.0) or 0.0) 

            new_record = MaintenanceRecord(description, date, mileage, cost)
            car.add_record(new_record)
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            return f"Erro ao registar: {e}", 400

    return render_template('register_maintenance.html')


@app.route('/download_report', methods=['GET'])
def download_report():
    """Gera e envia o relatório em PDF."""
    car = VEHICLE_DB.get("12-AA-34") 
    if not car:
        return "Veículo não encontrado.", 404

    # 1. Gerar o PDF
    pdf_buffer = generate_pdf_report(car.to_full_dict(), car.records)
    
    # 2. Enviar o PDF para o utilizador
    filename = f"Logbook_Manutencao_{car.license_plate}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True)
