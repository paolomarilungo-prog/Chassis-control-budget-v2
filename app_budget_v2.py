import streamlit as st
import pandas as pd
import json
import datetime

# --- 1. CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(
    page_title="Automotive Budget Estimator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INIZIALIZZAZIONE DELLA MEMORIA (SESSION STATE) ---
if "admin_ecu" not in st.session_state:
    st.session_state.admin_ecu = ["ECU_Chassis", "ECU_Braking", "ECU_Steering"]
if "admin_models" not in st.session_state:
    st.session_state.admin_models = ["Platform_A", "Platform_B"]
if "admin_vehicles" not in st.session_state:
    st.session_state.admin_vehicles = ["Model_Sport", "Model_GT"]

if "project_data" not in st.session_state:
    st.session_state.project_data = {
        "tipo_budget": "Nuovo veicolo",
        "hc_totali": 10.0,
        "zbb_totali": 5.0,
        "costo_orario_hc": 60.0,
        "costo_orario_zbb": 45.0,
        "css": 2000.0,
        "data_pm": datetime.date.today(),
        "data_sop": datetime.date.today() + datetime.timedelta(days=365),
        "model_line": "Platform_A",
        "veicolo": "Model_Sport",
        "selected_ecus": ["ECU_Chassis"],
        "premesse": "",
        "ecu_inputs": {}  # Conterrà i dati immessi per ogni centralina
    }

# --- 3. FUNZIONI DI EXPORT / IMPORT JSON ---
def esporta_json():
    dati_da_salvare = {
        "admin_ecu": st.session_state.admin_ecu,
        "admin_models": st.session_state.admin_models,
        "admin_vehicles": st.session_state.admin_vehicles,
        "project_data": {**st.session_state.project_data}
    }
    # Convertiamo le date in stringhe per renderle compatibili con il formato JSON
    dati_da_salvare["project_data"]["data_pm"] = dati_da_salvare["project_data"]["data_pm"].isoformat()
    dati_da_salvare["project_data"]["data_sop"] = dati_da_salvare["project_data"]["data_sop"].isoformat()
    return json.dumps(dati_da_salvare, indent=4)

def importa_json(file_caricato):
    try:
        dati = json.load(file_caricato)
        st.session_state.admin_ecu = dati.get("admin_ecu", [])
        st.session_state.admin_models = dati.get("admin_models", [])
        st.session_state.admin_vehicles = dati.get("admin_vehicles", [])
        
        proj = dati.get("project_data", {})
        if "data_pm" in proj:
            proj["data_pm"] = datetime.date.fromisoformat(proj["data_pm"])
        if "data_sop" in proj:
            proj["data_sop"] = datetime.date.fromisoformat(proj["data_sop"])
            
        st.session_state.project_data = proj
        st.success("Dati caricati correttamente!")
        st.rerun()
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {e}")

# --- 4. BARRA LATERALE (SIDEBAR) & NAVIGAZIONE ---
st.sidebar.title("🚗 Menu Principale")
sezione = st.sidebar.radio("Vai a:", ["Sezione Admin (Anagrafiche)", "Sezione Progetto (Stima Costi)"])

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Backup Progetto")

# Pulsante Download
json_output = esporta_json()
st.sidebar.download_button(
    label="📤 Esporta Progetto (JSON)",
    data=json_output,
    file_name=f"budget_{datetime.date.today()}.json",
    mime="application/json",
    use_container_width=True
)

# Pulsante Upload
file_upload = st.sidebar.file_uploader("📥 Importa Progetto (JSON)", type=["json"])
if file_upload is not None:
    if st.sidebar.button("Applica file caricato", use_container_width=True):
        importa_json(file_upload)


