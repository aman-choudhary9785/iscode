import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Geopolymer Concrete Mix Design Calculator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #0f66bd; text-align: center; margin-bottom: 1.5rem;}
    .section-header {background-color: #f0f2f6; padding: 0.5rem; border-radius: 5px;}
    .result-box {background-color: #f8f9fa; padding: 1rem; border-radius: 5px; border-left: 5px solid #0f66bd; margin: 1rem 0;}
    .info-box {background-color: #e7f0ff; padding: 1rem; border-radius: 5px; border-left: 5px solid #4c8dff; margin: 1rem 0;}
    .warning-box {background-color: #fff3cd; padding: 1rem; border-radius: 5px; border-left: 5px solid #ffc107; margin: 1rem 0;}
</style>
""", unsafe_allow_html=True)

def geopolymer_mix_design(target_strength, precursors, activators, fine_agg, coarse_agg, ss_sh_ratio=2.0, act_binder_ratio=0.45, extra_water=0):
    warnings = []
    
    precursor_sum = sum(p['percentage'] for p in precursors.values())
    if abs(precursor_sum - 100) > 0.1:
        return {"error": f"Precursor percentages must sum to 100%, current sum is {precursor_sum}%"}
    
    if 'Sodium Silicate' in activators:
        ss = activators['Sodium Silicate']
        ss_sum = ss['sio2'] + ss['na2o'] + ss['h2o']
        if abs(ss_sum - 100) > 0.1:
            return {"error": f"Sodium silicate composition must sum to 100%, current sum is {ss_sum}%"}
        
        activator_modulus = ss['sio2'] / ss['na2o']
        if activator_modulus < 0.6 or activator_modulus > 2.0:
            warnings.append(f"Activator modulus (SiO₂/Na₂O = {activator_modulus:.2f}) is outside the recommended range (0.6-2.0) as per IS 17452:2020")
        
        if ss['sio2'] < 30 or ss['sio2'] > 35:
            warnings.append(f"SiO₂ content ({ss['sio2']}%) is outside the recommended range (30-35%) as per IS 17452:2020")
        
        if ss['na2o'] < 12 or ss['na2o'] > 18:
            warnings.append(f"Na₂O content ({ss['na2o']}%) is outside the recommended range (12-18%) as per IS 17452:2020")
        
        if ss['h2o'] < 40 or ss['h2o'] > 50:
            warnings.append(f"H₂O content ({ss['h2o']}%) is outside the recommended range (40-50%) as per IS 17452:2020")
    
    if target_strength <= 30:
        total_binder_content = 350
    elif target_strength <= 40:
        total_binder_content = 400
    elif target_strength <= 50:
        total_binder_content = 450
    else:
        total_binder_content = 500
    
    binder_quantities = {name: total_binder_content * props['percentage'] / 100 for name, props in precursors.items() if props['percentage'] > 0}
    
    total_activator = total_binder_content * act_binder_ratio
    activator_quantities = {}
    if 'Sodium Silicate' in activators and 'Sodium Hydroxide' in activators:
        ss_quantity = total_activator * ss_sh_ratio / (1 + ss_sh_ratio)
        sh_quantity = total_activator - ss_quantity
        activator_quantities['Sodium Silicate'] = ss_quantity
        activator_quantities['Sodium Hydroxide'] = sh_quantity
    elif 'Sodium Silicate' in activators:
        activator_quantities['Sodium Silicate'] = total_activator
    elif 'Sodium Hydroxide' in activators:
        activator_quantities['Sodium Hydroxide'] = total_activator
    
    water_in_activator = 0
    if 'Sodium Silicate' in activator_quantities:
        water_in_activator += activator_quantities['Sodium Silicate'] * activators['Sodium Silicate']['h2o'] / 100
    
    if 'Sodium Hydroxide' in activator_quantities:
        molarity = activators['Sodium Hydroxide']['molarity']
        naoh_mass = 40
        naoh_solid_concentration = molarity * naoh_mass / 1000
        naoh_solution_density = 1000 + (naoh_solid_concentration * 1000)
        naoh_solid_fraction = naoh_solid_concentration / (naoh_solution_density / 1000)
        water_in_activator += activator_quantities['Sodium Hydroxide'] * (1 - naoh_solid_fraction)
    
    total_water = water_in_activator + extra_water
    
    air_content = 0.02
    total_volume = 1.0
    binder_volume = sum(qty / (precursors[name]['sg'] * 1000) for name, qty in binder_quantities.items())
    activator_volume = 0
    if 'Sodium Silicate' in activator_quantities:
        activator_volume += activator_quantities['Sodium Silicate'] / (activators['Sodium Silicate']['sg'] * 1000)
    if 'Sodium Hydroxide' in activator_quantities:
        molarity = activators['Sodium Hydroxide']['molarity']
        sh_density = 1000 + 0.04 * molarity * 40
        activator_volume += activator_quantities['Sodium Hydroxide'] / sh_density
    
    extra_water_volume = extra_water / 1000
    agg_volume = total_volume - binder_volume - activator_volume - extra_water_volume - air_content
    
    ca_size = coarse_agg['size']
    fa_fraction = 0.35 if ca_size > 20 else (0.40 if ca_size > 10 else 0.45)
    fa_fraction += (2.6 - fine_agg['fm']) * 0.05
    
    fa_volume = agg_volume * fa_fraction
    ca_volume = agg_volume - fa_volume
    fa_quantity = fa_volume * fine_agg['sg'] * 1000
    ca_quantity = ca_volume * coarse_agg['sg'] * 1000
    
    fa_quantity_wet = fa_quantity * (1 + fine_agg['moisture'] / 100)
    ca_quantity_wet = ca_quantity * (1 + coarse_agg['moisture'] / 100)
    
    concrete_density = sum(binder_quantities.values()) + sum(activator_quantities.values()) + extra_water + fa_quantity_wet + ca_quantity_wet
    
    activator_solids = 0
    if 'Sodium Silicate' in activator_quantities:
        ss = activators['Sodium Silicate']
        activator_solids += activator_quantities['Sodium Silicate'] * (ss['sio2'] + ss['na2o']) / 100
    if 'Sodium Hydroxide' in activator_quantities:
        molarity = activators['Sodium Hydroxide']['molarity']
        naoh_solid_concentration = molarity * 40 / 1000
        naoh_solution_density = 1000 + (naoh_solid_concentration * 1000)
        naoh_solid_fraction = naoh_solid_concentration / (naoh_solution_density / 1000)
        activator_solids += activator_quantities['Sodium Hydroxide'] * naoh_solid_fraction
    
    total_solids = sum(binder_quantities.values()) + activator_solids
    water_geopolymer_solids_ratio = total_water / total_solids if total_solids > 0 else 0
    
    results = {
        'target_strength': target_strength,
        'binder_quantities': binder_quantities,
        'total_binder': sum(binder_quantities.values()),
        'activator_quantities': activator_quantities,
        'total_activator': sum(activator_quantities.values()),
        'activator_solids': activator_solids,
        'fine_aggregate': fa_quantity_wet,
        'coarse_aggregate': ca_quantity_wet,
        'water_content': total_water,
        'extra_water': extra_water,
        'water_geopolymer_solids_ratio': water_geopolymer_solids_ratio,
        'concrete_density': concrete_density,
        'warnings': warnings,
        'mix_ratio': {
            'binder': 1.0,
            'activator': sum(activator_quantities.values()) / sum(binder_quantities.values()) if sum(binder_quantities.values()) > 0 else 0,
            'fine_agg': fa_quantity_wet / sum(binder_quantities.values()) if sum(binder_quantities.values()) > 0 else 0,
            'coarse_agg': ca_quantity_wet / sum(binder_quantities.values()) if sum(binder_quantities.values()) > 0 else 0
        }
    }
    
    return results

st.markdown('<h1 class="main-header">Geopolymer Concrete Mix Design Calculator<br>(IS 17452:2020)</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
This calculator implements the mix design methodology for alkali-activated concrete according to IS 17452:2020. Enter your design parameters below to generate a comprehensive mix design.
</div>
""", unsafe_allow_html=True)

st.markdown('<h2 class="section-header">Target Properties</h2>', unsafe_allow_html=True)
target_strength = st.number_input("Target Compressive Strength (MPa)", 
                               min_value=20, max_value=80, value=40, 
                               help="Specify the required 28-day compressive strength")

st.markdown('<h2 class="section-header">Precursor Materials</h2>', unsafe_allow_html=True)

precursors = {
    'Fly Ash': {'percentage': 70, 'sg': 2.2},
    'GGBFS': {'percentage': 30, 'sg': 2.9},
    'Metakaolin': {'percentage': 0, 'sg': 2.6},
    'Silica Fume': {'percentage': 0, 'sg': 2.2}
}

col1, col2 = st.columns(2)
with col1:
    precursors['Fly Ash']['percentage'] = st.number_input("Fly Ash Percentage", 
                                                       min_value=0, max_value=100, value=70,
                                                       help="Percentage of fly ash in the total binder")
with col2:
    precursors['Fly Ash']['sg'] = st.number_input("Fly Ash Specific Gravity", 
                                               min_value=2.0, max_value=3.0, value=2.2, step=0.1,
                                               help="Specific gravity of fly ash")

col1, col2 = st.columns(2)
with col1:
    precursors['GGBFS']['percentage'] = st.number_input("GGBFS Percentage", 
                                                     min_value=0, max_value=100, value=30,
                                                     help="Percentage of GGBFS in the total binder")
with col2:
    precursors['GGBFS']['sg'] = st.number_input("GGBFS Specific Gravity", 
                                             min_value=2.0, max_value=3.5, value=2.9, step=0.1,
                                             help="Specific gravity of GGBFS")

total_precursor = sum(p['percentage'] for p in precursors.values())
if abs(total_precursor - 100) > 0.1:
    st.markdown(f"""
    <div class="warning-box">
    <strong>Warning:</strong> Precursor percentages must sum to 100%. Current sum is {total_precursor}%.
    </div>
    """, unsafe_allow_html=True)

st.markdown('<h2 class="section-header">Alkaline Activators</h2>', unsafe_allow_html=True)

activators = {}

use_sodium_silicate = st.checkbox("Use Sodium Silicate", value=True)
if use_sodium_silicate:
    col1, col2, col3 = st.columns(3)
    with col1:
        sio2 = st.number_input("SiO₂ Content (%)", min_value=20, max_value=40, value=30,
                             help="Percentage of SiO₂ in sodium silicate solution")
    with col2:
        na2o = st.number_input("Na₂O Content (%)", min_value=5, max_value=25, value=15,
                             help="Percentage of Na₂O in sodium silicate solution")
    with col3:
        h2o = st.number_input("H₂O Content (%)", min_value=30, max_value=70, value=55,
                            help="Percentage of H₂O in sodium silicate solution")
    
    ss_sg = st.number_input("Sodium Silicate Specific Gravity", 
                          min_value=1.3, max_value=1.8, value=1.5, step=0.1,
                          help="Specific gravity of sodium silicate solution")
    
    activators['Sodium Silicate'] = {
        'sio2': sio2,
        'na2o': na2o,
        'h2o': h2o,
        'sg': ss_sg
    }

use_sodium_hydroxide = st.checkbox("Use Sodium Hydroxide", value=True)
if use_sodium_hydroxide:
    naoh_molarity = st.number_input("NaOH Molarity (M)", 
                                  min_value=4, max_value=16, value=10, step=1,
                                  help="Molarity of sodium hydroxide solution")
    
    activators['Sodium Hydroxide'] = {
        'molarity': naoh_molarity
    }

st.markdown("#### Activator Parameters")
col1, col2 = st.columns(2)
with col1:
    ss_sh_ratio = st.number_input("Sodium Silicate to Sodium Hydroxide Ratio", 
                                 min_value=0.5, max_value=5.0, value=2.0, step=0.1,
                                 help="Mass ratio of sodium silicate to sodium
