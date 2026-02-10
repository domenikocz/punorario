import streamlit as st
import pandas as pd
import datetime

# Aumenta il limite di caricamento (opzionale se eseguito localmente)
# st.set_page_config deve essere la PRIMA istruzione Streamlit
st.set_page_config(page_title="GME 15-min Analyzer", layout="wide")

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
    # GME 1-24 -> Python 0-23
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

st.title("GME 15-min Analyzer (2025-2026)")

with st.sidebar:
    anno_sel = st.selectbox("Anno", [2025, 2026])
    mese_sel = st.selectbox("Mese", list(range(1, 13)))
    st.info("Nota: Per file grandi l'upload potrebbe richiedere qualche secondo.")

uploaded_file = st.file_uploader("Carica file Excel GME (15 min)", type=['xlsx'])

if uploaded_file:
    try:
        # Caricamento ottimizzato: leggiamo solo le colonne necessarie
        # Il file GME ha spesso molte zone (NORD, SUD, ecc.) che appesantiscono la lettura
        df = pd.read_excel(uploaded_file)
        
        # Pulizia nomi colonne
        df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
        
        col_data = "Data/Date (YYYYMMDD)"
        col_ora = "Ora /Hour"
        col_pun = "PUN INDEX GME"

        # Pre-conversione per velocizzare il filtro
        df['Data_Str'] = df[col_data].astype(str)
        df['Data_DT'] = pd.to_datetime(df['Data_Str'], format='%Y%m%d')
        
        # Filtro immediato per ridurre il peso dei dati in memoria
        mask = (df['Data_DT'].dt.year == anno_sel) & (df['Data_DT'].dt.month == mese_sel)
        df_mese = df.loc[mask].copy()

        if df_mese.empty:
            st.warning(f"Nessun dato trovato per {mese_sel}/{anno_sel}.")
        else:
            df_mese['Data_Obj'] = df_mese['Data_DT'].dt.date
            df_mese['Ora'] = df_mese[col_ora]
            
            festivita = get_festivita_italiane(anno_sel)
            df_mese['Fascia'] = df_mese.apply(lambda r: assegna_fascia(r, festivita), axis=1)

            # CALCOLO MEDIE MENSILI
            f1 = df_mese[df_mese['Fascia'] == 'F1'][col_pun].mean()
            f2 = df_mese[df_mese['Fascia'] == 'F2'][col_pun].mean()
            f3 = df_mese[df_mese['Fascia'] == 'F3'][col_pun].mean()
            f0 = df_mese[col_pun].mean()

            st.subheader(f"Medie Mensili {mese_sel}/{anno_sel}")
            res_df = pd.DataFrame({
                "Fascia": ["F0 (PUN Medio)", "F1", "F2", "F3"],
                "€/MWh": [f0, f1, f2, f3],
                "€/kWh": [f0/1000, f1/1000, f2/1000, f3/1000]
            })
            st.table(res_df.style.format({'€/MWh': '{:.2f}', '€/kWh': '{:.5f}'}))

            # CALCOLO PUN ORARIO (Media dei 4 quarti d'ora)
            st.subheader("PUN Orario (Media dei 15 min)")
            # Raggruppiamo per Data e Ora per avere il valore orario richiesto
            pun_orario = df_mese.groupby([col_data, 'Ora', 'Fascia'])[col_pun].mean().reset_index()
            pun_orario.columns = ['Data', 'Ora', 'Fascia', 'PUN_Orario_MWh']
            pun_orario['PUN_Orario_kWh'] = pun_orario['PUN_Orario_MWh'] / 1000
            
            st.dataframe(pun_orario, use_container_width=True)
            
            # Download dei risultati orari
            csv = pun_orario.to_csv(index=False).encode('utf-8')
            st.download_button("Scarica PUN Orario in CSV", csv, f"PUN_Orario_{mese_sel}_{anno_sel}.csv", "text/csv")

    except Exception as e:
        st.error(f"Si è verificato un errore durante l'elaborazione: {e}")
