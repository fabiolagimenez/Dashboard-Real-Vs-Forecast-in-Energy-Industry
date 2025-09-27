import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io
import base64
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="📊 Energy Analytics Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .narrative-box {
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .kpi-positive {
        color: #28a745;
    }
    .kpi-negative {
        color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_sample_data():
    """Carga datos de ejemplo cuando no se sube archivo"""
    # Crear datos de ejemplo basados en la estructura analizada
    np.random.seed(42)
    
    categories = ['Costs', 'Expenses']
    countries = ['Dominican Republic', 'Mexico', 'Panama']
    periods = [f"2025-{str(i).zfill(2)}" for i in range(1, 10)]
    
    cost_accounts = ['Ancillary Services', 'Capacity Purchase', 'Generation Costs', 'Must Run Costs', 'Transmission Costs']
    expense_accounts = ['Contingent Workers (Temporary Help)', 'Contract Services Consulting Costs', 
                       'Facilities Management Costs', 'Insurance Costs', 'IT Equipment Costs',
                       'Legal and Audit Costs', 'Maintenance Costs', 'Office Supplies',
                       'Professional Services', 'Travel and Training Costs']
    
    data = []
    for period in periods:
        for country in countries:
            # Costs
            for account in cost_accounts:
                base_amount = np.random.uniform(50000, 2000000)
                forecast = base_amount * np.random.uniform(0.9, 1.1)
                real = forecast * np.random.uniform(0.85, 1.15)
                
                data.append({
                    'Category': 'Costs',
                    'Account Description': account,
                    'Country': country,
                    'Period': period,
                    'Real Amount': real,
                    'Forecast': forecast,
                    'Desviacion_absoluta': real - forecast,
                    'Desviacion_pct': ((real - forecast) / forecast) * 100 if forecast != 0 else 0
                })
            
            # Expenses  
            for account in expense_accounts:
                base_amount = np.random.uniform(10000, 500000)
                forecast = base_amount * np.random.uniform(0.9, 1.1)
                real = forecast * np.random.uniform(0.8, 1.2)
                
                data.append({
                    'Category': 'Expenses',
                    'Account Description': account,
                    'Country': country,
                    'Period': period,
                    'Real Amount': real,
                    'Forecast': forecast,
                    'Desviacion_absoluta': real - forecast,
                    'Desviacion_pct': ((real - forecast) / forecast) * 100 if forecast != 0 else 0
                })
    
    return pd.DataFrame(data)

def load_data(uploaded_file):
    """Carga datos desde archivo subido o datos de ejemplo"""
    if uploaded_file is not None:
        try:
            # Leer Excel
            if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
                df = pd.read_excel(uploaded_file, sheet_name='DATA')
            else:
                df = pd.read_csv(uploaded_file)
            
            # Verificar columnas requeridas
            required_cols = ['Category', 'Account Description', 'Country', 'Period', 'Real Amount', 'Forecast']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"Columnas faltantes: {missing_cols}")
                return load_sample_data()
            
            return df
        except Exception as e:
            st.error(f"Error al cargar el archivo: {str(e)}")
            return load_sample_data()
    else:
        return load_sample_data()

def normalize_data(df):
    """Normaliza y procesa los datos"""
    df = df.copy()
    
    # Convertir Period a string
    df['Period'] = df['Period'].astype(str)
    
    # Asegurar tipos numéricos
    numeric_cols = ['Real Amount', 'Forecast']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calcular desviaciones si no existen
    if 'Desviacion_absoluta' not in df.columns:
        df['Desviacion_absoluta'] = df['Real Amount'] - df['Forecast']
    
    if 'Desviacion_pct' not in df.columns:
        df['Desviacion_pct'] = np.where(df['Forecast'] != 0, 
                                       ((df['Real Amount'] - df['Forecast']) / df['Forecast']) * 100, 
                                       0)
    
    # Manejar valores nulos
    df = df.dropna(subset=['Real Amount', 'Forecast'])
    
    return df

