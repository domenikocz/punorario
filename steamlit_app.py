import streamlit as st
import pandas as pd
import datetime

def get_festivita_italiane(anno):
    """Calcola le festività nazionali italiane."""
    festivita = [
        datetime.date(anno, 1, 1), datetime.date(anno, 1, 6),
        datetime.date(anno, 4, 25), datetime.date(anno, 5, 1),
        datetime.date(anno, 6, 2), datetime.date(anno, 8, 15),
        datetime.date(anno, 11, 1), datetime.date(anno, 12, 8),
        datetime.date(anno, 12, 25), datetime.date(anno, 12, 26),
    ]
    # Pasquetta
    a, b, c = anno % 19, anno // 100, anno % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese_p = (h + l - 7 * m + 114) // 31
    giorno_p = ((h + l - 7 * m + 114) % 31) + 1
    festivita.append(datetime.date(anno, mese_p, giorno_p) + datetime.timedelta(days=1))
    return festivita

def assegna_fascia(row, festivita):
    # L'ora nel file GME è 1-24. Python usa 0-23.
    ora_zero_based = int(row['Ora']) - 1
    data_obj = row['Data_Obj']
    giorno_sett = data_obj.weekday() # 0=Lun, 6=Dom

    if giorno_sett == 6 or data_obj in festivita:
        return 'F3'
    if giorno_sett == 5:
        return 'F2' if 7 <= ora_zero_based < 23 else 'F3'
    if 8 <= ora_zero_based < 19:
        return 'F1'
    elif ora_zero_based == 7 or 19 <= ora_zero_based < 23:
        return 'F2'
    else:
        return 'F3'

st.title("GME 15-min Analyzer (2025-2026)")

with st.sidebar:
    anno_sel = st.selectbox("Anno", [2025, 2026])
    mese_sel = st.selectbox("Mese", list(range(1, 13)))

uploaded_file = st.file_uploader("Carica file Excel GME (15 min)", type=['xlsx'])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        # Pulizia nomi colonne da invii a capo
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        # Identificazione colonne
        col_data = "Data/Date (YYYYMMDD)"
        col_ora = "Ora /Hour"
        col_pun = "PUN INDEX GME"
        
        # Conversione e Filtro
        df['Data_Str'] = df[col_data].astype(str)
        df['Data_Obj'] = pd.to_datetime(df['Data_Str'], format='%Y%m%d').dt.date
        
        df_filtered = df[(pd.to_datetime(df['Data_Str']).dt.year == anno_sel) & 
                         (pd.to_datetime(df['Data_Str']).dt.month == mese_sel)].copy()

        if df_filtered.empty:
            st.warning("Nessun dato per il periodo selezionato.")
        else:
            festivita = get_festivita_italiane(anno_sel)
            # Rinomino per comodità
            df_filtered['Ora'] = df_filtered[col_ora]
            df_filtered['Fascia'] = df_filtered.apply(lambda r: assegna_fascia(r, festivita), axis=1)

            # 1. Calcolo Medie Fasce (F1, F2, F3, F0)
            f1 = df_filtered[df_filtered['Fascia'] == 'F1'][col_pun].mean()
            f2 = df_filtered[df_filtered['Fascia'] == 'F2'][col_pun].mean()
            f3 = df_filtered[df_filtered['Fascia'] == 'F3'][col_pun].mean()
            f0 = df_filtered[col_pun].mean()

            st.header(f"Medie Mensili {mese_sel}/{anno_sel}")
            res_df = pd.DataFrame({
                "Fascia": ["F0 (Totale)", "F1", "F2", "F3"],
                "€/MWh": [f0, f1, f2, f3],
                "€/kWh": [f0/1000, f1/1000, f2/1000, f3/1000]
            })
            st.table(res_df.style.format({'€/MWh': '{:.2f}', '€/kWh': '{:.5f}'}))

            # 2. PUN Orario (Media dei 4 periodi per ogni ora)
            st.header("Dettaglio PUN Orario")
            pun_orario = df_filtered.groupby([col_data, 'Ora', 'Fascia'])[col_pun].mean().reset_index()
            pun_orario.columns = ['Data', 'Ora', 'Fascia', 'PUN Orario (€/MWh)']
            
            st.dataframe(pun_orario)
            
            # Grafico del PUN orario
            st.line_chart(pun_orario['PUN Orario (€/MWh)'])

    except Exception as e:
        st.error(f"Errore nel caricamento: {e}")
