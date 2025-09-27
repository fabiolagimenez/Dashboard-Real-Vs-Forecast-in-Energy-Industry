import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Control Presupuestario",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("📊 Dashboard de Control Presupuestario")
st.markdown("---")

@st.cache_data
def load_data(uploaded_file):
    """Cargar y procesar los datos del archivo Excel"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name='DATA')
        
        # Verificar columnas requeridas
        required_columns = ['Category', 'Account Description', 'Country', 'Period', 
                          'Real Amount', 'Forecast', 'Desviacion_absoluta', 'Desviacion_pct']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Faltan las siguientes columnas en el archivo: {missing_columns}")
            return None
            
        # Convertir Period a datetime para mejor manejo
        df['Period_Date'] = pd.to_datetime(df['Period'], format='%Y-%m')
        df['Year_Month'] = df['Period']
        
        # Limpiar nombres de países
        country_mapping = {
            'Dominican Republic': 'República Dominicana',
            'Mexico': 'México',
            'Panama': 'Panamá'
        }
        df['Country'] = df['Country'].map(country_mapping).fillna(df['Country'])
        
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo: {str(e)}")
        return None

def calculate_kpis(df):
    """Calcular los KPIs principales"""
    total_forecast = df['Forecast'].sum()
    total_real = df['Real Amount'].sum()
    total_deviation_abs = df['Desviacion_absoluta'].sum()
    total_deviation_pct = (total_deviation_abs / total_forecast * 100) if total_forecast != 0 else 0
    
    # Calcular % Cumplimiento KPI (desviación absoluta ≤ 100,000 USD)
    within_kpi = df[df['Desviacion_absoluta'].abs() <= 100000].shape[0]
    total_records = df.shape[0]
    kpi_compliance = (within_kpi / total_records * 100) if total_records != 0 else 0
    
    return {
        'total_forecast': total_forecast,
        'total_real': total_real,
        'total_deviation_abs': total_deviation_abs,
        'total_deviation_pct': total_deviation_pct,
        'kpi_compliance': kpi_compliance
    }

def create_kpi_cards(kpis):
    """Crear las tarjetas de KPIs"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="💰 Total Forecast",
            value=f"${kpis['total_forecast']:,.0f}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💵 Total Real",
            value=f"${kpis['total_real']:,.0f}",
            delta=None
        )
    
    with col3:
        deviation_color = "normal" if abs(kpis['total_deviation_abs']) <= 100000 else "inverse"
        st.metric(
            label="📈 Desviación Absoluta",
            value=f"${kpis['total_deviation_abs']:,.0f}",
            delta=f"{kpis['total_deviation_pct']:.1f}%"
        )
    
    with col4:
        pct_color = "normal" if abs(kpis['total_deviation_pct']) <= 5 else "inverse"
        st.metric(
            label="📊 % Desviación Total",
            value=f"{kpis['total_deviation_pct']:.1f}%",
            delta=None
        )
    
    with col5:
        compliance_color = "normal" if kpis['kpi_compliance'] >= 80 else "inverse"
        st.metric(
            label="✅ % Cumplimiento KPI",
            value=f"{kpis['kpi_compliance']:.1f}%",
            delta=None
        )

def create_forecast_vs_real_chart(df):
    """Crear gráfico de barras agrupadas Forecast vs Real por mes"""
    monthly_data = df.groupby('Year_Month').agg({
        'Forecast': 'sum',
        'Real Amount': 'sum',
        'Desviacion_absoluta': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=monthly_data['Year_Month'],
        y=monthly_data['Forecast'],
        name='Forecast',
        marker_color='lightblue',
        text=monthly_data['Forecast'],
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        x=monthly_data['Year_Month'],
        y=monthly_data['Real Amount'],
        name='Real',
        marker_color='darkblue',
        text=monthly_data['Real Amount'],
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    ))
    
    fig.update_layout(
        title='💹 Forecast vs Real por Mes',
        xaxis_title='Período',
        yaxis_title='Monto (USD)',
        barmode='group',
        height=500,
        showlegend=True
    )
    
    # Narrativa automática
    max_deviation_month = monthly_data.loc[monthly_data['Desviacion_absoluta'].abs().idxmax()]
    avg_deviation = monthly_data['Desviacion_absoluta'].mean()
    
    narrative = f"""
    📝 **Análisis:** El mes con mayor desviación fue **{max_deviation_month['Year_Month']}** 
    con una desviación de **${max_deviation_month['Desviacion_absoluta']:,.0f}**. 
    En promedio, las desviaciones son {'**positivas (sobrecosto)**' if avg_deviation > 0 else '**negativas (ahorro)**'} 
    con un promedio de **${avg_deviation:,.0f}** mensual.
    """
    
    return fig, narrative