def calculate_kpis(df):
    """Calcula KPIs principales"""
    total_forecast = df['Forecast'].sum()
    total_real = df['Real Amount'].sum()
    net_deviation = total_real - total_forecast
    net_deviation_pct = (net_deviation / total_forecast) * 100 if total_forecast != 0 else 0
    
    # KPI de cumplimiento (desviación absoluta <= 100k)
    kpi_compliance = (abs(df['Desviacion_absoluta']) <= 100000).mean() * 100
    
    return {
        'total_forecast': total_forecast,
        'total_real': total_real,
        'net_deviation': net_deviation,
        'net_deviation_pct': net_deviation_pct,
        'kpi_compliance': kpi_compliance
    }

def create_monthly_chart(df):
    """Gráfico de barras agrupadas por mes"""
    monthly_data = df.groupby('Period').agg({
        'Real Amount': 'sum',
        'Forecast': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Forecast', x=monthly_data['Period'], y=monthly_data['Forecast'],
                         marker_color='#1f77b4', opacity=0.8))
    fig.add_trace(go.Bar(name='Real', x=monthly_data['Period'], y=monthly_data['Real Amount'],
                         marker_color='#ff7f0e', opacity=0.8))
    
    fig.update_layout(
        title='Forecast vs Real por Mes',
        barmode='group',
        xaxis_title='Período',
        yaxis_title='Monto (USD)',
        height=500
    )
    
    return fig, monthly_data

def create_deviation_line_chart(df):
    """Gráfico de línea para desviación porcentual"""
    monthly_dev = df.groupby('Period').apply(
        lambda x: ((x['Real Amount'].sum() - x['Forecast'].sum()) / x['Forecast'].sum()) * 100
    ).reset_index()
    monthly_dev.columns = ['Period', 'Deviation_Pct']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_dev['Period'], y=monthly_dev['Deviation_Pct'],
                            mode='lines+markers', name='Desviación %',
                            line=dict(color='#d62728', width=3),
                            marker=dict(size=8)))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
    
    fig.update_layout(
        title='Desviación Porcentual Mensual',
        xaxis_title='Período',
        yaxis_title='Desviación (%)',
        height=400
    )
    
    return fig, monthly_dev

def create_top_accounts_chart(df):
    """Top 10 cuentas con mayor desviación absoluta"""
    top_accounts = df.groupby('Account Description').agg({
        'Desviacion_absoluta': 'sum'
    }).reset_index()
    top_accounts['abs_deviation'] = abs(top_accounts['Desviacion_absoluta'])
    top_accounts = top_accounts.nlargest(10, 'abs_deviation')
    
    colors = ['#d62728' if x < 0 else '#2ca02c' for x in top_accounts['Desviacion_absoluta']]
    
    fig = go.Figure(go.Bar(
        x=top_accounts['Desviacion_absoluta'],
        y=top_accounts['Account Description'],
        orientation='h',
        marker_color=colors,
        opacity=0.8
    ))
    
    fig.update_layout(
        title='Top 10 Cuentas por Desviación Absoluta',
        xaxis_title='Desviación (USD)',
        height=500
    )
    
    return fig, top_accounts

def create_waterfall_chart(df):
    """Gráfico waterfall mensual simplificado"""
    monthly_data = df.groupby(['Period', 'Category']).agg({
        'Desviacion_absoluta': 'sum'
    }).reset_index()
    
    # Preparar datos para waterfall
    periods = sorted(df['Period'].unique())
    
    fig = go.Figure()
    
    # Agregar barras por categoría
    for category in df['Category'].unique():
        cat_data = monthly_data[monthly_data['Category'] == category]
        fig.add_trace(go.Bar(
            name=category,
            x=cat_data['Period'],
            y=cat_data['Desviacion_absoluta'],
            opacity=0.8
        ))
    
    fig.update_layout(
        title='Desviación por Categoría y Período',
        xaxis_title='Período',
        yaxis_title='Desviación (USD)',
        height=500,
        barmode='group'
    )
    
    return fig, monthly_data

