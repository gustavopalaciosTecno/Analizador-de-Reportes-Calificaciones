import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import re

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Calificaciones",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard de Análisis de Calificaciones")
st.markdown("---")


def extract_data_from_pdf(pdf_file):
    """
    Extrae los datos del PDF específico con formato de tabla
    """
    data = []

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extraer la tabla directamente
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        # Buscar la tabla que tiene los datos (la primera después del encabezado)
                        for row in table:
                            if row and len(row) >= 5:
                                # Verificar que sea una fila de datos (tiene email y %)
                                nombre = row[0] if row[0] else ''
                                email = row[1] if row[1] else ''
                                calificacion = row[2] if row[2] else ''
                                fecha = row[3] if row[3] else ''
                                tiempo = row[4] if row[4] else ''

                                # Limpiar y validar
                                if email and '@' in email and '%' in calificacion:
                                    # Limpiar nombre
                                    nombre = nombre.strip()

                                    # Extraer porcentaje
                                    calif_match = re.search(r'(\d+(?:\.\d+)?)', calificacion)
                                    if calif_match:
                                        calificacion_num = float(calif_match.group(1))

                                        # Limpiar fecha (puede tener hora)
                                        fecha_limpia = fecha.split()[0] if fecha else ''

                                        data.append({
                                            'Nombre': nombre,
                                            'Email': email.strip(),
                                            'Calificación': calificacion_num,
                                            'Fecha': fecha_limpia,
                                            'Tiempo': tiempo.strip()
                                        })

                # Método alternativo: extraer por texto si las tablas no funcionan
                if not data:
                    text = page.extract_text()
                    lines = text.split('\n')

                    # Patrón para encontrar líneas con datos
                    for line in lines:
                        # Buscar líneas que contengan email y porcentaje
                        if '@' in line and '%' in line:
                            # Dividir por espacios o tabulaciones
                            parts = re.split(r'\s{2,}|\t', line)
                            parts = [p.strip() for p in parts if p.strip()]

                            if len(parts) >= 5:
                                # Intentar identificar cada campo
                                nombre = parts[0]
                                email = next((p for p in parts if '@' in p), '')
                                calificacion = next((p for p in parts if '%' in p), '')

                                # Encontrar fecha (formato DD/MM/YYYY)
                                fecha = next((p for p in parts if re.match(r'\d{2}/\d{2}/\d{4}', p)), '')

                                # El resto es tiempo
                                tiempo_parts = [p for p in parts if p not in [nombre, email, calificacion, fecha]]
                                tiempo = ' '.join(tiempo_parts) if tiempo_parts else ''

                                if email and calificacion:
                                    calif_num = float(re.search(r'(\d+(?:\.\d+)?)', calificacion).group(1))

                                    data.append({
                                        'Nombre': nombre,
                                        'Email': email,
                                        'Calificación': calif_num,
                                        'Fecha': fecha,
                                        'Tiempo': tiempo
                                    })

    except Exception as e:
        st.error(f"Error al leer el PDF: {str(e)}")
        return None

    if data:
        df = pd.DataFrame(data)
        # Eliminar duplicados exactos si los hay
        df = df.drop_duplicates()
        return df
    else:
        return None


# Sidebar para carga de archivo
with st.sidebar:
    st.header("📁 Carga de archivo PDF")
    uploaded_file = st.file_uploader("Seleccionar archivo PDF", type=['pdf'])

    if uploaded_file is not None:
        if st.button("🔄 Procesar PDF", type="primary"):
            with st.spinner("Extrayendo datos del PDF..."):
                df = extract_data_from_pdf(uploaded_file)

            if df is not None and not df.empty:
                st.session_state['df'] = df
                st.success(f"✅ ¡Éxito! Se extrajeron {len(df)} registros")
                st.info(f"📊 Alumnos únicos: {df['Nombre'].nunique()}")
            else:
                st.error("No se pudieron extraer datos. Verifica el formato del PDF.")
                st.session_state['df'] = None