def create_deviation_trend_chart(df):
    """Crear gráfico de línea de desviación porcentual por mes"""
    monthly_data = df.groupby('Year_Month').agg({
        'Forecast': 'sum',
        'Real Amount': 'sum',
        'Desviacion_absoluta': 'sum'
    }).reset_index()
    
    monthly_data['Desviacion_pct'] = (monthly_data['Desviacion_absoluta'] / monthly_data['Forecast'] * 100)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_data['Year_Month'],
        y=monthly_data['Desviacion_pct'],
        mode='lines+markers',
        name='% Desviación',
        line=dict(color='red', width=3),
        marker=dict(size=8),
        text=monthly_data['Desviacion_pct'],
        texttemplate='%{text:.1f}%',
        textposition='top center'
    ))
    
    # Línea de referencia en 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  annotation_text="Línea Base (0%)")
    
    fig.update_layout(
        title='📈 Tendencia de Desviación Porcentual por Mes',
        xaxis_title='Período',
        yaxis_title='% Desviación',
        height=400,
        showlegend=True
    )
    
    # Narrativa
    max_dev_month = monthly_data.loc[monthly_data['Desviacion_pct'].abs().idxmax()]
    trend = "creciente" if monthly_data['Desviacion_pct'].iloc[-1] > monthly_data['Desviacion_pct'].iloc[0] else "decreciente"
    
    narrative = f"""
    📝 **Análisis:** La mayor desviación porcentual ocurrió en **{max_dev_month['Year_Month']}** 
    con **{max_dev_month['Desviacion_pct']:.1f}%**. La tendencia general es **{trend}** 
    a lo largo del período analizado.
    """
    
    return fig, narrative

