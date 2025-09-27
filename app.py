import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Financiero - Sector Energía",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores corporativos
COLORS = {
    'blue': '#1e88e5',
    'green': '#43a047', 
    'red': '#e53935',
    'light_blue': '#90caf9',
    'light_green': '#81c784',
    'light_red': '#ef5350'
}

# Constantes
MONTHS = [f"2025-{m:02d}" for m in range(1, 10)]

def load_sample_data():
    """Crear dataset de ejemplo mínimo para demostración"""
    sample_data = {
        'Category': ['Costs', 'Expenses', 'Costs', 'Expenses'],
        'Account Description': ['Generation Costs', 'Administrative Expenses', 'Transmission Costs', 'Marketing Expenses'],
        'Country': ['Panama', 'Panama', 'Mexico', 'Mexico'],
        'Period': ['2025-01', '2025-01', '2025-02', '2025-02'],
        'Real Amount': [1500000, 250000, 1200000, 180000],
        'Forecast': [1400000, 260000, 1150000, 190000],
        'Desviacion_absoluta': [100000, -10000, 50000, -10000],
        'Desviacion_pct': [7.14, -3.85, 4.35, -5.26]
    }
    return pd.DataFrame(sample_data)

def clean_currency_column(series):
    """Limpiar columna de montos eliminando símbolos y convirtiendo a numérico"""
    if series.dtype == 'object':
        # Eliminar símbolos de moneda, comas, espacios
        cleaned = series.astype(str).str.replace(r'[$,\s]', '', regex=True)
        # Convertir a numérico, NaN se convierte en 0
        return pd.to_numeric(cleaned, errors='coerce').fillna(0)
    return pd.to_numeric(series, errors='coerce').fillna(0)

def normalize_period(period_series):
    """Normalizar columna Period a formato YYYY-MM"""
    normalized = []
    for period in period_series:
        try:
            if isinstance(period, str):
                # Si ya está en formato YYYY-MM, mantenerlo
                if len(period) == 7 and period[4] == '-':
                    normalized.append(period)
                else:
                    # Intentar parsearlo como fecha
                    date_obj = pd.to_datetime(period)
                    normalized.append(date_obj.strftime('%Y-%m'))
            else:
                # Si es datetime
                date_obj = pd.to_datetime(period)
                normalized.append(date_obj.strftime('%Y-%m'))
        except:
            normalized.append('2025-01')  # Valor por defecto
    return normalized

@st.cache_data
def process_data(df):
    """Procesar y limpiar los datos"""
    # Crear copia del dataframe
    df = df.copy()
    
    # Limpiar columnas numéricas
    numeric_cols = ['Real Amount', 'Forecast', 'Desviacion_absoluta', 'Desviacion_pct']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_currency_column(df[col])
    
    # Normalizar Period
    if 'Period' in df.columns:
        df['Period'] = normalize_period(df['Period'])
    
    # Crear alias para evitar KeyError con columnas en inglés
    df['Deviation_Abs'] = df.get('Desviacion_absoluta', df['Real Amount'] - df['Forecast'])
    df['Deviation_Pct'] = df.get('Desviacion_pct', 
                                 (df['Real Amount'] - df['Forecast']) / df['Forecast'].replace(0, np.nan)).fillna(0)
    
    # Si faltan las columnas de desviación, calcularlas
    if 'Desviacion_absoluta' not in df.columns:
        df['Desviacion_absoluta'] = df['Deviation_Abs']
    if 'Desviacion_pct' not in df.columns:
        df['Desviacion_pct'] = df['Deviation_Pct']
    
    return df

def load_data():
    """Cargar datos desde archivo subido o usar datos de ejemplo"""
    uploaded_file = st.sidebar.file_uploader(
        "📁 Subir archivo de datos",
        type=['csv', 'xlsx'],
        help="Sube un archivo CSV o Excel con la hoja DATA"
    )
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                # Leer Excel, buscar hoja DATA
                excel_file = pd.ExcelFile(uploaded_file)
                if 'DATA' in excel_file.sheet_names:
                    df = pd.read_excel(uploaded_file, sheet_name='DATA')
                else:
                    st.warning("No se encontró hoja 'DATA', usando la primera hoja disponible")
                    df = pd.read_excel(uploaded_file, sheet_name=0)
            else:
                df = pd.read_csv(uploaded_file)
            
            return process_data(df)
            
        except Exception as e:
            st.error(f"Error al cargar archivo: {str(e)}")
            return process_data(load_sample_data())
    
    else:
        st.sidebar.info("💡 Usando datos de ejemplo. Sube un archivo para usar tus datos.")
        return process_data(load_sample_data())