# ==============================================================================
# SEZIONE ADMIN (CONFIGURAZIONE DI BASE)
# ==============================================================================
if SECTION := (sezione == "Sezione Admin (Anagrafiche)"):
    st.title("⚙️ Configurazione Anagrafiche di Base")
    st.write("Inserisci o rimuovi gli elementi che popoleranno i menù di scelta nella sezione progetto.")
    
    col1, col2, col3 = st.columns(3)
    
    # Gestione Portfolio ECU
    with col1:
        with st.container(border=True):
            st.markdown("### 🎛️ Portfolio ECU")
            nuova_ecu = st.text_input("Nuova ECU:", key="input_add_ecu")
            if st.button("Aggiungi", key="btn_add_ecu") and nuova_ecu:
                if nueva_ecu not in st.session_state.admin_ecu:
                    st.session_state.admin_ecu.append(nuova_ecu)
                    st.rerun()
            for item in st.session_state.admin_ecu:
                c_text, c_btn = st.columns([4, 1])
                c_text.write(item)
                if c_btn.button("❌", key=f"del_ecu_{item}"):
                    st.session_state.admin_ecu.remove(item)
                    st.rerun()

    # Gestione Model Line
    with col2:
        with st.container(border=True):
            st.markdown("### 📐 Model Line")
            nuovo_modello = st.text_input("Nuova Model Line:", key="input_add_model")
            if st.button("Aggiungi", key="btn_add_model") and nuovo_modello:
                if nuovo_modello not in st.session_state.admin_models:
                    st.session_state.admin_models.append(nuovo_modello)
                    st.rerun()
            for item in st.session_state.admin_models:
                c_text, c_btn = st.columns([4, 1])
                c_text.write(item)
                if c_btn.button("❌", key=f"del_model_{item}"):
                    st.session_state.admin_models.remove(item)
                    st.rerun()

    # Gestione Veicoli
    with col3:
        with st.container(border=True):
            st.markdown("### 🚘 Veicoli")
            nuovo_veicolo = st.text_input("Nuovo Veicolo:", key="input_add_vehicle")
            if st.button("Aggiungi", key="btn_add_vehicle") and nuovo_veicolo:
                if nuovo_veicolo not in st.session_state.admin_vehicles:
                    st.session_state.admin_vehicles.append(nuovo_veicolo)
                    st.rerun()
            for item in st.session_state.admin_vehicles:
                c_text, c_btn = st.columns([4, 1])
                c_text.write(item)
                if c_btn.button("❌", key=f"del_vehicle_{item}"):
                    st.session_state.admin_vehicles.remove(item)
                    st.rerun()


