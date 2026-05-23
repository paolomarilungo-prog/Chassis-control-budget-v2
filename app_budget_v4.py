import streamlit as st
import json
import os
import pandas as pd
import datetime

# --- INIZIALIZZAZIONE DELLA PAGINA ---
st.set_page_config(
    page_title="Automotive ECU Budgeting Tool",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "ecu_budget_db.json"

# --- STRUTTURA DATI DI DEFAULT (PERSISTENZA) ---
def load_db():
    default_structure = {
        "admin": {
            "guidelines": "Inserire qui le note e le linee guida globali per la costificazione del budget...",
            "ecu_portfolio": ["Kangaroo", "Kangaroo Lite", "Chassis_Master", "Gateway_ECU"],
            "model_lines": ["Model Line Alpha", "Model Line Beta"],
            "vehicles": {
                "Model Line Alpha": ["V12-Hypercar", "V10-Supersport"],
                "Model Line Beta": ["SUV-Luxury", "SUV-Sport"]
            }
        },
        "repository": {}
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_structure
    return default_structure

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Caricamento del database globale all'interno del session_state
if "db" not in st.session_state:
    st.session_state.db = load_db()

# Gestione del Workspace temporaneo per modifiche/caricamenti senza reset di stato
if "workspace" not in st.session_state:
    st.session_state.workspace = {}

db = st.session_state.db

# --- MOTORE DI CALCOLO INTERNO (INGEGNERIA DEL BUDGET) ---
def calcola_budget_progetto(pm_date, sop_date, hc, zbb, hr_hc, hr_zbb, css, selected_ecus, ecu_inputs):
    if not pm_date or not sop_date or (sop_date <= pm_date):
        return None
    
    # Calcolo tempi globali progetto
    giorni_totali = (sop_date - pm_date).days
    settimane_progetto = giorni_totali / 7.0
    
    tot_risorse = hc + zbb
    f_hc = hc / tot_risorse if tot_risorse > 0 else 0.0
    f_zbb = zbb / tot_risorse if tot_risorse > 0 else 0.0
    rie = hc / zbb if zbb > 0 else 0.0
    
    voci_ore_fisse = [
        "Project management", "SW & ZDC management", "Requirement management", 
        "SW development", "SW testing (MIL)", "Issue analysis & Bugfix"
    ]
    
    ecu_details = {}
    total_hours_project = 0.0
    total_hc_hours_project = 0.0
    total_zbb_hours_project = 0.0
    
    total_hc_cost_project = 0.0
    total_zbb_cost_project = 0.0
    total_supplier_cost_project = 0.0
    total_ext_cost_project = 0.0
    
    for ecu in selected_ecus:
        inputs = ecu_inputs.get(ecu, {})
        n_ss = inputs.get("nSS", 0.0)
        
        # Calcolo voci condizionate da nSS locale alla ECU
        veh_testing_h = n_ss * 40.0
        veh_testing_ext = n_ss * css
        
        # Accumulo ore totali per la ECU
        ore_totali_ecu = veh_testing_h
        for voce in voci_ore_fisse:
            ore_totali_ecu += inputs.get(f"{voce}_h", 0.0)
            
        # Ripartizione proporzionale RIE delle ore della singola ECU
        hc_hours_ecu = ore_totali_ecu * f_hc
        zbb_hours_ecu = ore_totali_ecu * f_zbb
        
        # Calcolo costi economici basati sulle tariffe orarie
        hc_cost_ecu = hc_hours_ecu * hr_hc
        zbb_cost_ecu = zbb_hours_ecu * hr_zbb
        
        # Gestione voci di costo fisso ed esterno
        supplier_cost_ecu = inputs.get("ecu_supplier_cost", 0.0)
        ext_cost_ecu = (
            inputs.get("hil_testing_ext", 0.0) +
            inputs.get("hil_setup_ext", 0.0) +
            inputs.get("parts_ext", 0.0) +
            veh_testing_ext
        )
        
        total_cost_ecu = hc_cost_ecu + zbb_cost_ecu + supplier_cost_ecu + ext_cost_ecu
        
        ecu_details[ecu] = {
            "nSS": n_ss,
            "total_hours": ore_totali_ecu,
            "hc_hours": hc_hours_ecu,
            "zbb_hours": zbb_hours_ecu,
            "hc_cost": hc_cost_ecu,
            "zbb_cost": zbb_cost_ecu,
            "supplier_cost": supplier_cost_ecu,
            "ext_cost": ext_cost_ecu,
            "total_cost": total_cost_ecu,
            "breakdown_inputs": inputs # Salviamo lo stato nativo degli input per reload futuri
        }
        
        # Incremento accumulatori globali di progetto
        total_hours_project += ore_totali_ecu
        total_hc_hours_project += hc_hours_ecu
        total_zbb_hours_project += zbb_hours_ecu
        total_hc_cost_project += hc_cost_ecu
        total_zbb_cost_project += zbb_cost_ecu
        total_supplier_cost_project += supplier_cost_ecu
        total_ext_cost_project += ext_cost_ecu
        
    # Calcolo FTE Annui complessivi (1 FTE = 40 ore/settimana sull'arco temporale del progetto)
    ore_teoriche_un_fte = settimane_progetto * 40.0
    fte_annui = total_hours_project / ore_teoriche_un_fte if ore_teoriche_un_fte > 0 else 0.0
    
    return {
        "settimane_progetto": settimane_progetto,
        "rie": rie,
        "ecu_details": ecu_details,
        "global": {
            "total_hours": total_hours_project,
            "hc_hours": total_hc_hours_project,
            "zbb_hours": total_zbb_hours_project,
            "fte_annui": fte_annui,
            "hc_cost": total_hc_cost_project,
            "zbb_cost": total_zbb_cost_project,
            "supplier_cost": total_supplier_cost_project,
            "ext_cost": total_ext_cost_project,
            "grand_total": total_hc_cost_project + total_zbb_cost_project + total_supplier_cost_project + total_ext_cost_project
        }
    }

# --- INTERFACCIA UTENTE PRINCIPALE ---
st.title("Automotive ECU Budgeting & Costing Platform")
st.markdown("Piattaforma ingegneristica per il calcolo dei costi di sviluppo e la ripartizione delle risorse $HC/ZBB$.")

tab1, tab2, tab3 = st.tabs(["⚙️ Admin Panel", "📊 Nuovo Budget / Change Request", "🗄️ Repository & Versioning"])

# ==========================================
# 1. SEZIONE ADMIN (TAB 1)
# ==========================================
with tab1:
    st.header("Anagrafiche Portfolio ed Informative di Sistema")
    
    # Gestione delle Note Linee Guida
    st.subheader("Note e Linee Guida Generali")
    guidelines_input = st.text_area("Modifica le note informative visualizzate nel configuratore:", value=db["admin"]["guidelines"], height=100)
    if guidelines_input != db["admin"]["guidelines"]:
        db["admin"]["guidelines"] = guidelines_input
        save_db(db)
        st.success("Linee guida salvate con successo.")
        
    st.write("---")
    col_a1, col_a2 = st.columns(2)
    
    with col_a1:
        st.subheader("Portfolio Centraline (ECU)")
        with st.form("add_ecu_form", clear_on_submit=True):
            nuova_ecu = st.text_input("Nome Nuova Centralina da inserire:")
            if st.form_submit_button("Inserisci ECU nel Portfolio") and nuova_ecu:
                clean_name = nuova_ecu.strip()
                if clean_name not in db["admin"]["ecu_portfolio"]:
                    db["admin"]["ecu_portfolio"].append(clean_name)
                    save_db(db)
                    st.success(f"Centralina {clean_name} inserita.")
                    st.rerun()
                    
        df_ecu = pd.DataFrame(db["admin"]["ecu_portfolio"], columns=["Centraline Disponibili"])
        st.dataframe(df_ecu, use_container_width=True, height=200)
        
        ecu_da_eliminare = st.selectbox("Seleziona una ECU da rimuovere:", [""] + db["admin"]["ecu_portfolio"])
        if st.button("Rimuovi ECU dal Portfolio") and ecu_da_eliminare:
            db["admin"]["ecu_portfolio"].remove(ecu_da_eliminare)
            save_db(db)
            st.success(f"Rimossa ECU: {ecu_da_eliminare}")
            st.rerun()

    with col_a2:
        st.subheader("Model Line & Gestione Veicoli")
        with st.form("add_ml_form", clear_on_submit=True):
            nuova_ml = st.text_input("Inserisci Nuova Model Line:")
            if st.form_submit_button("Crea Model Line") and nuova_ml:
                clean_ml = nuova_ml.strip()
                if clean_ml not in db["admin"]["model_lines"]:
                    db["admin"]["model_lines"].append(clean_ml)
                    db["admin"]["vehicles"][clean_ml] = []
                    save_db(db)
                    st.success(f"Model Line '{clean_ml}' creata.")
                    st.rerun()
                    
        st.write("---")
        with st.form("add_veh_form", clear_on_submit=True):
            ml_target = st.selectbox("Associa al modello (Model Line):", db["admin"]["model_lines"])
            nuovo_veh = st.text_input("Nome Nuovo Veicolo:")
            if st.form_submit_button("Salva Nuovo Veicolo") and nuovo_veh and ml_target:
                clean_veh = nuovo_veh.strip()
                if clean_veh not in db["admin"]["vehicles"].get(ml_target, []):
                    db["admin"]["vehicles"][ml_target].append(clean_veh)
                    save_db(db)
                    st.success(f"Veicolo '{clean_veh}' associato a '{ml_target}'.")
                    st.rerun()
                    
        # Tabella di visualizzazione relazioni Model Line / Veicoli
        lista_relazioni = []
        for ml, veicoli in db["admin"]["vehicles"].items():
            for v in veicoli:
                lista_relazioni.append({"Model Line": ml, "Veicolo": v})
        if lista_relazioni:
            st.dataframe(pd.DataFrame(lista_relazioni), use_container_width=True, height=200)

# ==========================================
# 2. SINGOLO PROGETTO / COSTIFICAZIONE (TAB 2)
# ==========================================
with tab2:
    st.header("Configuratore Economico e di Risorse del Progetto")
    st.info(f"📋 **Linee Guida Attive:** {db['admin']['guidelines']}")
    
    # Recupero dati in caso di caricamento da repository (Workspace)
    wl = st.session_state.workspace
    
    st.subheader("1. Master Data Iniziali")
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        tipo_richiesta = st.selectbox(
            "Tipo di budget richiesto:", 
            ["Nuovo Veicolo", "Change Request"],
            index=0 if wl.get("tipo_richiesta") == "Nuovo Veicolo" else (1 if wl.get("tipo_richiesta") == "Change Request" else 0)
        )
        titolo_cr = ""
        if tipo_richiesta == "Change Request":
            titolo_cr = st.text_input("Titolo della CR (Obbligatorio):", value=wl.get("titolo_cr", ""))
            
    with col_m2:
        model_line_sel = st.selectbox(
            "Seleziona Model Line:", 
            db["admin"]["model_lines"],
            index=db["admin"]["model_lines"].index(wl["model_line"]) if wl.get("model_line") in db["admin"]["model_lines"] else 0
        )
        veicoli_filtrati = db["admin"]["vehicles"].get(model_line_sel, [])
        veicolo_sel = st.selectbox(
            "Seleziona Veicolo coinvolto:", 
            veicoli_filtrati,
            index=veicoli_filtrati.index(wl["veicolo"]) if wl.get("veicolo") in veicoli_filtrati else 0
        )
        
    with col_m3:
        # Gestione date e scadenze milestone
        pm_default = datetime.date.today()
        sop_default = datetime.date.today() + datetime.timedelta(days=365)
        
        if wl.get("milestone_pm"):
            pm_default = datetime.date.fromisoformat(wl["milestone_pm"])
        if wl.get("milestone_sop"):
            sop_default = datetime.date.fromisoformat(wl["milestone_sop"])
            
        milestone_pm = st.date_input("Inizio Progetto (Milestone PM):", value=pm_default)
        milestone_sop = st.date_input("Fine Progetto (Milestone SOP):", value=sop_default)
        
        if milestone_sop > milestone_pm:
            settimane_calc = (milestone_sop - milestone_pm).days / 7.0
            st.markdown(f"Durata Progetto Calcolata: **{settimane_calc:.1f} settimane** ({settimane_calc/52.177:.2f} anni)")
        else:
            st.error("La data di SOP deve essere successiva alla data di PM.")

    premesse_progetto = st.text_area("Definizione delle premesse di progetto:", value=wl.get("premesse", ""))
    
    st.write("---")
    st.subheader("2. Parametri di Costo ed Organizzazione Risorse (Globali)")
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        hc_val = st.number_input("Numero di Interni (HC):", min_value=0, value=wl.get("hc", 5), step=1)
        zbb_val = st.number_input("Numero di Esterni (ZBB):", min_value=0, value=wl.get("zbb", 5), step=1)
        rie_calc = hc_val / zbb_val if zbb_val > 0 else 0.0
        st.markdown(f"Rapporto RIE corrente (HC/ZBB): **{rie_calc:.3f}**")
        
    with col_p2:
        hrHC_val = st.number_input("Costo Orario Interni hrHC (€/h):", min_value=0.0, value=wl.get("hrHC", 60.0), step=5.0)
        hrZBB_val = st.number_input("Costo Orario Esterni hrZBB (€/h):", min_value=0.0, value=wl.get("hrZBB", 45.0), step=5.0)
        
    with col_p3:
        css_val = st.number_input("Costo Medio Sessione Sviluppo CSS (€):", min_value=0.0, value=wl.get("css", 1500.0), step=100.0)

    st.write("---")
    st.subheader("3. Stima dei Costi per Singola ECU (Ripartizione Dinamica)")
    
    selected_ecus = st.multiselect(
        "Seleziona le Centraline coinvolte nel progetto attuale:", 
        db["admin"]["ecu_portfolio"],
        default=wl.get("selected_ecus", [])
    )
    
    # Raccolta degli input generati in tempo reale dalle finestre espanse
    dati_input_ecu = {}
    
    voci_ore_fisse = [
        "Project management", "SW & ZDC management", "Requirement management", 
        "SW development", "SW testing (MIL)", "Issue analysis & Bugfix"
    ]
    
    if selected_ecus:
        for ecu in selected_ecus:
            # Caricamento degli input storici o correnti della ECU dal workspace caricato
            saved_ecu_inputs = wl.get("ecu_data", {}).get(ecu, {}).get("breakdown_inputs", {})
            
            with st.expander(f"⚙️ Finestra Introduzione Costi - Centralina: {ecu}", expanded=True):
                dati_input_ecu[ecu] = {}
                
                col_e1, col_e2, col_e3 = st.columns(3)
                
                with col_e1:
                    st.markdown("**Tempi e Fornitore**")
                    dati_input_ecu[ecu]["nSS"] = st.number_input(
                        f"Settimane Sviluppo/Pista (nSS) - {ecu}:", 
                        min_value=0, value=int(saved_ecu_inputs.get("nSS", 10)), key=f"nss_{ecu}"
                    )
                    dati_input_ecu[ecu]["ecu_supplier_cost"] = st.number_input(
                        f"ECU supplier cost (€) - {ecu}:", 
                        min_value=0.0, value=float(saved_ecu_inputs.get("ecu_supplier_cost", 0.0)), step=500.0, key=f"sup_{ecu}"
                    )
                    
                    # Calcolo e blocco visualizzazione ore di testing pista
                    calc_h_pista = dati_input_ecu[ecu]["nSS"] * 40
                    st.text_input(f"Vehicle testing (h) [nSS * 40] - {ecu}:", value=f"{calc_h_pista} h", disabled=True, key=f"v_h_{ecu}")
                    
                with col_e2:
                    st.markdown("**Immissione Ore Ingegneria (h)**")
                    for voce in voci_ore_fisse:
                        dati_input_ecu[ecu][f"{voce}_h"] = st.number_input(
                            f"{voce} (h) - {ecu}:", 
                            min_value=0.0, value=float(saved_ecu_inputs.get(f"{voce}_h", 0.0)), step=10.0, key=f"h_{voce}_{ecu}"
                        )
                        
                with c_e3 = col_e3:
                    st.markdown("**Voci di Costo Esterno (ext cost)**")
                    dati_input_ecu[ecu]["hil_testing_ext"] = st.number_input(
                        f"HIL testing (€ ext) - {ecu}:", 
                        min_value=0.0, value=float(saved_ecu_inputs.get("hil_testing_ext", 0.0)), step=500.0, key=f"hil_t_{ecu}"
                    )
                    dati_input_ecu[ecu]["hil_setup_ext"] = st.number_input(
                        f"HIL Set-up (HW) (€ ext) - {ecu}:", 
                        min_value=0.0, value=float(saved_ecu_inputs.get("hil_setup_ext", 0.0)), step=500.0, key=f"hil_s_{ecu}"
                    )
                    dati_input_ecu[ecu]["parts_ext"] = st.number_input(
                        f"Parts (€ ext) - {ecu}:", 
                        min_value=0.0, value=float(saved_ecu_inputs.get("parts_ext", 0.0)), step=500.0, key=f"parts_{ecu}"
                    )
                    
                    # Calcolo e blocco visualizzazione costi esterni di testing pista
                    calc_ext_pista = dati_input_ecu[ecu]["nSS"] * css_val
                    st.text_input(f"Vehicle testing (ext cost) [nSS * CSS] - {ecu}:", value=f"{calc_ext_pista:.2f} €", disabled=True, key=f"v_ext_{ecu}")

                # Calcolo reattivo istantaneo per il blocco SUM_UP interno alla ECU
                res_singola = calcola_budget_progetto(
                    milestone_pm, milestone_sop, hc_val, zbb_val, hrHC_val, hrZBB_val, css_val, [ecu], {ecu: dati_input_ecu[ecu]}
                )
                
                if res_singola and ecu in res_singola["ecu_details"]:
                    s_ecu = res_singola["ecu_details"][ecu]
                    st.markdown("---")
                    st.markdown(f"📊 **SUM_UP Singola Centralina - {ecu}**")
                    cs1, cs2, cs3, cs4 = st.columns(4)
                    cs1.metric("Ore HC", f"{s_ecu['hc_hours']:.1f} h", help=f"Ripartite su costo orario hrHC")
                    cs2.metric("Ore ZBB", f"{s_ecu['zbb_hours']:.1f} h", help=f"Ripartite su costo orario hrZBB")
                    cs3.metric("Supplier Cost (€)", f"{s_ecu['supplier_cost']:,} €")
                    cs4.metric("Ext Cost Totale (€)", f"{s_ecu['ext_cost']:,} €")
    else:
        st.warning("Seleziona almeno una centralina dal menu superiore per inserire le stime di costo.")

    # Esecuzione calcoli globali macro sul progetto complessivo
    calcoli_finali = calcola_budget_progetto(
        milestone_pm, milestone_sop, hc_val, zbb_val, hrHC_val, hrZBB_val, css_val, selected_ecus, dati_input_ecu
    )

    # ==========================================
    # 3. OVERVIEW FINALE & LOGICA DI SALVATAGGIO
    # ==========================================
    if selected_ecus and calcoli_finali:
        st.write("---")
        st.header("📈 Overview Finale Consolidata di Progetto")
        
        # 3.1 Tabella di Sintesi delle Ore e FTE
        st.subheader("Sintesi Ore Totali ed Equivalent Workload (FTE)")
        g_metr = calcoli_finali["global"]
        
        data_table_fte = {
            "Metrica Risorsa / Tempo": ["Ore Totali Progetto", "Ore HC (Interne)", "Ore ZBB (Esterne)", "Rapporto RIE Calcolato", "FTE Lavorativi Annui"],
            "Valore di Progetto Consolidato": [
                f"{g_metr['total_hours']:.1f} h",
                f"{g_metr['hc_hours']:.1f} h",
                f"{g_metr['zbb_hours']:.1f} h",
                f"{calcoli_finali['rie']:.3f}",
                f"{g_metr['fte_annui']:.2f} FTE/anno"
            ]
        }
        st.table(pd.DataFrame(data_table_fte))
        
        # 3.2 SUM_UP Totale Progetto (TABELLA RICHIESTA)
        st.subheader("SUM_UP Finanziario Complessivo del Budget")
        
        data_sumup_table = {
            "Voce di Costo": ["Interni (HC)", "Esterni (ZBB)", "Fornitore (Supplier)", "Spese Esterne (Ext Cost)", "GRAND TOTAL PROGETTO"],
            "Ore Totali Riferite": [f"{g_metr['hc_hours']:.1f} h", f"{g_metr['zbb_hours']:.1f} h", "-", "-", f"{g_metr['total_hours']:.1f} h"],
            "Costo Totale (€)": [f"{g_metr['hc_cost']:,} €", f"{g_metr['zbb_cost']:,} €", f"{g_metr['supplier_cost']:,} €", f"{g_metr['ext_cost']:,} €", f"{g_metr['grand_total']:,} €"]
        }
        st.table(pd.DataFrame(data_sumup_table))
        
        # 3.3 Dettaglio ECU Affiancato
        st.subheader("Tabella Comparativa Dettaglio Singole ECU")
        rows_confronto = []
        for ecu_name, details in calcoli_finali["ecu_details"].items():
            rows_confronto.append({
                "Centralina": ecu_name,
                "Settimane (nSS)": details["nSS"],
                "Ore Totali (h)": round(details["total_hours"], 1),
                "Ore HC (h)": round(details["hc_hours"], 1),
                "Ore ZBB (h)": round(details["zbb_hours"], 1),
                "Costo HC (€)": round(details["hc_cost"], 2),
                "Costo ZBB (€)": round(details["zbb_cost"], 2),
                "Supplier (€)": round(details["supplier_cost"], 2),
                "Ext Cost (€)": round(details["ext_cost"], 2),
                "Totale Complessivo (€)": round(details["total_cost"], 2)
            })
        st.dataframe(pd.DataFrame(rows_confronto), use_container_width=True)

        # Logica di Archiviazione e Versionamento
        st.write("---")
        st.subheader("Salvataggio e Storicizzazione della Costificazione")
        
        # Generazione automatica del nome in base alle regole definite
        if tipo_richiesta == "Nuovo Veicolo":
            nome_costificazione_chiave = veicolo_sel if veicolo_sel else "Veicolo_Non_Selezionato"
        else:
            nome_costificazione_chiave = f"{veicolo_sel}_{titolo_cr}".strip() if veicolo_sel and titolo_cr else ""
            
        if not nome_costificazione_chiave or nome_costificazione_chiave.endswith("_"):
            st.error("⚠️ Impossibile salvare: assicurarsi che il veicolo e il titolo della CR siano compilati correttamente.")
        else:
            st.write(f"Chiave identificativa di salvataggio nel repository: **{nome_costificazione_chiave}**")
            
            if st.button("💾 Salva Costificazione Progetto", type="primary"):
                # Creazione del payload completo da archiviare
                payload_salvataggio = {
                    "tipo_richiesta": tipo_richiesta,
                    "titolo_cr": titolo_cr,
                    "model_line": model_line_sel,
                    "veicolo": veicolo_sel,
                    "milestone_pm": milestone_pm.isoformat(),
                    "milestone_sop": milestone_sop.isoformat(),
                    "premesse": premesse_progetto,
                    "hc": hc_val,
                    "zbb": zbb_val,
                    "hrHC": hrHC_val,
                    "hrZBB": hrZBB_val,
                    "css": css_val,
                    "selected_ecus": selected_ecus,
                    "ecu_data": dati_input_ecu,
                    "summary_calculations": {
                        "global": g_metr,
                        "rie": calcoli_finali["rie"],
                        "weeks": calcoli_finali["settimane_progetto"],
                        "ecu_rows": rows_confronto
                    },
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Gestione dello storico e del versionamento progressivo automatico
                if nome_costificazione_chiave not in db["repository"]:
                    payload_salvataggio["version"] = 1
                    db["repository"][nome_costificazione_chiave] = [payload_salvataggio]
                    st.success(f"Budget '{nome_costificazione_chiave}' registrato con successo (Versione v1)!")
                else:
                    storico_esistente = db["repository"][nome_costificazione_chiave]
                    prossima_v = len(storico_existing := storico_esistente) + 1
                    payload_salvataggio["version"] = prossima_v
                    db["repository"][nome_costificazione_chiave].append(payload_salvataggio)
                    st.success(f"Archiviata nuova versione v{prossima_v} per la costificazione '{nome_costificazione_chiave}'.")
                    
                save_db(db)
                # Pulisce l'area workspace temporanea dopo il salvataggio
                st.session_state.workspace = {}
                st.rerun()

# ==========================================
# 4. REPOSITORY & VERSIONING (TAB 3)
# ==========================================
with tab3:
    st.header("🗄️ Repository Storico e Controllo Versionamento")
    
    if not db["repository"]:
        st.info("Nessun budget salvato trovato in archivio. Compila e salva una simulazione nel Tab 2 per iniziare.")
    else:
        nomi_progetti = list(db["repository"].keys())
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            progetto_selezionato = st.selectbox("Seleziona il Progetto da ispezionare:", nomi_progetti)
        
        if record_storico := db["repository"].get(progetto_selezionato):
            with col_r2:
                versioni_disponibili = [f"Versione v{v['version']} — [{v['timestamp']}]" for v in record_storico]
                versione_selezionata_str = st.selectbox("Seleziona la versione del preventivo:", versioni_disponibili)
                
            idx_v = versioni_disponibili.index(versione_selezionata_str)
            budget_archiviato = record_storico[idx_v]
            
            # --- APERTURA ED ISPEZIONE IMMEDIATA DEL DETTAGLIO RICHIESTA ---
            st.write("---")
            st.markdown(f"### 🔍 Dettaglio Completo Archiviato: `{progetto_selezionato}` (v{budget_archiviato['version']})")
            
            c_det1, c_det2, c_det3 = st.columns(3)
            with c_det1:
                st.markdown(f"**Tipo Richiesta:** {budget_archiviato['tipo_richiesta']}")
                st.markdown(f"**Model Line:** {budget_archiviato['model_line']}")
                st.markdown(f"**Veicolo:** {budget_archiviato['veicolo']}")
            with c_det2:
                st.markdown(f"**Milestone PM:** {budget_archiviato['milestone_pm']}")
                st.markdown(f"**Milestone SOP:** {budget_archiviato['milestone_sop']}")
                st.markdown(f"**Durata:** {budget_archiviato['summary_calculations']['weeks']:.1f} settimane")
            with c_det3:
                g_saved = budget_archiviato["summary_calculations"]["global"]
                st.markdown(f"**Costo Totale Progetto:** {g_saved['grand_total']:,} €")
                st.markdown(f"**Forza Lavoro Totale:** {g_saved['fte_annui']:.2f} FTE/anno")
                
            st.markdown(f"**Premesse del Preventivo:** *{budget_archiviato['premesse']}*")
            
            # Rendering immediato delle tabelle consolidate memorizzate
            st.markdown("#### Tabelle di Sintesi Finanziaria Salvare")
            
            # Tabella SUM_UP consolidata
            data_sumup_saved = {
                "Voce di Costo": ["Interni (HC)", "Esterni (ZBB)", "Fornitore (Supplier)", "Spese Esterne (Ext Cost)", "GRAND TOTAL"],
                "Ore Riferite": [f"{g_saved['hc_hours']:.1f} h", f"{g_saved['zbb_hours']:.1f} h", "-", "-", f"{g_saved['total_hours']:.1f} h"],
                "Costo (€)": [f"{g_saved['hc_cost']:,} €", f"{g_saved['zbb_cost']:,} €", f"{g_saved['supplier_cost']:,} €", f"{g_saved['ext_cost']:,} €", f"{g_saved['grand_total']:,} €"]
            }
            st.table(pd.DataFrame(data_sumup_saved))
            
            # Tabella spaccato ECU analitico memorizzato
            st.markdown("#### Spaccato Analitico di tutte le ECU coinvolte:")
            df_ecu_saved = pd.DataFrame(budget_archiviato["summary_calculations"]["ecu_rows"])
            st.dataframe(df_ecu_saved, use_container_width=True)
            
            # Azione di caricamento nel workspace operativo del Tab 2 per modifiche
            st.write("---")
            if st.button("🔄 Carica questa Costificazione nel Configuratore (Tab 2) per Modifica"):
                st.session_state.workspace = budget_archiviato
                st.success("Dati pronti nell'area di lavoro del Tab 2! Spostati nella scheda precedente per modificare i parametri e registrare una nuova versione.")
                st.rerun()
