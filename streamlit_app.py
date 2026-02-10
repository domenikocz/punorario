import streamlit as st
import pandas as pd
import datetime
import os

def get_festivita_italiane(anno):
    festivita = [
        datetime.date(anno, 1, 1), datetime.date(anno, 1, 6),
        datetime.date(anno, 4, 25), datetime.date(anno, 5, 1),
        datetime.date(anno, 6, 2), datetime.date(anno, 8, 15),
        datetime.date(anno, 11, 1), datetime.date(anno, 12, 8),
        datetime.date(anno, 12, 25), datetime.date(anno, 12, 26),
    ]
    # Calcolo Pasquetta
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
    ora = int(row['Ora']) - 1
    data_obj = row['Data_Obj']
    giorno_sett = data_obj.weekday()
    if giorno_sett == 6 or data_obj in festivita:
        return 'F3'
    if giorno_sett == 5:
        return 'F2' if 7 <= ora < 23 else 'F3'
    if 8 <= ora < 19:
        return 'F1'
    elif ora == 7 or 19 <= ora < 23:
        return 'F2'
    else:
        return 'F3'

st.set_page_config(page_title="GME Data Reader", layout="wide")
st.title("Analisi PUN Orario da Repository")

# Configurazione file nel repository
# Assicurati che i nomi dei file corrispondano a quelli presenti nella cartella
FILE_2025 = "Anno 2025_12_15.xlsx"
FILE_2026 = "Anno 2026_12_15.xlsx" # Modifica il nome se differente

with st.sidebar:
    st.header("Filtri")
    anno_sel = st.selectbox("Seleziona Anno", [2025, 2026])
    mese_sel = st.selectbox("Seleziona Mese", list(range(1, 13)))

# Selezione automatica del file in base all'anno
file_path = FILE_2025 if anno_sel == 2025 else FILE_2026

if os.path.exists(file_path):
    try:
        @st.cache_data
        def load_data(path):
            df = pd.read_excel(path)
            df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
            return df

        df_raw = load_data(file_path)
        
        col_data = "Data/Date (YYYYMMDD)"
        col_ora = "Ora /Hour"
        col_pun = "PUN INDEX GME"

        # Trasformazione date
        df_raw['Data_DT'] = pd.to_datetime(df_raw[col_data].astype(str), format='%Y%m%d')
        
        # Filtro per mese
        df_mese = df_raw[df_raw['Data_DT'].dt.month == mese_sel].copy()

        if df_mese.empty:
            st.warning(f"Dati non disponibili per il mese {mese_sel}/{anno_sel}")
        else:
            df_mese['Data_Obj'] = df_mese['Data_DT'].dt.date
            df_mese['Ora'] = df_mese[col_ora]
            
            festivita = get_festivita_italiane(anno_sel)
            df_mese['Fascia'] = df_mese.apply(lambda r: assegna_fascia(r, festivita), axis=1)

            # Medie Mensili
            f1 = df_mese[df_mese['Fascia'] == 'F1'][col_pun].mean()
            f2 = df_mese[df_mese['Fascia'] == 'F2'][col_pun].mean()
            f3 = df_mese[df_mese['Fascia'] == 'F3'][col_pun].mean()
            f0 = df_mese[col_pun].mean()

            st.subheader(f"Riepilogo Fasce: {mese_sel}/{anno_sel}")
            res_df = pd.DataFrame({
                "Fascia": ["F0 (PUN Medio)", "F1", "F2", "F3"],
                "€/MWh": [f0, f1, f2, f3],
                "€/kWh": [f0/1000, f1/1000, f2/1000, f3/1000]
            })
            st.table(res_df.style.format({'€/MWh': '{:.2f}', '€/kWh': '{:.5f}'}))

            # PUN Orario
            st.subheader("Dettaglio PUN Orario (Media 15 min)")
            pun_orario = df_mese.groupby([col_data, 'Ora', 'Fascia'])[col_pun].mean().reset_index()
            pun_orario.columns = ['Data', 'Ora', 'Fascia', 'PUN_Orario_MWh']
            pun_orario['PUN_Orario_kWh'] = pun_orario['PUN_Orario_MWh'] / 1000
            
            st.dataframe(pun_orario, use_container_width=True)

    except Exception as e:
        st.error(f"Errore durante l'apertura del file: {e}")
else:
    st.error(f"File non trovato nel repository: {file_path}")