def generate_narrative(chart_type, data):
    """Genera narrativa automática para cada gráfico"""
    narratives = {
        'monthly': generate_monthly_narrative(data),
        'deviation': generate_deviation_narrative(data),
        'top_accounts': generate_top_accounts_narrative(data),
        'waterfall': generate_waterfall_narrative(data)
    }
    return narratives.get(chart_type, "Análisis de datos en progreso.")

def generate_monthly_narrative(monthly_data):
    """Narrativa para gráfico mensual"""
    max_real_month = monthly_data.loc[monthly_data['Real Amount'].idxmax(), 'Period']
    max_real_value = monthly_data['Real Amount'].max()
    min_real_month = monthly_data.loc[monthly_data['Real Amount'].idxmin(), 'Period']
    
    avg_deviation = ((monthly_data['Real Amount'] - monthly_data['Forecast']) / monthly_data['Forecast'] * 100).mean()
    
    narrative = f"El mes con mayor ejecución real fue {max_real_month} con ${max_real_value:,.0f}, mientras que {min_real_month} registró el menor valor. "
    narrative += f"En promedio, la desviación mensual es de {avg_deviation:.1f}%, "
    
    if avg_deviation > 0:
        narrative += "indicando una tendencia a superar el forecast."
    else:
        narrative += "mostrando ejecución por debajo del forecast planificado."
    
    return narrative

def generate_deviation_narrative(monthly_dev):
    """Narrativa para desviación porcentual"""
    max_dev_month = monthly_dev.loc[monthly_dev['Deviation_Pct'].idxmax(), 'Period']
    max_dev_value = monthly_dev['Deviation_Pct'].max()
    
    positive_months = len(monthly_dev[monthly_dev['Deviation_Pct'] > 0])
    total_months = len(monthly_dev)
    
    narrative = f"La mayor desviación positiva ocurrió en {max_dev_month} con {max_dev_value:.1f}%. "
    narrative += f"Durante {positive_months} de {total_months} meses se superó el forecast, "
    
    if positive_months > total_months/2:
        narrative += "indicando una subestimación sistemática en la planificación."
    else:
        narrative += "sugiriendo un control adecuado del presupuesto."
    
    return narrative

def generate_top_accounts_narrative(top_accounts):
    """Narrativa para top cuentas"""
    worst_account = top_accounts.iloc[0]['Account Description']
    worst_deviation = top_accounts.iloc[0]['Desviacion_absoluta']
    
    negative_accounts = len(top_accounts[top_accounts['Desviacion_absoluta'] < 0])
    
    narrative = f"La cuenta con mayor impacto es '{worst_account}' con una desviación de ${worst_deviation:,.0f}. "
    
    if worst_deviation > 0:
        narrative += "Esta sobreejecución requiere análisis de las causas subyacentes. "
    else:
        narrative += "Esta subejecución podría indicar eficiencias operativas o retrasos. "
    
    narrative += f"De las top 10 cuentas, {negative_accounts} presentan subejecución vs forecast."
    
    return narrative

def generate_waterfall_narrative(monthly_data):
    """Narrativa para waterfall"""
    costs_total = monthly_data[monthly_data['Category'] == 'Costs']['Desviacion_absoluta'].sum()
    expenses_total = monthly_data[monthly_data['Category'] == 'Expenses']['Desviacion_absoluta'].sum()
    
    narrative = f"Los Costos presentan una desviación neta de ${costs_total:,.0f}, "
    narrative += f"mientras que los Gastos suman ${expenses_total:,.0f}. "
    
    dominant_category = "Costos" if abs(costs_total) > abs(expenses_total) else "Gastos"
    narrative += f"La categoría {dominant_category} tiene el mayor impacto en la desviación total. "
    
    if costs_total * expenses_total < 0:
        narrative += "Existe una compensación parcial entre ambas categorías."
    else:
        narrative += "Ambas categorías contribuyen en la misma dirección."
    
    return narrative

