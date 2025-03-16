import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Geopolymer Concrete Mix Design Calculator By AMAN CHOUDHARY",
    page_icon="🧪",
    layout="wide"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0f66bd;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .section-header {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .result-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #0f66bd;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #e7f0ff;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #4c8dff;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main mix design function (simplified)
def geopolymer_mix_design(target_strength, precursors, activators, fine_agg, coarse_agg, ss_sh_ratio=2.0, act_binder_ratio=0.45, extra_water=0):
    """Calculate geopolymer concrete mix design based on IS 17452:2020 guidelines."""
    warnings = []
    
    # Validate inputs
    precursor_sum = sum(p['percentage'] for p in precursors.values())
    if abs(precursor_sum - 100) > 0.1:
        return {"error": f"Precursor percentages must sum to 100%, current sum is {precursor_sum}%"}
    
    # Determine total binder content based on target strength
    if target_strength <= 30:
        total_binder_content = 350  # kg/m³
    elif target_strength <= 40:
        total_binder_content = 400  # kg/m³
    elif target_strength <= 50:
        total_binder_content = 450  # kg/m³
    else:
        total_binder_content = 500  # kg/m³
    
    # Calculate individual binder quantities
    binder_quantities = {}
    for name, props in precursors.items():
        if props['percentage'] > 0:
            binder_quantities[name] = total_binder_content * props['percentage'] / 100
    
    # Calculate activator quantities
    total_activator = total_binder_content * act_binder_ratio
    
    activator_quantities = {}
    if 'Sodium Silicate' in activators and 'Sodium Hydroxide' in activators:
        # Both SS and SH are used
        ss_quantity = total_activator * ss_sh_ratio / (1 + ss_sh_ratio)
        sh_quantity = total_activator - ss_quantity
        
        activator_quantities['Sodium Silicate'] = ss_quantity
        activator_quantities['Sodium Hydroxide'] = sh_quantity
    elif 'Sodium Silicate' in activators:
        # Only SS is used
        activator_quantities['Sodium Silicate'] = total_activator
    elif 'Sodium Hydroxide' in activators:
        # Only SH is used
        activator_quantities['Sodium Hydroxide'] = total_activator
    
    # Calculate water in the activator
    water_in_activator = 0
    if 'Sodium Silicate' in activator_quantities:
        water_in_activator += activator_quantities['Sodium Silicate'] * activators['Sodium Silicate']['h2o'] / 100
    
    if 'Sodium Hydroxide' in activator_quantities:
        molarity = activators['Sodium Hydroxide']['molarity']
        # Approximate calculation for water in SH solution
        naoh_mass = 40  # g/mol
        water_fraction = 1 - (molarity * naoh_mass / 1000) / (molarity * naoh_mass / 1000 + 1000)
        water_in_activator += activator_quantities['Sodium Hydroxide'] * water_fraction
    
    # Add extra water if specified
    total_water = water_in_activator + extra_water
    
    # Estimate air content
    air_content = 0.02  # 2%
    
    # Calculate aggregate content based on absolute volume method
    # Convert all ingredients to volume
    total_volume = 1.0  # m³
    
    # Volume of binders
    binder_volume = sum(qty / (precursors[name]['sg'] * 1000) for name, qty in binder_quantities.items())
    
    # Volume of activators
    activator_volume = 0
    if 'Sodium Silicate' in activator_quantities:
        activator_volume += activator_quantities['Sodium Silicate'] / (activators['Sodium Silicate']['sg'] * 1000)
    
    if 'Sodium Hydroxide' in activator_quantities:
        # Approximate SH solution density based on molarity
        molarity = activators['Sodium Hydroxide']['molarity']
        sh_density = 1000 + 0.04 * molarity * 40  # Approximate formula
        activator_volume += activator_quantities['Sodium Hydroxide'] / sh_density
    
    # Volume for extra water
    extra_water_volume = extra_water / 1000
    
    # Volume for aggregates
    agg_volume = total_volume - binder_volume - activator_volume - extra_water_volume - air_content
    
    # Split between fine and coarse aggregates based on coarse aggregate size
    ca_size = coarse_agg['size']
    fa_fraction = 0  # Fine aggregate fraction of total aggregate
    
    if ca_size <= 10:
        fa_fraction = 0.45
    elif ca_size <= 20:
        fa_fraction = 0.40
    else:
        fa_fraction = 0.35
    
    # Adjust based on fineness modulus
    fm = fine_agg['fm']
    fa_fraction += (2.6 - fm) * 0.05  # Adjust by up to ±5% based on FM
    
    # Calculate aggregate quantities
    fa_volume = agg_volume * fa_fraction
    ca_volume = agg_volume - fa_volume
    
    fa_quantity = fa_volume * fine_agg['sg'] * 1000
    ca_quantity = ca_volume * coarse_agg['sg'] * 1000
    
    # Adjust for moisture content
    fa_moisture = fine_agg['moisture']
    ca_moisture = coarse_agg['moisture']
    
    fa_quantity_wet = fa_quantity * (1 + fa_moisture / 100)
    ca_quantity_wet = ca_quantity * (1 + ca_moisture / 100)
    
    # Calculate concrete density
    concrete_density = sum(binder_quantities.values()) + sum(activator_quantities.values()) + extra_water + fa_quantity_wet + ca_quantity_wet
    
    # Calculate water to geopolymer solids ratio
    activator_solids = 0
    if 'Sodium Silicate' in activator_quantities:
        ss = activators['Sodium Silicate']
        activator_solids += activator_quantities['Sodium Silicate'] * (ss['sio2'] + ss['na2o']) / 100
    
    total_solids = sum(binder_quantities.values()) + activator_solids
    water_geopolymer_solids_ratio = total_water / total_solids if total_solids > 0 else 0
    
    # Prepare results
    results = {
        'target_strength': target_strength,
        'binder_quantities': binder_quantities,
        'total_binder': sum(binder_quantities.values()),
        'activator_quantities': activator_quantities,
        'total_activator': sum(activator_quantities.values()),
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

# Application title
st.markdown('<h1 class="main-header">Geopolymer Concrete Mix Design Calculator<br>(IS 17452:2020)</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
This calculator implements the mix design methodology for alkali-activated concrete according to IS 17452:2020. Enter your design parameters below to generate a comprehensive mix design.
</div>
""", unsafe_allow_html=True)

# Target Properties
st.markdown('<h2 class="section-header">Target Properties</h2>', unsafe_allow_html=True)
target_strength = st.number_input("Target Compressive Strength (MPa)", 
                               min_value=20, max_value=80, value=40, 
                               help="Specify the required 28-day compressive strength")

# Precursor Materials
st.markdown('<h2 class="section-header">Precursor Materials</h2>', unsafe_allow_html=True)

# Initialize precursors dictionary
precursors = {
    'Fly Ash': {'percentage': 70, 'sg': 2.2},
    'GGBFS': {'percentage': 30, 'sg': 2.9},
    'Metakaolin': {'percentage': 0, 'sg': 2.6},
    'Silica Fume': {'percentage': 0, 'sg': 2.2}
}

# Fly Ash
col1, col2 = st.columns(2)
with col1:
    precursors['Fly Ash']['percentage'] = st.number_input("Fly Ash Percentage", 
                                                       min_value=0, max_value=100, value=70,
                                                       help="Percentage of fly ash in the total binder")
with col2:
    precursors['Fly Ash']['sg'] = st.number_input("Fly Ash Specific Gravity", 
                                               min_value=2.0, max_value=3.0, value=2.2, step=0.1,
                                               help="Specific gravity of fly ash")

# GGBFS
col1, col2 = st.columns(2)
with col1:
    precursors['GGBFS']['percentage'] = st.number_input("GGBFS Percentage", 
                                                     min_value=0, max_value=100, value=30,
                                                     help="Percentage of GGBFS in the total binder")
with col2:
    precursors['GGBFS']['sg'] = st.number_input("GGBFS Specific Gravity", 
                                             min_value=2.0, max_value=3.5, value=2.9, step=0.1,
                                             help="Specific gravity of GGBFS")

# Calculate total precursor percentage and show warning if not 100%
total_precursor = sum(p['percentage'] for p in precursors.values())
if abs(total_precursor - 100) > 0.1:
    st.markdown(f"""
    <div class="warning-box">
    <strong>Warning:</strong> Precursor percentages must sum to 100%. Current sum is {total_precursor}%.
    </div>
    """, unsafe_allow_html=True)

# Activator configuration
st.markdown('<h2 class="section-header">Alkaline Activators</h2>', unsafe_allow_html=True)

# Initialize activators dictionary
activators = {}

# Sodium Silicate
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

# Sodium Hydroxide
use_sodium_hydroxide = st.checkbox("Use Sodium Hydroxide", value=True)
if use_sodium_hydroxide:
    naoh_molarity = st.number_input("NaOH Molarity (M)", 
                                  min_value=4, max_value=16, value=10, step=1,
                                  help="Molarity of sodium hydroxide solution")
    
    activators['Sodium Hydroxide'] = {
        'molarity': naoh_molarity
    }

# Activator Ratio
st.markdown("#### Activator Parameters")
col1, col2 = st.columns(2)
with col1:
    ss_sh_ratio = st.number_input("Sodium Silicate to Sodium Hydroxide Ratio", 
                                 min_value=0.5, max_value=5.0, value=2.0, step=0.1,
                                 help="Mass ratio of sodium silicate to sodium hydroxide solution")
with col2:
    act_binder_ratio = st.number_input("Activator to Binder Ratio", 
                                     min_value=0.3, max_value=0.6, value=0.45, step=0.05,
                                     help="Mass ratio of total activator to total binder")

# Extra water
extra_water = st.number_input("Additional Water (kg/m³)", 
                            min_value=0, max_value=50, value=0, step=5,
                            help="Extra water for workability adjustment")

# Aggregate configuration
st.markdown('<h2 class="section-header">Aggregates</h2>', unsafe_allow_html=True)

# Fine aggregate
st.markdown("#### Fine Aggregate")
col1, col2, col3 = st.columns(3)
with col1:
    fa_sg = st.number_input("Fine Aggregate Specific Gravity", 
                          min_value=2.4, max_value=2.8, value=2.6, step=0.1,
                          help="Specific gravity of fine aggregate")
with col2:
    fa_fm = st.number_input("Fineness Modulus", 
                          min_value=2.0, max_value=3.5, value=2.8, step=0.1,
                          help="Fineness modulus of fine aggregate")
with col3:
    fa_moisture = st.number_input("Fine Aggregate Moisture Content (%)", 
                                min_value=0.0, max_value=10.0, value=2.0, step=0.5,
                                help="Moisture content of fine aggregate as percentage of dry weight")

fine_agg = {
    'sg': fa_sg,
    'fm': fa_fm,
    'moisture': fa_moisture
}

# Coarse aggregate
st.markdown("#### Coarse Aggregate")
col1, col2, col3 = st.columns(3)
with col1:
    ca_sg = st.number_input("Coarse Aggregate Specific Gravity", 
                          min_value=2.4, max_value=3.0, value=2.7, step=0.1,
                          help="Specific gravity of coarse aggregate")
with col2:
    ca_size = st.selectbox("Maximum Aggregate Size (mm)", 
                         options=[10, 20, 40], index=1,
                         help="Maximum size of coarse aggregate")
with col3:
    ca_moisture = st.number_input("Coarse Aggregate Moisture Content (%)", 
                                min_value=0.0, max_value=10.0, value=1.0, step=0.5,
                                help="Moisture content of coarse aggregate as percentage of dry weight")

coarse_agg = {
    'sg': ca_sg,
    'size': ca_size,
    'moisture': ca_moisture
}

# Calculate button
if st.button("Calculate Mix Design", type="primary"):
    # Check if the total precursor percentage is 100%
    total_precursor = sum(p['percentage'] for p in precursors.values())
    if abs(total_precursor - 100) > 0.1:
        st.error(f"Precursor percentages must sum to 100%. Current sum is {total_precursor}%.")
    else:
        # Calculate mix design
        mix_design = geopolymer_mix_design(
            target_strength=target_strength,
            precursors=precursors,
            activators=activators,
            fine_agg=fine_agg,
            coarse_agg=coarse_agg,
            ss_sh_ratio=ss_sh_ratio,
            act_binder_ratio=act_binder_ratio,
            extra_water=extra_water
        )
        
        if 'error' in mix_design:
            st.error(mix_design['error'])
        else:
            # Display warnings if any
            if mix_design['warnings']:
                for warning in mix_design['warnings']:
                    st.markdown(f"""
                    <div class="warning-box">
                    <strong>Warning:</strong> {warning}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Display results
            st.markdown('<h2 class="section-header">Mix Design Results</h2>', unsafe_allow_html=True)
            
            # Material quantities
            st.markdown("### Material Quantities (kg/m³)")
            
            # Create a DataFrame for displaying quantities
            quantities_data = []
            
            # Add binder materials
            for name, quantity in mix_design['binder_quantities'].items():
                quantities_data.append({
                    'Material': name,
                    'Category': 'Binder',
                    'Quantity (kg/m³)': round(quantity, 1)
                })
            
            # Add activators
            for name, quantity in mix_design['activator_quantities'].items():
                quantities_data.append({
                    'Material': name,
                    'Category': 'Activator',
                    'Quantity (kg/m³)': round(quantity, 1)
                })
            
            # Add extra water if any
            if mix_design['extra_water'] > 0:
                quantities_data.append({
                    'Material': 'Additional Water',
                    'Category': 'Water',
                    'Quantity (kg/m³)': round(mix_design['extra_water'], 1)
                })
            
            # Add aggregates
            quantities_data.append({
                'Material': 'Fine Aggregate',
                'Category': 'Aggregate',
                'Quantity (kg/m³)': round(mix_design['fine_aggregate'], 1)
            })
            
            quantities_data.append({
                'Material': 'Coarse Aggregate',
                'Category': 'Aggregate',
                'Quantity (kg/m³)': round(mix_design['coarse_aggregate'], 1)
            })
            
            # Create DataFrame
            quantities_df = pd.DataFrame(quantities_data)
            
            # Display quantities table
            st.table(quantities_df)
            
            # Display totals
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Binder", f"{mix_design['total_binder']:.1f} kg/m³")
            with col2:
                st.metric("Total Activator", f"{mix_design['total_activator']:.1f} kg/m³")
            with col3:
                st.metric("Total Water Content", f"{mix_design['water_content']:.1f} kg/m³")
            
            # Display concrete properties
            st.markdown("### Concrete Properties")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Estimated Concrete Density", f"{mix_design['concrete_density']:.1f} kg/m³")
            with col2:
                st.metric("Water to Geopolymer Solids Ratio", f"{mix_design['water_geopolymer_solids_ratio']:.3f}")
            
            # Display mix ratio
            st.markdown("### Mix Ratio (by weight)")
            mr = mix_design['mix_ratio']
            st.markdown(f"**Binder : Activator : Fine Agg : Coarse Agg = 1 : {mr['activator']:.2f} : {mr['fine_agg']:.2f} : {mr['coarse_agg']:.2f}**")

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 40px; padding: 20px; background-color: #f0f2f6; border-radius: 5px;">
<p style="margin-bottom: 5px;">Geopolymer Concrete Mix Design Calculator based on IS 17452:2020</p>
<p style="font-size: 0.8em; color: #666;">Disclaimer: This calculator is provided for educational and research purposes only.</p>
</div>
""", unsafe_allow_html=True)