# Mostrar filtros si hay datos
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']

    with st.sidebar:
        st.markdown("---")
        st.header("🔍 Filtros")

        # Filtro por nombre
        nombres = ['Todos'] + sorted(df['Nombre'].unique().tolist())
        filtro_nombre = st.selectbox("👨‍🎓 Filtrar por nombre", nombres)

        # Rango de calificación
        st.subheader("📊 Rango de calificación")
        col1, col2 = st.columns(2)
        with col1:
            min_score = st.number_input("Mínimo (%)", min_value=0, max_value=100, value=0, step=5)
        with col2:
            max_score = st.number_input("Máximo (%)", min_value=0, max_value=100, value=100, step=5)

        if min_score > max_score:
            st.warning("⚠️ El mínimo no puede ser mayor al máximo")
            min_score, max_score = max_score, min_score

    # Aplicar filtros
    df_filtrado = df.copy()

    if filtro_nombre != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Nombre'] == filtro_nombre]

    df_filtrado = df_filtrado[
        (df_filtrado['Calificación'] >= min_score) &
        (df_filtrado['Calificación'] <= max_score)
        ]

    # Calcular estadísticas
    nota_corte = 60
    aprobados = df_filtrado[df_filtrado['Calificación'] >= nota_corte]
    desaprobados = df_filtrado[df_filtrado['Calificación'] < nota_corte]

    # Métricas principales
    st.markdown("## 📈 Estadísticas Generales")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📝 Total Intentos", len(df_filtrado))
    with col2:
        st.metric("✅ Aprobados", len(aprobados),
                  delta=f"{len(aprobados) / len(df_filtrado) * 100:.1f}%" if len(df_filtrado) > 0 else "0%")
    with col3:
        st.metric("❌ Desaprobados", len(desaprobados),
                  delta=f"{len(desaprobados) / len(df_filtrado) * 100:.1f}%" if len(df_filtrado) > 0 else "0%")
    with col4:
        promedio = df_filtrado['Calificación'].mean() if len(df_filtrado) > 0 else 0
        st.metric("📊 Promedio General", f"{promedio:.1f}%")
    with col5:
        mejor_nota = df_filtrado['Calificación'].max() if len(df_filtrado) > 0 else 0
        st.metric("🏆 Mejor Nota", f"{mejor_nota:.1f}%")

    st.markdown("---")

    # Gráficos
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Distribución de Calificaciones")
        fig_hist = px.histogram(
            df_filtrado,
            x='Calificación',
            nbins=20,
            title="Histograma de Calificaciones",
            labels={'Calificación': 'Calificación (%)', 'count': 'Cantidad de intentos'},
            color_discrete_sequence=['#FF6B6B']
        )
        fig_hist.add_vline(x=nota_corte, line_dash="dash", line_color="green",
                           annotation_text=f"Nota corte: {nota_corte}%")
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        st.subheader("🥧 Proporción Aprobados vs Desaprobados")
        fig_pie = px.pie(
            values=[len(aprobados), len(desaprobados)],
            names=['✅ Aprobados', '❌ Desaprobados'],
            title="Estado de los Intentos",
            color_discrete_sequence=['#4CAF50', '#FF5252'],
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Gráfico de rendimiento por estudiante
    st.subheader("📈 Rendimiento por Estudiante")

    # Calcular estadísticas por estudiante
    stats_estudiante = df_filtrado.groupby('Nombre').agg({
        'Calificación': ['mean', 'max', 'min', 'count']
    }).round(1)

    stats_estudiante.columns = ['Promedio', 'Mejor Nota', 'Peor Nota', 'Intentos']
    stats_estudiante = stats_estudiante.sort_values('Promedio', ascending=True)

    fig_bar = px.bar(
        x=stats_estudiante.index,
        y=stats_estudiante['Promedio'],
        title="Promedio de Calificaciones por Estudiante",
        labels={'x': 'Estudiante', 'y': 'Promedio (%)'},
        color=stats_estudiante['Promedio'],
        color_continuous_scale=['#FF5252', '#FFD700', '#4CAF50'],
        text=stats_estudiante['Promedio']
    )
    fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_bar.add_hline(y=nota_corte, line_dash="dash", line_color="red",
                      annotation_text=f"Nota corte: {nota_corte}%")
    fig_bar.update_layout(height=500)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Tabla detallada
    st.markdown("---")
    st.subheader("📋 Datos Detallados")

    # Preparar tabla para mostrar
    df_display = df_filtrado.copy()
    df_display['Calificación'] = df_display['Calificación'].apply(lambda x: f"{x:.2f}%")
    df_display['Estado'] = df_filtrado['Calificación'].apply(
        lambda x: '✅ Aprobado' if x >= nota_corte else '❌ Desaprobado'
    )

    # Ordenar por fecha (más reciente primero)
    df_display['Fecha_orden'] = pd.to_datetime(df_display['Fecha'], format='%d/%m/%Y', errors='coerce')
    df_display = df_display.sort_values('Fecha_orden', ascending=False)
    df_display = df_display.drop('Fecha_orden', axis=1)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Nombre": st.column_config.TextColumn("Nombre", width="medium"),
            "Email": st.column_config.TextColumn("Email", width="large"),
            "Calificación": st.column_config.TextColumn("Calificación", width="small"),
            "Fecha": st.column_config.TextColumn("Fecha", width="small"),
            "Tiempo": st.column_config.TextColumn("Tiempo", width="medium"),
            "Estado": st.column_config.TextColumn("Estado", width="small")
        }
    )

    # Botón de descarga
    csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name="calificaciones_filtradas.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Mostrar estadísticas adicionales
    with st.expander("📊 Estadísticas Detalladas"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Top 5 Mejores Notas**")
            top5 = df_filtrado.nlargest(5, 'Calificación')[['Nombre', 'Calificación', 'Fecha']]
            top5['Calificación'] = top5['Calificación'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(top5, hide_index=True, use_container_width=True)

        with col2:
            st.write("**Top 5 Peores Notas**")
            bottom5 = df_filtrado.nsmallest(5, 'Calificación')[['Nombre', 'Calificación', 'Fecha']]
            bottom5['Calificación'] = bottom5['Calificación'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(bottom5, hide_index=True, use_container_width=True)

else:
    st.info(
        "👈 **Instrucciones:**\n\n1. Sube un archivo PDF en la barra lateral\n2. Haz clic en 'Procesar PDF'\n3. Espera a que se extraigan los datos\n4. Usa los filtros para analizar los resultados")

    st.markdown("""
    ### 📌 Formato esperado del PDF:

    El PDF debe contener una tabla con las siguientes columnas:
    - **Nombre** del estudiante
    - **Email** 
    - **Calificación** (con símbolo %)
    - **Fecha** (formato DD/MM/AAAA)
    - **Tiempo** de realización

    ### ✅ Características del Dashboard:
    - Extracción automática de datos del PDF
    - Filtros por nombre y rango de calificación
    - Cálculo de aprobados/desaprobados (nota corte: 60%)
    - Gráficos interactivos
    - Exportación a CSV
    """)