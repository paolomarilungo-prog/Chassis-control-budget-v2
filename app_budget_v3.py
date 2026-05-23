import streamlit as st
import json
import os
import pandas as pd
import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Automotive ECU Budgeting Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "automotive_budget_db.json"

# --- INIZIALIZZAZIONE E PERSISTENZA DATI (JSON) ---
def load_database():
    default_db = {
        "admin": {
            "guidelines": "Linee guida generali per la stima dei budget ECU. Assicurarsi di verificare le tariffe orarie correnti.",
            "ecu_portfolio": ["Kangaroo", "Kangaroo Lite", "Chassis_Master", "Gateway_Gateway"],
            "model_lines": ["Model Line Alpha", "Model Line Beta"],
            "vehicles": {
                "Model Line Alpha": ["V12-Hypercar", "V10-Supersport"],
                "Model Line Beta": ["UV-Luxury", "UV-Sport"]
            }
        },
        "repository": {}
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_db
    return default_db

def save_database(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Carica i dati persistenti all'avvio
if "db" not in st.session_state:
    st.session_state.db = load_database()

# Inizializzazione dello stato di lavoro del budget corrente per permettere modifiche/caricamenti
if "current_budget" not in st.session_state:
    st.session_state.current_budget = {}

db = st.session_state.db

# --- FUNZIONI DI SUPPORTO AI CALCOLI ---
def calcola_metrice_progetto(pm_date, sop_date, hc, zbb, hr_hc, hr_zbb, css, n_ss, selected_ecus, ecu_data):
    if not pm_date or not sop_date:
        return {}
    
    # Calcolo durata del progetto
    giorni = (sop_date - pm_date).days
    settimane_totali = giorni / 7.0
    anni_totali = giorni / 365.25 if giorni > 0 else 0
    
    # Evita divisioni per zero nel rapporto RIE e pesi
    tot_risorse = hc + zbb
    rie = hc / zbb if zbb > 0 else 0.0
    f_hc = hc / tot_risorse if tot_risorse > 0 else 0.0
    f_zbb = zbb / tot_risorse if tot_risorse > 0 else 0.0
    
    # Calcolo valori fissi dipendenti da nSS e CSS
    veh_testing_h = n_ss * 40
    veh_testing_ext = n_ss * css
    
    voci_ore = [
        "Project management", "SW & ZDC management", "Requirement management", 
        "SW development", "SW testing (MIL)", "Issue analysis & Bugfix", "Vehicle testing (h)"
    ]
    voci_costi_est = [
        "HIL testing", "HIL Set-up (HW)", "Vehicle testing (ext cost)", "Parts"
    ]
    
    ecu_summaries = {}
    tot_ore_progetto = 0.0
    tot_hc_cost = 0.0
    tot_zbb_cost = 0.0
    tot_supplier_cost = 0.0
    tot_ext_cost = 0.0
    
    for ecu in selected_ecus:
        inputs = ecu_data.get(ecu, {})
        
        # Estrazione e calcolo ore totali per singola ECU
        ore_tot_ecu = 0.0
        costo_ore_hc_ecu = 0.0
        costo_ore_zbb_ecu = 0.0
        
        for voce in voci_ore:
            if voce == "Vehicle testing (h)":
                h_voce = veh_testing_h
            else:
                h_voce = inputs.get(f"{voce}_h", 0.0)
                
            ore_tot_ecu += h_voce
            
            # Ripartizione proporzionale
            h_hc = h_voce * f_hc
            h_zbb = h_voce * f_zbb
            
            costo_ore_hc_ecu += h_hc * hr_hc
            costo_ore_zbb_ecu += h_zbb * hr_zbb
            
        # Estrazione costi diretti ed esterni
        supplier_cost = inputs.get("ECU supplier cost", 0.0)
        
        ext_cost_ecu = 0.0
        for voce in voci_costi_est:
            if voce == "Vehicle testing (ext cost)":
                ext_cost_ecu += veh_testing_ext
            else:
                ext_cost_ecu += inputs.get(f"{voce}_ext", 0.0)
                
        # Totale complessivo ECU
        tot_ecu = costo_ore_hc_ecu + costo_ore_zbb_ecu + supplier_cost + ext_cost_ecu
        
        ecu_summaries[ecu] = {
            "hc_hours": ore_tot_ecu * f_hc,
            "zbb_hours": ore_tot_ecu * f_zbb,
            "total_hours": ore_tot_ecu,
            "hc_cost": costo_ore_hc_ecu,
            "zbb_cost": costo_ore_zbb_ecu,
            "supplier_cost": supplier_cost,
            "ext_cost": ext_cost_ecu,
            "total_cost": tot_ecu
        }
        
        # Accumulatori globali di progetto
        tot_ore_progetto += ore_tot_ecu
        tot_hc_cost += costo_ore_hc_ecu
        tot_zbb_cost += costo_ore_zbb_ecu
        tot_supplier_cost += supplier_cost
        tot_ext_cost += ext_cost_ecu

    # Calcolo FTE Annui complessivi sul progetto
    # 1 FTE = 40 ore/settimana. Ore totali lavorabili da 1 FTE nel ciclo di vita del progetto = settimane_totali * 40
    ore_lavorabili_un_fte = settimane_totali * 40 if settimane_totali > 0 else 1
    fte_annui = tot_ore_progetto / ore_lavorabili_un_fte if settimane_totali > 0 else 0.0

    return {
        "settimane_totali": settimane_totali,
        "anni_totali": anni_totali,
        "rie": rie,
        "f_hc": f_hc,
        "f_zbb": f_zbb,
        "veh_testing_h": veh_testing_h,
        "veh_testing_ext": veh_testing_ext,
        "ecu_summaries": ecu_summaries,
        "global": {
            "total_hours": tot_ore_progetto,
            "hc_hours": tot_ore_progetto * f_hc,
            "zbb_hours": tot_ore_progetto * f_zbb,
            "fte_annui": fte_annui,
            "hc_cost": tot_hc_cost,
            "zbb_cost": tot_zbb_cost,
            "supplier_cost": tot_supplier_cost,
            "ext_cost": tot_ext_cost,
            "grand_total": tot_hc_cost + tot_zbb_cost + tot_supplier_cost + tot_ext_cost
        }
    }

# --- INTERFACCIA UTENTE (TABS) ---
st.title("📊 Automotive ECU Budgeting & Costing Platform")
st.markdown("Applicazione ingegneristica per la pianificazione finanziaria e la ripartizione delle risorse del portfolio ECU.")

tab1, tab2, tab3 = st.tabs(["⚙️ Admin Panel", "📊 Nuovo Budget / Change Request", "🗄️ Repository & Versioning"])

# ==========================================
# 1. SEZIONE ADMIN (Tab 1)
# ==========================================
with tab1:
    st.header("Configurazione Anagrafiche e Parametri di Portfolio")
    
    # Linee Guida Informativie
    st.subheader("Note e Linee Guida di Budgeting")
    guidelines_input = st.text_area("Testo informativo globale:", value=db["admin"]["guidelines"], height=100)
    if guidelines_input != db["admin"]["guidelines"]:
        db["admin"]["guidelines"] = guidelines_input
        save_database(db)
        st.success("Linee guida aggiornate con successo.")
        
    st.write("---")
    
    col_adm1, col_adm2 = st.columns(2)
    
    with col_adm1:
        # Gestione Portfolio ECU
        st.subheader("Portfolio Centraline (ECU)")
        with st.form("form_ecu", clear_on_submit=True):
            nuova_ecu = st.text_input("Inserisci nome nuova ECU:")
            submit_ecu = st.form_submit_button("Aggiungi ECU al Portfolio")
            if submit_ecu and nuova_ecu:
                nuova_ecu_clean = nuova_ecu.strip()
                if nueva_ecu_clean not in db["admin"]["ecu_portfolio"]:
                    db["admin"]["ecu_portfolio"].append(nueva_ecu_clean)
                    save_database(db)
                    st.success(f"ECU '{nueva_ecu_clean}' aggiunta.")
                    st.rerun()
                else:
                    st.warning("ECU già presente nel portfolio.")
                    
        # Visualizzazione e rimozione ECU
        df_ecu = pd.DataFrame(db["admin"]["ecu_portfolio"], columns=["Nome ECU"])
        st.dataframe(df_ecu, use_container_width=True)
        ecu_da_eliminare = st.selectbox("Seleziona ECU da rimuovere:", [""] + db["admin"]["ecu_portfolio"])
        if st.button("Elimina ECU selezionata") and ecu_da_eliminare:
            db["admin"]["ecu_portfolio"].remove(ecu_da_eliminare)
            save_database(db)
            st.success(f"ECU '{ecu_da_eliminare}' rimossa.")
            st.rerun()

    with col_adm2:
        # Gestione Model Line e Veicoli
        st.subheader("Model Line & Veicoli Associati")
        
        # Aggiunta Model Line
        with st.form("form_ml", clear_on_submit=True):
            nuova_ml = st.text_input("Inserisci nuova Model Line:")
            submit_ml = st.form_submit_button("Aggiungi Model Line")
            if submit_ml and nuova_ml:
                nuova_ml_clean = nuova_ml.strip()
                if nuova_ml_clean not in db["admin"]["model_lines"]:
                    db["admin"]["model_lines"].append(nuova_ml_clean)
                    db["admin"]["vehicles"][nuova_ml_clean] = []
                    save_database(db)
                    st.success(f"Model Line '{nuova_ml_clean}' creata.")
                    st.rerun()
                    
        # Aggiunta Veicolo legato a Model Line
        with st.form("form_vehicle", clear_on_submit=True):
            ml_selezionata = st.selectbox("Seleziona Model Line per il veicolo:", db["admin"]["model_lines"])
            nuovo_veicolo = st.text_input("Inserisci nome nuovo Veicolo:")
            submit_veh = st.form_submit_button("Associa Veicolo")
            if submit_veh and nuovo_veicolo and ml_selezionata:
                nv_clean = nuovo_veicolo.strip()
                if nv_clean not in db["admin"]["vehicles"].get(ml_selezionata, []):
                    if ml_selezionata not in db["admin"]["vehicles"]:
                        db["admin"]["vehicles"][ml_selezionata] = []
                    db["admin"]["vehicles"][ml_selezionata].append(nv_clean)
                    save_database(db)
                    st.success(f"Veicolo '{nv_clean}' associato a '{ml_selezionata}'.")
                    st.rerun()
                else:
                    st.warning("Questo veicolo esiste già nella Model Line selezionata.")

        # Tabella riassuntiva Anagrafica Veicoli
        records_veicoli = []
        for ml, veh_list in db["admin"]["vehicles"].items():
            for v in veh_list:
                records_veicoli.append({"Model Line": ml, "Veicolo": v})
        if records_veicoli:
            st.dataframe(pd.DataFrame(records_veicoli), use_container_width=True)


# ==========================================
# 2. SINGOLO PROGETTO / COSTIFICAZIONE (Tab 2)
# ==========================================
with tab2:
    st.header("Configuratore Economico del Progetto")
    st.info(f"💡 **Linee Guida Attuali:** {db['admin']['guidelines']}")
    
    # Controllo se è presente un budget precaricato dal repository
    preload = st.session_state.current_budget
    
    st.subheader("1. Master Data Progetto")
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        tipo_richiesta = st.selectbox(
            "Tipo di Budget Richiesto:", 
            ["Nuovo Veicolo", "Change Request"],
            index=0 if preload.get("tipo_richiesta") == "Nuovo Veicolo" else (1 if preload.get("tipo_richiesta") == "Change Request" else 0)
        )
        titolo_cr = ""
        if tipo_richiesta == "Change Request":
            titolo_cr = st.text_input("Titolo della Change Request (Obbligatorio):", value=preload.get("titolo_cr", ""))
            
    with col_m2:
        ml_progetto = st.selectbox(
            "Seleziona Model Line Progetto:", 
            db["admin"]["model_lines"],
            index=db["admin"]["model_lines"].index(preload["ml_progetto"]) if preload.get("ml_progetto") in db["admin"]["model_lines"] else 0
        )
        
        # Filtro dinamico veicoli basato sulla model line selezionata
        veicoli_disponibili = db["admin"]["vehicles"].get(ml_progetto, [])
        veicolo_progetto = st.selectbox(
            "Seleziona Veicolo Coinvolto:", 
            veicoli_disponibili,
            index=veicoli_disponibili.index(preload["veicolo_progetto"]) if preload.get("veicolo_progetto") in veicoli_disponibili else 0
        )
        
    with col_m3:
        # Date di Progetto e calcolo automatico tempistiche
        pm_init = preload.get("milestone_pm", datetime.date.today())
        if isinstance(pm_init, str): pm_init = datetime.date.fromisoformat(pm_init)
        sop_init = preload.get("milestone_sop", datetime.date.today() + datetime.timedelta(days=365))
        if isinstance(sop_init, str): sop_init = datetime.date.fromisoformat(sop_init)
            
        milestone_pm = st.date_input("Inizio Progetto (Milestone PM):", value=pm_init)
        milestone_sop = st.date_input("Fine Progetto (Milestone SOP):", value=sop_init)
        
        # Calcolo preventivo al volo della durata
        giorni_calc = (milestone_sop - milestone_pm).days
        settimane_calc = giorni_calc / 7.0
        st.metric(label="Durata Stimata Progetto", value=f"{settimane_calc:.1f} Settimane", delta=f"{giorni_calc/365.25:.2f} Anni")

    premesse_progetto = st.text_area("Premesse e Vincoli di Progetto:", value=preload.get("premesse", ""))

    st.write("---")
    st.subheader("2. Parametri di Organizzazione e Risorse (Globali di Progetto)")
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    
    with col_r1:
        hc_input = st.number_input("Numero di risorse Interne (HC):", min_value=0, value=preload.get("hc", 5), step=1)
        zbb_input = st.number_input("Numero di risorse Esterne (ZBB):", min_value=0, value=preload.get("zbb", 5), step=1)
        
        # Calcolo dinamico RIE visibile
        rie_visual = hc_input / zbb_input if zbb_input > 0 else 0.0
        st.markdown(f"**Rapporto RIE (HC/ZBB):** `{rie_visual:.3f}`")
        
    with col_r2:
        hrHC_input = st.number_input("Costo orario Interni hrHC (€/h):", min_value=0.0, value=preload.get("hrHC", 60.0), step=5.0)
        hrZBB_input = st.number_input("Costo orario Esterni hrZBB (€/h):", min_value=0.0, value=preload.get("hrZBB", 45.0), step=5.0)
        
    with col_r3:
        css_input = st.number_input("Costo Sessione Sviluppo CSS (€):", min_value=0.0, value=preload.get("css", 1200.0), step=100.0)
        
    with col_r4:
        nSS_input = st.number_input("Settimane Sviluppo e Pista (nSS):", min_value=0, value=preload.get("nSS", 10), step=1)

    # Selezione multipla delle ECU coinvolte
    st.write("---")
    st.subheader("3. Selezione ed Estimating delle Centraline Coinvolte")
    
    selected_ecus = st.multiselect(
        "Seleziona le centraline del portfolio associate a questo budget:",
        db["admin"]["ecu_portfolio"],
        default=preload.get("selected_ecus", [])
    )
    
    # Dizionario in cui salvare gli input inseriti per ciascuna ECU in interfaccia
    ecu_inputs_state = {}
    
    voci_ore_input = [
        "Project management", "SW & ZDC management", "Requirement management", 
        "SW development", "SW testing (MIL)", "Issue analysis & Bugfix"
    ]
    voci_costi_est_input = [
        "HIL testing", "HIL Set-up (HW)", "Parts"
    ]

    # Generazione dei blocchi di input dinamici per ciascuna ECU
    if selected_ecus:
        for ecu in selected_ecus:
            # Recupera eventuali vecchi dati per la ECU se precaricati o già modificati
            old_ecu_data = preload.get("ecu_data", {}).get(ecu, {})
            
            with st.expander(f"⚙️ Stima Costi Sviluppo per Centralina: {ecu}", expanded=True):
                st.markdown(f"##### Inserimento Voci di Costo per **{ecu}**")
                
                c_ecu1, c_ecu2, c_ecu3 = st.columns(3)
                
                ecu_inputs_state[ecu] = {}
                
                with c_ecu1:
                    st.markdown("**Costi Fornitore & Ore Ingegneria**")
                    ecu_inputs_state[ecu]["ECU supplier cost"] = st.number_input(
                        f"ECU supplier cost (€) - {ecu}", min_value=0.0, 
                        value=float(old_ecu_data.get("ECU supplier cost", 0.0)), key=f"supp_{ecu}", step=500.0
                    )
                    
                    for voce in voci_ore_input[:3]:
                        ecu_inputs_state[ecu][f"{voce}_h"] = st.number_input(
                            f"{voce} (h) - {ecu}", min_value=0.0, 
                            value=float(old_ecu_data.get(f"{voce}_h", 0.0)), key=f"h_{voce}_{ecu}", step=10.0
                        )
                        
                with c_ecu2:
                    st.markdown("**Altre Ore Ingegneria**")
                    for voce in voci_ore_input[3:]:
                        ecu_inputs_state[ecu][f"{voce}_h"] = st.number_input(
                            f"{voce} (h) - {ecu}", min_value=0.0, 
                            value=float(old_ecu_data.get(f"{voce}_h", 0.0)), key=f"h_{voce}_{ecu}", step=10.0
                        )
                    
                    # Campi calcolati in automatico bloccati (sola visualizzazione informativa all'interno del form)
                    calc_veh_h = nSS_input * 40
                    st.text_input(f"Vehicle testing (h) [nSS * 40] - {ecu}", value=str(calc_veh_h), disabled=True, key=f"v_h_dis_{ecu}")
                    
                with c_ecu3:
                    st.markdown("**Spese Esterne / Hardware**")
                    for voce in voci_costi_est_input:
                        ecu_inputs_state[ecu][f"{voce}_ext"] = st.number_input(
                            f"{voce} (€ ext cost) - {ecu}", min_value=0.0, 
                            value=float(old_ecu_data.get(f"{voce}_ext", 0.0)), key=f"ext_{voce}_{ecu}", step=500.0
                        )
                    
                    calc_veh_ext = nSS_input * css_input
                    st.text_input(f"Vehicle testing (ext cost) [nSS * CSS] - {ecu}", value=f"{calc_veh_ext:.2f} €", disabled=True, key=f"v_ext_dis_{ecu}")

                # Esecuzione calcoli intermedi in tempo reale sulla singola ECU per la sezione SUM_UP
                res_calc = calcola_metrice_progetto(
                    milestone_pm, milestone_sop, hc_input, zbb_input, hrHC_input, hrZBB_input, 
                    css_input, nSS_input, [ecu], {ecu: ecu_inputs_state[ecu]}
                )
                
                # Visualizzazione della sezione SUM_UP specifica della ECU in fondo al suo expander
                if ecu in res_calc.get("ecu_summaries", {}):
                    s_ecu = res_calc["ecu_summaries"][ecu]
                    st.markdown("---")
                    st.markdown(f"📋 **SUM_UP Singola Centralina ({ecu})**")
                    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
                    col_s1.metric("Ore Totali HC", f"{s_ecu['hc_hours']:.1f} h")
                    col_s2.metric("Ore Totali ZBB", f"{s_ecu['zbb_hours']:.1f} h")
                    col_s3.metric("Costo Supplier", f"{s_ecu['supplier_cost']:,} €")
                    col_s4.metric("Somma Ext Cost", f"{s_ecu['ext_cost']:,} €")
                    col_s5.metric("Totale Complessivo ECU", f"{s_ecu['total_cost']:,} €")
    else:
        st.warning("Selezionare almeno una centralina per procedere con la costificazione delle voci.")

    # Esecuzione dei calcoli macro su tutto il progetto
    risultati_globali = calcola_metrice_progetto(
        milestone_pm, milestone_sop, hc_input, zbb_input, hrHC_input, hrZBB_input, 
        css_input, nSS_input, selected_ecus, ecu_inputs_state
    )

    # ==========================================
    # 3. OVERVIEW FINALE & SALVATAGGIO (Tab 2)
    # ==========================================
    if selected_ecus and risultati_globali:
        st.write("---")
        st.header("📈 Overview Finale del Progetto")
        
        # 3.1 Tabella Sintesi Ore e FTE
        st.subheader("Sintesi Risorse ed Equivalenti a Tempo Pieno (FTE)")
        g_metrics = risultati_globali["global"]
        
        df_fte = pd.DataFrame([{
            "Ore Totali Progetto": f"{g_metrics['total_hours']:.1f} h",
            "Ore HC (Interne)": f"{g_metrics['hc_hours']:.1f} h",
            "Ore ZBB (Esterne)": f"{g_metrics['zbb_hours']:.1f} h",
            "Rapporto RIE": f"{risultati_globali['rie']:.3f}",
            "FTE Annui Totali": f"{g_metrics['fte_annui']:.2f} FTE/anno"
        }])
        st.table(df_fte)
        
        # 3.2 SUM_UP Totale Progetto
        st.subheader("SUM_UP Finanziario di Progetto")
        col_g1, col_g2, col_g3, col_g4, col_g5 = st.columns(5)
        col_g1.metric("Totale Interni (HC)", f"{g_metrics['hc_cost']:,} €")
        col_g2.metric("Totale Esterni (ZBB)", f"{g_metrics['zbb_cost']:,} €")
        col_g3.metric("Totale Fornitore (Supplier)", f"{g_metrics['supplier_cost']:,} €")
        col_g4.metric("Totale Spese Esterne (Ext Cost)", f"{g_metrics['ext_cost']:,} €")
        col_g5.metric("GRAND TOTAL PROGETTO", f"{g_metrics['grand_total']:,} €")
        
        # 3.3 Dettaglio ECU Comparativo
        st.subheader("Dettaglio Analitico per Singola ECU")
        records_confronto = []
        for ecu, comp_data in risultati_globali["ecu_summaries"].items():
            records_confronto.append({
                "Centralina": ecu,
                "Ore Totali (h)": round(comp_data["total_hours"], 1),
                "Costo HC (€)": round(comp_data["hc_cost"], 2),
                "Costo ZBB (€)": round(comp_data["zbb_cost"], 2),
                "Costo Supplier (€)": round(comp_data["supplier_cost"], 2),
                "Ext Cost (€)": round(comp_data["ext_cost"], 2),
                "Totale ECU (€)": round(comp_data["total_cost"], 2)
            })
        df_confronto = pd.DataFrame(records_confronto)
        st.dataframe(df_confronto, use_container_width=True)

        # Logica di salvataggio del preventivo
        st.write("---")
        st.subheader("Salvataggio e Storicizzazione")
        
        # Definizione nome obbligatorio da requisiti
        if tipo_richiesta == "Nuovo Veicolo":
            nome_base_progetto = veicolo_progetto if veicolo_progetto else "Veicolo_Non_Definito"
        else:
            nome_base_progetto = f"{veicolo_progetto}_{titolo_cr}".strip() if veicolo_progetto and titolo_cr else ""
            
        if not nome_base_progetto or nome_base_progetto.endswith("_"):
            st.error("⚠️ Impossibile salvare. Verificare che il nome del veicolo o il titolo della CR siano compilati.")
        else:
            st.write(f"Il budget verrà archiviato nel repository con il seguente identificativo: **{nome_base_progetto}**")
            
            if st.button("💾 Salva Costificazione", type="primary"):
                # Struttura del documento di budget corrente da archiviare
                budget_payload = {
                    "tipo_richiesta": tipo_richiesta,
                    "titolo_cr": titolo_cr,
                    "ml_progetto": ml_progetto,
                    "veicolo_progetto": veicolo_progetto,
                    "milestone_pm": milestone_pm.isoformat(),
                    "milestone_sop": milestone_sop.isoformat(),
                    "premesse": premesse_progetto,
                    "hc": hc_input,
                    "zbb": zbb_input,
                    "hrHC": hrHC_input,
                    "hrZBB": hrZBB_input,
                    "css": css_input,
                    "nSS": nSS_input,
                    "selected_ecus": selected_ecus,
                    "ecu_data": ecu_inputs_state,
                    "calculations": {
                        "global": g_metrics,
                        "duration_weeks": risultati_globali["settimane_totali"]
                    },
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Gestione automatica del Versionamento continuo nel database JSON
                if nome_base_progetto not in db["repository"]:
                    # Nuova entry: prima versione v1
                    budget_payload["version"] = 1
                    db["repository"][nome_base_progetto] = [budget_payload]
                    st.success(f"Budget '{nome_base_progetto}' salvato come Nuova Costificazione (Versione v1)!")
                else:
                    # Record già presente: recupera ultima versione e incrementa per creare lo storico
                    storico_versioni = db["repository"][nome_base_progetto]
                    prossima_versione = len(storico_versioni) + 1
                    budget_payload["version"] = prossima_versione
                    db["repository"][nome_base_progetto].append(budget_payload)
                    st.success(f"Budget '{nome_base_progetto}' aggiornato correttamente! Archiviata Versione v{prossima_versione}.")
                
                save_database(db)
                # Resetta lo stato temporaneo dopo il salvataggio
                st.session_state.current_budget = {}
                st.rerun()


# ==========================================
# 4. REPOSITORY & VERSIONING (Tab 3)
# ==========================================
with tab3:
    st.header("🗄️ Repository Storico delle Costificazioni")
    
    if not db["repository"]:
        st.info("Nessun budget salvato nel database locale. Completa una simulazione nel Tab 2 e salvala.")
    else:
        st.subheader("Seleziona una Costificazione da esaminare o modificare")
        
        nomi_progetti_disponibili = list(db["repository"].keys())
        progetto_scelto = st.selectbox("Seleziona Progetto:", nomi_progetti_disponibili)
        
        if data_storico := db["repository"].get(progetto_scelto):
            # Selezione della versione specifica presente nello storico di quel nome progetto
            versioni_disponibili = [f"Versione v{b['version']} ({b['timestamp']})" for b in data_storico]
            versione_scelta_str = st.selectbox("Seleziona Versione da caricare:", versioni_disponibili)
            
            # Estrazione indice numerico della versione selezionata
            idx_versione = versioni_disponibili.index(versione_scelta_str)
            budget_selezionato = data_storico[idx_versione]
            
            # --- MOSTRA OVERVIEW STATICA DELLA VERSIONE SELEZIONATA ---
            st.markdown(f"### 📊 Overview di Riferimento: {progetto_scelto} (v{budget_selezionato['version']})")
            
            c_rep1, c_rep2, c_rep3 = st.columns(3)
            with c_rep1:
                st.markdown(f"**Tipo:** {budget_selezionato['tipo_richiesta']}")
                st.markdown(f"**Model Line:** {budget_selezionato['ml_progetto']}")
                st.markdown(f"**Veicolo:** {budget_selezionato['veicolo_progetto']}")
            with c_rep2:
                st.markdown(f"**Milestone PM:** {budget_selezionato['milestone_pm']}")
                st.markdown(f"**Milestone SOP:** {budget_selezionato['milestone_sop']}")
                st.markdown(f"**Settimane di Sviluppo (nSS):** {budget_selezionato['nSS']}")
            with c_rep3:
                calc_saved = budget_selezionato["calculations"]["global"]
                st.metric("Costo Totale Archiviato", f"{calc_saved['grand_total']:,} €")
                st.metric("FTE Annui Allocati", f"{calc_saved['fte_annui']:.2f} FTE")
            
            st.markdown(f"**Premesse d'origine:** *{budget_selezionato['premesse']}*")
            
            # Bottone di azione per caricare i dati nel workspace editabile del Tab 2
            st.write("---")
            if st.button("🔄 Carica questo Budget nel Tab 2 per Modificarlo / Creare Nuova Versione"):
                st.session_state.current_budget = budget_selezionato
                st.success("Dati caricati nell'area di lavoro del Tab 2! Spostati nel secondo tab per modificarli e salvare la nuova versione.")
                st.rerun()