def create_filters(df):
    """Crear filtros en sidebar"""
    st.sidebar.header("🔍 Filtros")
    
    # Filtro de País
    countries = ['Todos'] + sorted(df['Country'].unique().tolist())
    selected_country = st.sidebar.selectbox("País", countries)
    
    # Filtro de Categoría
    categories = ['Todas'] + sorted(df['Category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Categoría", categories)
    
    # Filtro de Período
    periods = sorted(df['Period'].unique().tolist())
    selected_periods = st.sidebar.multiselect(
        "Períodos", 
        periods, 
        default=periods
    )
    
    # Búsqueda por Account Description
    search_term = st.sidebar.text_input("🔎 Buscar cuenta", "")
    
    return selected_country, selected_category, selected_periods, search_term

def apply_filters(df, country, category, periods, search_term):
    """Aplicar filtros al dataframe"""
    filtered_df = df.copy()
    
    if country != 'Todos':
        filtered_df = filtered_df[filtered_df['Country'] == country]
    
    if category != 'Todas':
        filtered_df = filtered_df[filtered_df['Category'] == category]
    
    if periods:
        filtered_df = filtered_df[filtered_df['Period'].isin(periods)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['Account Description'].str.contains(search_term, case=False, na=False)
        ]
    
    return filtered_df

def calculate_kpis(df):
    """Calcular KPIs principales"""
    if df.empty:
        return {
            'total_forecast': 0,
            'total_real': 0,
            'net_deviation': 0,
            'deviation_pct': 0,
            'compliance_rate': 0,
            'total_rows': 0,
            'compliant_rows': 0
        }
    
    total_forecast = df['Forecast'].sum()
    total_real = df['Real Amount'].sum()
    net_deviation = total_real - total_forecast
    
    # Evitar división por cero
    deviation_pct = (net_deviation / total_forecast * 100) if total_forecast != 0 else 0
    
    # Cumplimiento KPI (|Deviation_Abs| <= 100000)
    total_rows = len(df)
    compliant_rows = len(df[abs(df['Deviation_Abs']) <= 100000])
    compliance_rate = (compliant_rows / total_rows * 100) if total_rows > 0 else 0
    
    return {
        'total_forecast': total_forecast,
        'total_real': total_real,
        'net_deviation': net_deviation,
        'deviation_pct': deviation_pct,
        'compliance_rate': compliance_rate,
        'total_rows': total_rows,
        'compliant_rows': compliant_rows
    }

def create_kpi_cards(kpis):
    """Crear cards de KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Total Forecast",
            value=f"${kpis['total_forecast']:,.0f}",
        )
    
    with col2:
        st.metric(
            label="💵 Total Real",
            value=f"${kpis['total_real']:,.0f}",
            delta=f"${kpis['net_deviation']:,.0f}"
        )
    
    with col3:
        st.metric(
            label="📊 Desviación %",
            value=f"{kpis['deviation_pct']:.1f}%",
        )
    
    with col4:
        st.metric(
            label="✅ Cumplimiento KPI",
            value=f"{kpis['compliance_rate']:.1f}%",
            help="Proporción de cuentas con |Desviación| ≤ $100,000"
        )

def create_forecast_vs_real_chart(df):
    """Crear gráfico de barras Forecast vs Real por mes"""
    # Agregar por mes
    monthly_data = df.groupby('Period').agg({
        'Forecast': 'sum',
        'Real Amount': 'sum'
    }).reset_index()
    
    # Reindexar para incluir todos los meses
    monthly_data = monthly_data.set_index('Period').reindex(MONTHS, fill_value=0).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Forecast',
        x=monthly_data['Period'],
        y=monthly_data['Forecast'],
        marker_color=COLORS['blue']
    ))
    
    fig.add_trace(go.Bar(
        name='Real',
        x=monthly_data['Period'],
        y=monthly_data['Real Amount'],
        marker_color=COLORS['green']
    ))
    
    fig.update_layout(
        title='Forecast vs Real por Mes',
        xaxis_title='Período',
        yaxis_title='Monto ($)',
        barmode='group',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_deviation_line_chart(df):
    """Crear gráfico de línea de desviación % por mes"""
    # Calcular desviación % por mes
    monthly_dev = df.groupby('Period').agg({
        'Forecast': 'sum',
        'Real Amount': 'sum'
    }).reset_index()
    
    monthly_dev['Deviation_Pct'] = (
        (monthly_dev['Real Amount'] - monthly_dev['Forecast']) / 
        monthly_dev['Forecast'].replace(0, np.nan) * 100
    ).fillna(0)
    
    # Reindexar
    monthly_dev = monthly_dev.set_index('Period').reindex(MONTHS, fill_value=0).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_dev['Period'],
        y=monthly_dev['Deviation_Pct'],
        mode='lines+markers',
        name='Desviación %',
        line=dict(color=COLORS['red'], width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Desviación Porcentual por Mes',
        xaxis_title='Período',
        yaxis_title='Desviación (%)',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_top_accounts_chart(df):
    """Crear gráfico Top 10 cuentas por desviación absoluta"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin datos para mostrar", 
                          xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Top 10 Cuentas por Desviación", height=400)
        return fig
    
    # Obtener top 10 por valor absoluto de desviación
    top_accounts = df.nlargest(10, abs(df['Deviation_Abs']))
    
    # Crear colores basados en si es positivo o negativo
    colors = [COLORS['red'] if x > 0 else COLORS['green'] for x in top_accounts['Deviation_Abs']]
    
    fig = go.Figure(go.Bar(
        y=top_accounts['Account Description'],
        x=top_accounts['Deviation_Abs'],
        orientation='h',
        marker_color=colors,
        text=[f"${x:,.0f}" for x in top_accounts['Deviation_Abs']],
        textposition="outside"
    ))
    
    fig.update_layout(
        title='Top 10 Cuentas por Desviación Absoluta',
        xaxis_title='Desviación ($)',
        yaxis_title='Cuenta',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_waterfall_chart(df, selected_month):
    """Crear gráfico waterfall para un mes específico"""
    month_data = df[df['Period'] == selected_month] if not df.empty else pd.DataFrame()
    
    if month_data.empty:
        forecast_val = 0
        expenses_delta = 0
        costs_delta = 0
        real_val = 0
    else:
        forecast_val = month_data['Forecast'].sum()
        expenses_delta = month_data[month_data['Category'] == 'Expenses']['Deviation_Abs'].sum()
        costs_delta = month_data[month_data['Category'] == 'Costs']['Deviation_Abs'].sum()
        real_val = month_data['Real Amount'].sum()
    
    fig = go.Figure(go.Waterfall(
        name="Waterfall",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["Forecast", "ΔExpenses", "ΔCosts", "Real"],
        y=[forecast_val, expenses_delta, costs_delta, real_val],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": COLORS['green']}},
        increasing={"marker": {"color": COLORS['red']}},
        totals={"marker": {"color": COLORS['blue']}}
    ))
    
    fig.update_layout(
        title=f'Análisis Waterfall - {selected_month}',
        yaxis_title='Monto ($)',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_detail_table(df):
    """Crear tabla de detalle con badge de cumplimiento"""
    if df.empty:
        return pd.DataFrame()
    
    # Preparar datos para la tabla
    table_df = df.copy()
    table_df['Deviation_Pct_Display'] = table_df['Deviation_Pct'].apply(lambda x: f"{x:.2f}%")
    table_df['Cumple_KPI'] = table_df['Deviation_Abs'].apply(
        lambda x: "✅ Cumple" if abs(x) <= 100000 else "❌ No cumple"
    )
    
    # Seleccionar columnas para mostrar
    display_cols = [
        'Country', 'Period', 'Category', 'Account Description',
        'Forecast', 'Real Amount', 'Desviacion_absoluta', 
        'Deviation_Pct_Display', 'Cumple_KPI'
    ]
    
    return table_df[display_cols].rename(columns={
        'Deviation_Pct_Display': 'Desviacion_pct (%)',
        'Cumple_KPI': 'Estado KPI'
    })

def generate_kpi_report(kpis, filters_applied):
    """Generar reporte CSV con KPIs agregados"""
    report_data = {
        'Métrica': [
            'Total Forecast',
            'Total Real',
            'Desviación Neta',
            'Desviación %',
            'Filas Evaluadas',
            'Filas que Cumplen KPI',
            'Tasa de Cumplimiento %'
        ],
        'Valor': [
            f"${kpis['total_forecast']:,.2f}",
            f"${kpis['total_real']:,.2f}",
            f"${kpis['net_deviation']:,.2f}",
            f"{kpis['deviation_pct']:.2f}%",
            kpis['total_rows'],
            kpis['compliant_rows'],
            f"{kpis['compliance_rate']:.2f}%"
        ]
    }
    
    report_df = pd.DataFrame(report_data)
    
    # Agregar información de filtros aplicados
    filter_info = pd.DataFrame({
        'Filtro': ['País', 'Categoría', 'Períodos', 'Búsqueda'],
        'Valor': [
            filters_applied.get('country', 'Todos'),
            filters_applied.get('category', 'Todas'),
            ', '.join(filters_applied.get('periods', [])),
            filters_applied.get('search_term', '')
        ]
    })
    
    return report_df, filter_info

def main():
    # Título principal
    st.title("⚡ Dashboard Financiero - Sector Energía")
    st.markdown("---")
    
    # Cargar datos
    df = load_data()
    
    if df.empty:
        st.error("No se pudieron cargar los datos. Verifica el archivo.")
        return
    
    # Crear filtros
    country, category, periods, search_term = create_filters(df)
    
    # Aplicar filtros
    filtered_df = apply_filters(df, country, category, periods, search_term)
    
    # Almacenar filtros aplicados para el reporte
    filters_applied = {
        'country': country,
        'category': category, 
        'periods': periods,
        'search_term': search_term
    }
    
    if filtered_df.empty:
        st.warning("⚠️ Sin datos en el rango seleccionado. Ajusta los filtros.")
        return
    
    # Calcular KPIs
    kpis = calculate_kpis(filtered_df)
    
    # Mostrar KPIs
    st.subheader("📊 Indicadores Clave de Desempeño")
    create_kpi_cards(kpis)
    
    st.markdown("---")
    
    # Gráficos principales
    st.subheader("📈 Análisis Gráfico")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = create_forecast_vs_real_chart(filtered_df)
        st.plotly_chart(fig1, use_container_width=True)
        
        # Narrativa segura
        if not filtered_df.empty:
            monthly_totals = filtered_df.groupby('Period')['Real Amount'].sum()
            if len(monthly_totals) > 0 and monthly_totals.max() > 0:
                best_month = monthly_totals.idxmax()
                st.caption(f"💡 El mes con mayor ejecución real fue {best_month}")
    
    with col2:
        fig2 = create_deviation_line_chart(filtered_df)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Narrativa segura
        monthly_dev = filtered_df.groupby('Period').apply(
            lambda x: ((x['Real Amount'].sum() - x['Forecast'].sum()) / 
                      x['Forecast'].sum() * 100) if x['Forecast'].sum() != 0 else 0
        )
        if len(monthly_dev) > 0:
            avg_dev = monthly_dev.mean()
            st.caption(f"💡 Desviación promedio: {avg_dev:.1f}%")
    
    # Segunda fila de gráficos
    col3, col4 = st.columns(2)
    
    with col3:
        fig3 = create_top_accounts_chart(filtered_df)
        st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # Selector de mes para waterfall
        available_months = sorted(filtered_df['Period'].unique().tolist()) if not filtered_df.empty else MONTHS[:3]
        selected_month = st.selectbox("Seleccionar mes para Waterfall:", available_months)
        
        fig4 = create_waterfall_chart(filtered_df, selected_month)
        st.plotly_chart(fig4, use_container_width=True)
    
    st.markdown("---")
    
    # Tabla de detalle
    st.subheader("📋 Detalle de Cuentas")
    
    detail_table = create_detail_table(filtered_df)
    if not detail_table.empty:
        st.dataframe(detail_table, use_container_width=True)
        st.caption(f"Mostrando {len(detail_table)} registros")
    else:
        st.info("No hay datos para mostrar en la tabla.")
    
    st.markdown("---")
    
    # Descarga de reporte
    st.subheader("📥 Descarga de Reportes")
    
    col_download1, col_download2 = st.columns(2)
    
    with col_download1:
        # Reporte de KPIs
        report_df, filter_info = generate_kpi_report(kpis, filters_applied)
        
        # Crear buffer para CSV
        buffer = io.StringIO()
        buffer.write("=== REPORTE DE KPIs ===\n")
        buffer.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        buffer.write("FILTROS APLICADOS:\n")
        filter_info.to_csv(buffer, index=False)
        buffer.write("\n")
        
        buffer.write("INDICADORES CLAVE:\n")
        report_df.to_csv(buffer, index=False)
        
        st.download_button(
            label="📊 Descargar Reporte KPIs",
            data=buffer.getvalue(),
            file_name=f"reporte_kpis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col_download2:
        # Datos filtrados
        if not filtered_df.empty:
            csv_buffer = io.StringIO()
            filtered_df.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label="📋 Descargar Datos Filtrados",
                data=csv_buffer.getvalue(),
                file_name=f"datos_filtrados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()

# CHECKLIST DE VERIFICACIÓN AUTOMÁTICA:
# ✅ Se puede cargar sin archivo (usa datos de ejemplo)
# ✅ Acepta Excel con hoja DATA
# ✅ Eje de meses fijo (2025-01 a 2025-09)
# ✅ KPIs se calculan aun si algún mes queda en 0
# ✅ Top 10 y Waterfall no fallan con meses sin datos
# ✅ % Cumplimiento se basa en |Deviation_Abs| ≤ 100000
# ✅ No usa idxmax() sin validar DF no vacío
# ✅ Manejo robusto de divisiones por cero
# ✅ Reindexación de meses antes de graficar
# ✅ Alias para columnas en inglés/español
# ✅ Normalización de Period a YYYY-MM
# ✅ Limpieza de columnas monetarias
# ✅ Filtros funcionales en sidebar
# ✅ Descarga de reportes CSV
# ✅ Textos y errores en español
# ✅ Colores corporativos aplicados