# ==============================================================================
# SEZIONE PROGETTO (STIMA BUDGET)
# ==============================================================================
else:
    st.title("📊 Sviluppo Preventivo e Stima Budget")
    
    # Scorciatoia per accedere ai dati di progetto
    p_data = st.session_state.project_data
    
    # --------------------------------------------------------------------------
    # PARAMETRI GENERALI DI PROGETTO
    # --------------------------------------------------------------------------
    with st.expander("📝 1. Configurazione Iniziale Progetto", expanded=True):
        g_col1, g_col2, g_col3 = st.columns(3)
        
        with g_col1:
            p_data["tipo_budget"] = st.selectbox(
                "Tipo di Budget", ["Nuovo veicolo", "Change request"],
                index=["Nuovo veicolo", "Change request"].index(p_data["tipo_budget"])
            )
            
            # Gestione dinamica dei fallback se le liste admin sono vuote
            opts_models = st.session_state.admin_models if st.session_state.admin_models else ["Nessuna voce"]
            opts_vehicles = st.session_state.admin_vehicles if st.session_state.admin_vehicles else ["Nessuna voce"]
            
            p_data["model_line"] = st.selectbox(
                "Model Line", opts_models,
                index=opts_models.index(p_data["model_line"]) if p_data["model_line"] in opts_models else 0
            )
            p_data["veicolo"] = st.selectbox(
                "Veicolo", opts_vehicles,
                index=opts_vehicles.index(p_data["veicolo"]) if p_data["veicolo"] in opts_vehicles else 0
            )

        with g_col2:
            p_data["hc_totali"] = st.number_input("Numero Interni (HC)", min_value=0.0, value=float(p_data["hc_totali"]), step=1.0)
            p_data["zbb_totali"] = st.number_input("Numero Esterni (ZBB)", min_value=0.0, value=float(p_data["zbb_totali"]), step=1.0)
            
            # Calcolo automatico RIE senza divisioni per zero
            if p_data["zbb_totali"] > 0:
                rie_val = p_data["hc_totali"] / p_data["zbb_totali"]
                st.metric("Rapporto RIE (HC / ZBB)", f"{rie_val:.2f}")
            else:
                rie_val = 0.0
                st.metric("Rapporto RIE (HC / ZBB)", "ZBB nullo (100% HC)")
                
            p_data["css"] = st.number_input("Costo Sessione Sviluppo (CSS) [€]", min_value=0.0, value=float(p_data["css"]), step=100.0)

        with g_col3:
            p_data["costo_orario_hc"] = st.number_input("Costo Orario Interni [€/h]", min_value=0.0, value=float(p_data["costo_orario_hc"]), step=5.0)
            p_data["costo_orario_zbb"] = st.number_input("Costo Orario Esterni [€/h]", min_value=0.0, value=float(p_data["costo_orario_zbb"]), step=5.0)
            
            p_data["data_pm"] = st.date_input("Data Inizio (PM)", p_data["data_pm"])
            p_data["data_sop"] = st.date_input("Data Fine (SOP)", p_data["data_sop"])
            
            giorni = (p_data["data_sop"] - p_data["data_pm"]).days
            settimane_progetto = max(0.0, giorni / 7.0)
            frazione_anno_progetto = max(0.0, giorni / 365.25)
            st.write(f"⏱️ **Durata stimata:** {settimane_progetto:.1f} settimane / {frazione_anno_progetto:.2f} anni")

        st.markdown("---")
        
        # --- PROTEZIONE ANTICRASH MULTISELECT ---
        # Filtriamo le centraline salvate in precedenza per assicurarci che esistano ancora nell'admin
        valid_selected_ecus = [e for e in p_data["selected_ecus"] if e in st.session_state.admin_ecu]
        
        p_data["selected_ecus"] = st.multiselect(
            "Seleziona le Centraline Coinvolte",
            options=st.session_state.admin_ecu,
            default=valid_selected_ecus
        )
        
        p_data["premesse"] = st.text_area("Note e Premesse di Progetto", value=p_data["premesse"])

    # --------------------------------------------------------------------------
    # COMPILAZIONE COSTI DETTAGLIATI PER CENTRALINA
    # --------------------------------------------------------------------------
    st.subheader("🎛️ Costi per Singola Centralina")
    
    elenco_riepiloghi_ecu = []
    
    if not p_data["selected_ecus"]:
        st.info("Scegli almeno una centralina per poterne stimare i costi operativi.")
    else:
        schede_ecu = st.tabs(p_data["selected_ecus"])
        
        for i, nome_ecu in enumerate(p_data["selected_ecus"]):
            with schede_ecu[i]:
                st.markdown(f"### 📑 Modulo di Stima: **{nome_ecu}**")
                
                # Se la centralina non ha un dizionario allocato nello stato, lo creiamo
                if nome_ecu not in p_data["ecu_inputs"]:
                    p_data["ecu_inputs"][nome_ecu] = {
                        "nSS": 0.0, "supplier_cost": 0.0, "pm_h": 0.0, "sw_zdc_h": 0.0,
                        "req_m_h": 0.0, "sw_dev_h": 0.0, "mil_h": 0.0, "bugfix_h": 0.0,
                        "hil_test_ext": 0.0, "hil_setup_ext": 0.0, "parts_ext": 0.0
                    }
                
                inputs = p_data["ecu_inputs"][nome_ecu]
                
                # Input parametri cardine
                c_ec1, c_ec2 = st.columns(2)
                with c_ec1:
                    inputs["nSS"] = st.number_input(f"Settimane Sviluppo/Pista (nSS) - {nome_ecu}", min_value=0.0, value=float(inputs["nSS"]), key=f"nss_{nome_ecu}")
                with c_ec2:
                    inputs["supplier_cost"] = st.number_input(f"Costo Fornitore (Supplier Cost) [€] - {nome_ecu}", min_value=0.0, value=float(inputs["supplier_cost"]), key=f"sup_{nome_ecu}")
                
                # Calcoli automatici basati su nSS
                auto_testing_h = inputs["nSS"] * 40.0
                auto_testing_cost_ext = inputs["nSS"] * p_data["css"]
                
                st.markdown("#### Voci di Costo Specifiche")
                f_col1, f_col2 = st.columns(2)
                
                with f_col1:
                    st.caption("**Impegno in Ore (h):**")
                    inputs["pm_h"] = st.number_input("Project management [h]", min_value=0.0, value=float(inputs["pm_h"]), key=f"pm_{nome_ecu}")
                    inputs["sw_zdc_h"] = st.number_input("SW & ZDC management [h]", min_value=0.0, value=float(inputs["sw_zdc_h"]), key=f"zdc_{nome_ecu}")
                    inputs["req_m_h"] = st.number_input("Requirement management [h]", min_value=0.0, value=float(inputs["req_m_h"]), key=f"req_{nome_ecu}")
                    inputs["sw_dev_h"] = st.number_input("SW development [h]", min_value=0.0, value=float(inputs["sw_dev_h"]), key=f"dev_{nome_ecu}")
                    inputs["mil_h"] = st.number_input("SW testing (MIL) [h]", min_value=0.0, value=float(inputs["mil_h"]), key=f"mil_{nome_ecu}")
                    inputs["bugfix_h"] = st.number_input("Issue analysis & Bugfix [h]", min_value=0.0, value=float(inputs["bugfix_h"]), key=f"bug_{nome_ecu}")
                    st.text_input("Vehicle testing [h] (Autocalcolato: nSS * 40)", value=f"{auto_testing_h} h", disabled=True, key=f"vth_{nome_ecu}")
                    
                with f_col2:
                    st.caption("**Spese Esterne / Materiali (€):**")
                    inputs["hil_test_ext"] = st.number_input("HIL testing [€]", min_value=0.0, value=float(inputs["hil_test_ext"]), key=f"hilt_{nome_ecu}")
                    inputs["hil_setup_ext"] = st.number_input("HIL Set-up (HW) [€]", min_value=0.0, value=float(inputs["hil_setup_ext"]), key=f"hils_{nome_ecu}")
                    st.text_input("Vehicle testing [€] (Autocalcolato: nSS * CSS)", value=f"{auto_testing_cost_ext:,.2f} €", disabled=True, key=f"vte_{nome_ecu}")
                    inputs["parts_ext"] = st.number_input("Parts [€]", min_value=0.0, value=float(inputs["parts_ext"]), key=f"parts_{nome_ecu}")

                # --- LOGICA DEL RAPPORTO RIE & ALLOCAZIONE COSTI ORARI ---
                ore_totali_da_ripartire = (
                    inputs["pm_h"] + inputs["sw_zdc_h"] + inputs["req_m_h"] + 
                    inputs["sw_dev_h"] + inputs["mil_h"] + inputs["bugfix_h"] + auto_testing_h
                )
                
                if p_data["zbb_totali"] == 0 and p_data["hc_totali"] == 0:
                    ore_zbb = 0.0
                    ore_hc = 0.0
                elif p_data["zbb_totali"] == 0:
                    ore_zbb = 0.0
                    ore_hc = ore_totali_da_ripartire
                else:
                    # Formula da requisiti: Ore_ZBB = Ore_totali / (1 + RIE)
                    ore_zbb = ore_totali_da_ripartire / (1 + rie_val)
                    ore_hc = ore_totali_da_ripartire - ore_zbb
                
                costo_monetario_hc = ore_hc * p_data["costo_orario_hc"]
                costo_monetario_zbb = ore_zbb * p_data["costo_orario_zbb"]
                costo_manpower_totale = costo_monetario_hc + costo_monetario_zbb
                
                # Somma Altri Costi Esterni (Ext Cost)
                voci_ext_cost = inputs["hil_test_ext"] + inputs["hil_setup_ext"] + auto_testing_cost_ext + inputs["parts_ext"]
                
                # Costo Totale della Centralina
                budget_totale_ecu = costo_manpower_totale + inputs["supplier_cost"] + voci_ext_cost
                
                # Calcolo FTE Equivalenti all'anno
                quota_ore_anno_progetto = 1600.0 * frazione_anno_progetto
                fte_ecu_anno = ore_totali_da_ripartire / quota_ore_anno_progetto if quota_ore_anno_progetto > 0 else 0.0
                
                # Archiviamo il riassunto locale
                elenco_riepiloghi_ecu.append({
                    "Centralina": nome_ecu,
                    "Ore HC": round(ore_hc, 1),
                    "Ore ZBB": round(ore_zbb, 1),
                    "Costo HC (€)": round(costo_monetario_hc, 2),
                    "Costo ZBB (€)": round(costo_monetario_zbb, 2),
                    "Supplier Cost (€)": round(inputs["supplier_cost"], 2),
                    "Ext Cost (€)": round(voci_ext_cost, 2),
                    "Costo Totale (€)": round(budget_totale_ecu, 2),
                    "FTE/Anno equivalenti": round(fte_ecu_anno, 2)
                })
                
                # --- FINESTRA DI SUM_UP LOCALE ---
                st.markdown("---")
                st.markdown(f"##### 📊 Sintesi Economica ECU: {nome_ecu}")
                sm1, sm2, sm3, sm4 = st.columns(4)
                sm1.metric("Ore Interni (HC)", f"{ore_hc:.1f} h", f"{costo_monetario_hc:,.2f} €", delta_color="off")
                sm2.metric("Ore Esterni (ZBB)", f"{ore_zbb:.1f} h", f"{costo_monetario_zbb:,.2f} €", delta_color="off")
                sm3.metric("Impegno Risorse", f"{fte_ecu_anno:.2f} FTE")
                sm4.metric("Budget Totale ECU", f"{budget_totale_ecu:,.2f} €")

    # --------------------------------------------------------------------------
    # OVERVIEW GLOBALE FINALE
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.header("🏁 Overview Finale del Progetto")
    
    if elenco_riepiloghi_ecu:
        df_completo = pd.DataFrame(elenco_riepiloghi_ecu)
        
        # Aggregazioni globali
        tot_ore_hc = df_completo["Ore HC"].sum()
        tot_ore_zbb = df_completo["Ore ZBB"].sum()
        tot_costo_supplier = df_completo["Supplier Cost (€)"].sum()
        tot_costo_esterni = df_completo["Ext Cost (€)"].sum()
        tot_fte_progetto = df_completo["FTE/Anno equivalenti"].sum()
        budget_complessivo_progetto = df_completo["Costo Totale (€)"].sum()
        
        # Cruscotto KPI
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.container(border=True).metric("Totale Ore Interni (HC)", f"{tot_ore_hc:,.1f} h", f"Equivalenti a {tot_fte_progetto:.2f} FTE Globali")
            st.container(border=True).metric("Totale Costi Fornitori", f"{tot_costo_supplier:,.2f} €")
        with kpi2:
            st.container(border=True).metric("Totale Ore Esterni (ZBB)", f"{tot_ore_zbb:,.1f} h")
            st.container(border=True).metric("Totale Spese Ext / Materiali", f"{tot_costo_esterni:,.2f} €")
        with kpi3:
            st.container(border=True).metric(
                "💰 BUDGET TOTALE PROGETTO", 
                f"{budget_complessivo_progetto:,.2f} €",
                help="Include tutte le voci di costo orario, materiali e fornitori di tutte le ECU selezionate."
            )
            
        # Tabella di visualizzazione strutturata delle ECU affiancate
        st.markdown("#### Tabella Comparativa di Dettaglio")
        st.dataframe(df_completo, hide_index=True, use_container_width=True)
    else:
        st.warning("Nessuna centralina inserita a budget o nessun dato disponibile nell'Overview.")