def create_top_accounts_chart(df):
    """Crear gráfico de top 10 cuentas con mayor desviación absoluta"""
    account_deviations = df.groupby('Account Description')['Desviacion_absoluta'].sum().reset_index()
    account_deviations['Abs_Deviation'] = account_deviations['Desviacion_absoluta'].abs()
    top_10 = account_deviations.nlargest(10, 'Abs_Deviation')
    
    # Colores según si es positivo o negativo
    colors = ['red' if x > 0 else 'green' for x in top_10['Desviacion_absoluta']]
    
    fig = go.Figure(go.Bar(
        y=top_10['Account Description'],
        x=top_10['Desviacion_absoluta'],
        orientation='h',
        marker_color=colors,
        text=top_10['Desviacion_absoluta'],
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    ))
    
    fig.update_layout(
        title='🏆 Top 10 Cuentas con Mayor Desviación Absoluta',
        xaxis_title='Desviación (USD)',
        yaxis_title='Cuenta',
        height=500,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    # Narrativa
    worst_account = top_10.iloc[0]
    over_budget = len(top_10[top_10['Desviacion_absoluta'] > 0])
    
    narrative = f"""
    📝 **Análisis:** La cuenta con mayor desviación es **{worst_account['Account Description']}** 
    con **${worst_account['Desviacion_absoluta']:,.0f}**. De las top 10 cuentas, 
    **{over_budget}** están sobre presupuesto y **{10-over_budget}** bajo presupuesto.
    """
    
    return fig, narrative

def create_waterfall_chart(df):
    """Crear gráfico waterfall por categoría"""
    category_data = df.groupby('Category')['Desviacion_absoluta'].sum().reset_index()
    
    fig = go.Figure(go.Waterfall(
        name="Desviaciones por Categoría",
        orientation="v",
        measure=["relative"] * len(category_data) + ["total"],
        x=list(category_data['Category']) + ['Total'],
        textposition="outside",
        text=[f"${x:,.0f}" for x in category_data['Desviacion_absoluta']] + [f"${category_data['Desviacion_absoluta'].sum():,.0f}"],
        y=list(category_data['Desviacion_absoluta']) + [category_data['Desviacion_absoluta'].sum()],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        title="🌊 Análisis Waterfall por Categoría (Costs vs Expenses)",
        xaxis_title="Categoría",
        yaxis_title="Desviación (USD)",
        height=400
    )
    
    # Narrativa
    worst_category = category_data.loc[category_data['Desviacion_absoluta'].abs().idxmax()]
    
    narrative = f"""
    📝 **Análisis:** La categoría **{worst_category['Category']}** tiene la mayor desviación 
    con **${worst_category['Desviacion_absoluta']:,.0f}**. El impacto total combinado 
    es de **${category_data['Desviacion_absoluta'].sum():,.0f}**.
    """
    
    return fig, narrative

def main():
    # Sidebar para filtros
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Upload de archivo
        uploaded_file = st.file_uploader(
            "📁 Cargar archivo Excel",
            type=['xlsx', 'xls'],
            help="Sube tu archivo 'Data Indicador Real Vs Forecast.xlsx'"
        )
        
        if uploaded_file is None:
            st.info("👆 Por favor, carga tu archivo Excel para comenzar el análisis")
            return
    
    # Cargar datos
    df = load_data(uploaded_file)
    
    if df is None:
        return
    
    # Filtros dinámicos en sidebar
    with st.sidebar:
        st.markdown("---")
        
        # Filtro de países
        countries = ['Todos'] + sorted(df['Country'].unique().tolist())
        selected_countries = st.multiselect(
            "🌍 Seleccionar Países",
            countries,
            default=['Todos']
        )
        
        # Filtro de categorías
        categories = ['Todas'] + sorted(df['Category'].unique().tolist())
        selected_categories = st.selectbox(
            "📂 Seleccionar Categoría",
            categories
        )
        
        # Filtro de períodos
        periods = sorted(df['Year_Month'].unique().tolist())
        selected_periods = st.select_slider(
            "📅 Rango de Períodos",
            options=periods,
            value=(periods[0], periods[-1])
        )
        
        st.markdown("---")
        st.info("💡 Tip: Usa los filtros para análisis específicos por región, categoría o período.")
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    if 'Todos' not in selected_countries and selected_countries:
        filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
    
    if selected_categories != 'Todas':
        filtered_df = filtered_df[filtered_df['Category'] == selected_categories]
    
    # Filtro de períodos
    filtered_df = filtered_df[
        (filtered_df['Year_Month'] >= selected_periods[0]) & 
        (filtered_df['Year_Month'] <= selected_periods[1])
    ]
    
    if filtered_df.empty:
        st.warning("⚠️ No hay datos disponibles con los filtros seleccionados.")
        return
    
    # Mostrar información de filtros aplicados
    st.info(f"📋 Mostrando {len(filtered_df)} registros de {len(df)} totales con los filtros aplicados.")
    
    # KPIs principales
    st.subheader("📊 Indicadores Clave de Desempeño (KPIs)")
    kpis = calculate_kpis(filtered_df)
    create_kpi_cards(kpis)
    
    st.markdown("---")
    
    # Gráficos principales
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Análisis Temporal")
        fig1, narrative1 = create_forecast_vs_real_chart(filtered_df)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown(narrative1)
    
    with col2:
        st.subheader("📉 Tendencia de Desviaciones")
        fig2, narrative2 = create_deviation_trend_chart(filtered_df)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown(narrative2)
    
    st.markdown("---")
    
    # Segunda fila de gráficos
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🎯 Cuentas con Mayor Impacto")
        fig3, narrative3 = create_top_accounts_chart(filtered_df)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown(narrative3)
    
    with col4:
        st.subheader("💧 Análisis por Categoría")
        fig4, narrative4 = create_waterfall_chart(filtered_df)
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown(narrative4)
    
    st.markdown("---")
    
    # Tabla de resumen
    with st.expander("📋 Ver Datos Detallados", expanded=False):
        st.subheader("Datos Filtrados")
        st.dataframe(
            filtered_df.style.format({
                'Real Amount': '${:,.2f}',
                'Forecast': '${:,.2f}',
                'Desviacion_absoluta': '${:,.2f}',
                'Desviacion_pct': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        # Opción de descarga
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="💾 Descargar datos filtrados como CSV",
            data=csv,
            file_name="datos_presupuestarios_filtrados.csv",
            mime="text/csv"
        )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            📊 Dashboard de Control Presupuestario | Creado con Streamlit & Plotly
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