def main():
    # Header
    st.title("⚡ Energy Analytics Dashboard")
    st.markdown("**Análisis de Forecast vs Real para Empresa de Energía Eléctrica**")
    st.markdown("---")
    
    # Sidebar para carga de archivos
    with st.sidebar:
        st.header("📁 Carga de Datos")
        uploaded_file = st.file_uploader(
            "Subir archivo CSV o Excel",
            type=['csv', 'xlsx', 'xls'],
            help="Si no subes un archivo, se usarán datos de ejemplo"
        )
        
        if uploaded_file is None:
            st.info("🔹 Usando datos de ejemplo")
        else:
            st.success(f"✅ Archivo cargado: {uploaded_file.name}")
    
    # Cargar y normalizar datos
    df = load_data(uploaded_file)
    df = normalize_data(df)
    
    # Sidebar para filtros
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Filtro de país
        countries = ['Todos'] + sorted(df['Country'].unique().tolist())
        selected_country = st.selectbox("País", countries)
        
        # Filtro de categoría
        categories = ['Todas'] + sorted(df['Category'].unique().tolist())
        selected_category = st.selectbox("Categoría", categories)
        
        # Filtro de período
        all_periods = sorted(df['Period'].unique())
        # Forzar períodos 2025-01 a 2025-09
        default_periods = [p for p in all_periods if p.startswith('2025-')]
        selected_periods = st.multiselect(
            "Períodos", 
            all_periods, 
            default=default_periods if default_periods else all_periods[:9]
        )
        
        # Búsqueda por cuenta
        st.subheader("🔎 Búsqueda de Cuenta")
        account_search = st.text_input("Buscar cuenta", placeholder="Ej: Generation")
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    if selected_country != 'Todos':
        filtered_df = filtered_df[filtered_df['Country'] == selected_country]
    
    if selected_category != 'Todas':
        filtered_df = filtered_df[filtered_df['Category'] == selected_category]
    
    if selected_periods:
        filtered_df = filtered_df[filtered_df['Period'].isin(selected_periods)]
    
    if account_search:
        filtered_df = filtered_df[
            filtered_df['Account Description'].str.contains(account_search, case=False, na=False)
        ]
    
    # Verificar que hay datos después de filtrar
    if filtered_df.empty:
        st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
        return
    
    # KPIs principales
    st.header("📊 KPIs Principales")
    kpis = calculate_kpis(filtered_df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Forecast",
            f"${kpis['total_forecast']:,.0f}",
            help="Suma total del forecast"
        )
    
    with col2:
        st.metric(
            "Total Real",
            f"${kpis['total_real']:,.0f}",
            help="Suma total de la ejecución real"
        )
    
    with col3:
        delta_color = "normal" if abs(kpis['net_deviation_pct']) <= 5 else "inverse"
        st.metric(
            "Desviación Neta",
            f"${kpis['net_deviation']:,.0f}",
            f"{kpis['net_deviation_pct']:+.1f}%"
        )
    
    with col4:
        compliance_color = "normal" if kpis['kpi_compliance'] >= 80 else "inverse"
        st.metric(
            "% Cumplimiento KPI",
            f"{kpis['kpi_compliance']:.1f}%",
            help="% de cuentas con |desviación| ≤ $100k"
        )
    
    st.markdown("---")
    
    # Gráficos principales
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Forecast vs Real Mensual")
        monthly_fig, monthly_data = create_monthly_chart(filtered_df)
        st.plotly_chart(monthly_fig, use_container_width=True)
        
        # Narrativa
        st.markdown(f"""
        <div class="narrative-box">
        <strong>📝 Análisis:</strong> {generate_narrative('monthly', monthly_data)}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📉 Desviación Porcentual")
        deviation_fig, deviation_data = create_deviation_line_chart(filtered_df)
        st.plotly_chart(deviation_fig, use_container_width=True)
        
        # Narrativa
        st.markdown(f"""
        <div class="narrative-box">
        <strong>📝 Análisis:</strong> {generate_narrative('deviation', deviation_data)}
        </div>
        """, unsafe_allow_html=True)
    
    # Segunda fila de gráficos
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🎯 Top 10 Cuentas por Desviación")
        top_fig, top_data = create_top_accounts_chart(filtered_df)
        st.plotly_chart(top_fig, use_container_width=True)
        
        # Narrativa
        st.markdown(f"""
        <div class="narrative-box">
        <strong>📝 Análisis:</strong> {generate_narrative('top_accounts', top_data)}
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.subheader("🌊 Desviación por Categoría")
        waterfall_fig, waterfall_data = create_waterfall_chart(filtered_df)
        st.plotly_chart(waterfall_fig, use_container_width=True)
        
        # Narrativa
        st.markdown(f"""
        <div class="narrative-box">
        <strong>📝 Análisis:</strong> {generate_narrative('waterfall', waterfall_data)}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabla detalle
    st.subheader("📋 Tabla Detalle")
    
    # Formatear columnas numéricas
    display_df = filtered_df.copy()
    numeric_cols = ['Real Amount', 'Forecast', 'Desviacion_absoluta']
    for col in numeric_cols:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
    
    display_df['Desviacion_pct'] = display_df['Desviacion_pct'].apply(lambda x: f"{x:.2f}%")
    
    # Renombrar columnas para mejor presentación
    display_df = display_df.rename(columns={
        'Category': 'Categoría',
        'Account Description': 'Descripción de Cuenta',
        'Country': 'País',
        'Period': 'Período',
        'Real Amount': 'Monto Real',
        'Forecast': 'Forecast',
        'Desviacion_absoluta': 'Desviación Absoluta',
        'Desviacion_pct': 'Desviación %'
    })
    
    # Mostrar tabla con paginación
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Botón de descarga
    st.subheader("💾 Descargar Datos")
    
    # Preparar datos para descarga
    download_data = filtered_df.copy()
    
    # Crear reporte de KPIs
    kpi_report = pd.DataFrame([
        ['Total Forecast', f"${kpis['total_forecast']:,.2f}"],
        ['Total Real', f"${kpis['total_real']:,.2f}"],
        ['Desviación Neta (USD)', f"${kpis['net_deviation']:,.2f}"],
        ['Desviación Neta (%)', f"{kpis['net_deviation_pct']:.2f}%"],
        ['% Cumplimiento KPI', f"{kpis['kpi_compliance']:.2f}%"],
        ['Período de Análisis', f"{min(selected_periods) if selected_periods else 'N/A'} - {max(selected_periods) if selected_periods else 'N/A'}"],
        ['País Seleccionado', selected_country],
        ['Categoría Seleccionada', selected_category],
        ['Total de Registros', len(filtered_df)],
        ['Fecha de Generación', datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ], columns=['Métrica', 'Valor'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Descargar datos detallados
        csv_data = download_data.to_csv(index=False)
        st.download_button(
            label="📊 Descargar Datos Detallados (CSV)",
            data=csv_data,
            file_name=f"forecast_vs_real_detalle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Descargar reporte de KPIs
        kpi_csv = kpi_report.to_csv(index=False)
        st.download_button(
            label="📈 Descargar Reporte KPIs (CSV)",
            data=kpi_csv,
            file_name=f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Footer con información adicional
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p><strong>Energy Analytics Dashboard</strong> | Desarrollado para análisis de Forecast vs Real</p>
    <p>🔧 Soporte técnico: Verificar rangos de datos y filtros aplicados</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
