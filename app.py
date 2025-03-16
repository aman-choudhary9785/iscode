import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt

st.set_page_config(
    page_title="Geopolymer Concrete Mix Design Calculator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f66bd;
        color: white;
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

# Main mix design function
def geopolymer_mix_design(target_strength, precursors, activators, fine_agg, coarse_agg, ss_sh_ratio=2.0, act_binder_ratio=0.45, extra_water=0):
    """
    Calculate geopolymer concrete mix design based on IS 17452:2020 guidelines.
    
    Parameters:
    -----------
    target_strength : float
        Target compressive strength in MPa
    precursors : dict
        Dictionary of precursor materials with their percentages and specific gravities
    activators : dict
        Dictionary of alkaline activators with their properties
    fine_agg : dict
        Properties of fine aggregate: {'sg': float, 'fm': float, 'moisture': float}
    coarse_agg : dict
        Properties of coarse aggregate: {'sg': float, 'size': int, 'moisture': float}
    ss_sh_ratio : float, optional
        Ratio of sodium silicate to sodium hydroxide, by default 2.0
    act_binder_ratio : float, optional
        Ratio of activator to binder, by default 0.45
    extra_water : float, optional
        Additional water in kg/m³, by default 0
    
    Returns:
    --------
    dict
        Mix design results including quantities of all materials
    """
    warnings = []
    
    # Validate inputs
    precursor_sum = sum(p['percentage'] for p in precursors.values())
    if abs(precursor_sum - 100) > 0.1:
        return {"error": f"Precursor percentages must sum to 100%, current sum is {precursor_sum}%"}
    
    if 'Sodium Silicate' in activators:
        ss = activators['Sodium Silicate']
        ss_sum = ss['sio2'] + ss['na2o'] + ss['h2o']
        if abs(ss_sum - 100) > 0.1:
            return {"error": f"Sodium silicate composition must sum to 100%, current sum is {ss_sum}%"}
        
        # Check activator modulus according to IS 17452:2020
        activator_modulus = ss['sio2'] / ss['na2o']
        if activator_modulus < 0.6 or activator_modulus > 2.0:
            warnings.append(f"Activator modulus (SiO₂/Na₂O = {activator_modulus:.2f}) is outside the recommended range (0.6-2.0) as per IS 17452:2020")
        
        # Check composition ranges
        if ss['sio2'] < 30 or ss['sio2'] > 35:
            warnings.append(f"SiO₂ content ({ss['sio2']}%) is outside the recommended range (30-35%) as per IS 17452:2020")
        
        if ss['na2o'] < 12 or ss['na2o'] > 18:
            warnings.append(f"Na₂O content ({ss['na2o']}%) is outside the recommended range (12-18%) as per IS 17452:2020")
        
        if ss['h2o'] < 40 or ss['h2o'] > 50:
            warnings.append(f"H₂O content ({ss['h2o']}%) is outside the recommended range (40-50%) as per IS 17452:2020")
    
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
        # Calculate NaOH solid content
        naoh_mass = 40  # g/mol
        naoh_solid_concentration = molarity * naoh_mass / 1000  # kg/L
        naoh_solution_density = 1000 + (naoh_solid_concentration * 1000)  # kg/m³ (approximate)
        naoh_solid_fraction = naoh_solid_concentration / (naoh_solution_density / 1000)
        
        water_in_activator += activator_quantities['Sodium Hydroxide'] * (1 - naoh_solid_fraction)
    
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
    
    # Calculate activator solids (for technical details)
    activator_solids = 0
    if 'Sodium Silicate' in activator_quantities:
        ss = activators['Sodium Silicate']
        activator_solids += activator_quantities['Sodium Silicate'] * (ss['sio2'] + ss['na2o']) / 100
    
    if 'Sodium Hydroxide' in activator_quantities:
        molarity = activators['Sodium Hydroxide']['molarity']
        naoh_solid_concentration = molarity * 40 / 1000  # kg/L
        naoh_solution_density = 1000 + (naoh_solid_concentration * 1000)  # kg/m³
        naoh_solid_fraction = naoh_solid_concentration / (naoh_solution_density / 1000)
        activator_solids += activator_quantities['Sodium Hydroxide'] * naoh_solid_fraction
    
    # Calculate total solids (binder + activator solids)
    total_solids = sum(binder_quantities.values()) + activator_solids
    
    # Calculate water to geopolymer solids ratio
    if total_solids > 0:
        water_geopolymer_solids_ratio = total_water / total_solids
    else:
        water_geopolymer_solids_ratio = 0
    
    # Prepare results
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

# Sidebar for general settings
st.sidebar.markdown('<h1 style="text-align: center; color: #0f66bd;">Settings</h1>', unsafe_allow_html=True)

# Information and standards
with st.sidebar.expander("About IS 17452:2020", expanded=False):
    st.markdown("""
    **IS 17452:2020** is an Indian Standard that provides guidelines for the use of alkali-activated concrete for precast products. 
    
    Key provisions of this standard include:
    
    - Activator modulus (SiO₂/Na₂O) should range between 0.6 and 2.0
    - Sodium silicate solution composition recommendations:
        - SiO₂: 30-35%
        - Na₂O: 12-18%
        - H₂O: 40-50%
    - Mix design principles based on absolute volume method
    - Appropriate ranges for activator-to-binder ratios based on target strength
    
    This calculator implements these guidelines to provide standardized mix designs for geopolymer concrete.
    """)

# Application title
st.markdown('<h1 class="main-header">Geopolymer Concrete Mix Design Calculator<br>(IS 17452:2020)</h1>', unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
This calculator implements the mix design methodology for alkali-activated concrete according to IS 17452:2020. Enter your design parameters below to generate a comprehensive mix design.
</div>
""", unsafe_allow_html=True)

# Main content in tabs
tab1, tab2 = st.tabs(["Mix Design Calculator", "Technical Information"])

with tab1:
    # Target Properties
    st.markdown('<h2 class="section-header">Target Properties</h2>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        target_strength = st.number_input("Target Compressive Strength (MPa)", 
                                         min_value=20, max_value=80, value=40, 
                                         help="Specify the required 28-day compressive strength")
    
    # Precursor Materials
    st.markdown('<h2 class="section-header">Precursor Materials</h2>', unsafe_allow_html=True)
    
    # Create tabs for precursor configuration
    precursor_tabs = st.tabs(["Fly Ash", "GGBFS", "Metakaolin", "Silica Fume"])
    
    # Initialize precursors dictionary
    precursors = {
        'Fly Ash': {'percentage': 0, 'sg': 2.2},
        'GGBFS': {'percentage': 0, 'sg': 2.9},
        'Metakaolin': {'percentage': 0, 'sg': 2.6},
        'Silica Fume': {'percentage': 0, 'sg': 2.2}
    }
    
    # Fly Ash configuration
    with precursor_tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            precursors['Fly Ash']['percentage'] = st.number_input("Fly Ash Percentage", 
                                                               min_value=0, max_value=100, value=70,
                                                               help="Percentage of fly ash in the total binder")
        with col2:
            precursors['Fly Ash']['sg'] = st.number_input("Fly Ash Specific Gravity", 
                                                       min_value=2.0, max_value=3.0, value=2.2, step=0.1,
                                                       help="Specific gravity of fly ash")
    
    # GGBFS configuration
    with precursor_tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            precursors['GGBFS']['percentage'] = st.number_input("GGBFS Percentage", 
                                                             min_value=0, max_value=100, value=30,
                                                             help="Percentage of GGBFS in the total binder")
        with col2:
            precursors['GGBFS']['sg'] = st.number_input("GGBFS Specific Gravity", 
                                                     min_value=2.0, max_value=3.5, value=2.9, step=0.1,
                                                     help="Specific gravity of GGBFS")
    
    # Metakaolin configuration
    with precursor_tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            precursors['Metakaolin']['percentage'] = st.number_input("Metakaolin Percentage", 
                                                                  min_value=0, max_value=100, value=0,
                                                                  help="Percentage of metakaolin in the total binder")
        with col2:
            precursors['Metakaolin']['sg'] = st.number_input("Metakaolin Specific Gravity", 
                                                          min_value=2.0, max_value=3.0, value=2.6, step=0.1,
                                                          help="Specific gravity of metakaolin")
    
    # Silica Fume configuration
    with precursor_tabs[3]:
        col1, col2 = st.columns(2)
        with col1:
            precursors['Silica Fume']['percentage'] = st.number_input("Silica Fume Percentage", 
                                                                   min_value=0, max_value=100, value=0,
                                                                   help="Percentage of silica fume in the total binder")
        with col2:
            precursors['Silica Fume']['sg'] = st.number_input("Silica Fume Specific Gravity", 
                                                           min_value=2.0, max_value=3.0, value=2.2, step=0.1,
                                                           help="Specific gravity of silica fume")
    
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
        st.markdown("#### Sodium Silicate Composition")
        
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
        
        ss_sum = sio2 + na2o + h2o
        if abs(ss_sum - 100) > 0.1:
            st.markdown(f"""
            <div class="warning-box">
            <strong>Warning:</strong> Sodium silicate composition must sum to 100%. Current sum is {ss_sum}%.
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            ss_sg = st.number_input("Sodium Silicate Specific Gravity", 
                                  min_value=1.3, max_value=1.8, value=1.5, step=0.1,
                                  help="Specific gravity of sodium silicate solution")
        
        activators['Sodium Silicate'] = {
            'sio2': sio2,
            'na2o': na2o,
            'h2o': h2o,
            'sg': ss_sg
        }
        
        if sio2 > 0 and na2o > 0:
            modulus = sio2 / na2o
            st.markdown(f"**Activator Modulus (SiO₂/Na₂O): {modulus:.2f}**")
            
            if modulus < 0.6 or modulus > 2.0:
                st.markdown(f"""
                <div class="warning-box">
                <strong>Warning:</strong> Activator modulus is outside the recommended range (0.6-2.0) as per IS 17452:2020.
                </div>
                """, unsafe_allow_html=True)
    
    # Sodium Hydroxide
    use_sodium_hydroxide = st.checkbox("Use Sodium Hydroxide", value=True)
    if use_sodium_hydroxide:
        col1, col2 = st.columns(2)
        with col1:
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
                
                # Create visualization of mix proportions
                st.markdown("### Material Proportions by Weight")
                
                # Calculate percentages
                total_weight = mix_design['concrete_density']
                
                chart_data = []
                
                # Add binder materials
                for name, quantity in mix_design['binder_quantities'].items():
                    chart_data.append({
                        'Material': name,
                        'Category': 'Binder',
                        'Percentage': quantity / total_weight * 100
                    })
                
                # Add activators
                for name, quantity in mix_design['activator_quantities'].items():
                    chart_data.append({
                        'Material': name,
                        'Category': 'Activator',
                        'Percentage': quantity / total_weight * 100
                    })
                
                # Add extra water if any
                if mix_design['extra_water'] > 0:
                    chart_data.append({
                        'Material': 'Additional Water',
                        'Category': 'Water',
                        'Percentage': mix_design['extra_water'] / total_weight * 100
                    })
                
                # Add aggregates
                chart_data.append({
                    'Material': 'Fine Aggregate',
                    'Category': 'Aggregate',
                    'Percentage': mix_design['fine_aggregate'] / total_weight * 100
                })
                
                chart_data.append({
                    'Material': 'Coarse Aggregate',
                    'Category': 'Aggregate',
                    'Percentage': mix_design['coarse_aggregate'] / total_weight * 100
                })
                
                # Create DataFrame for chart
                chart_df = pd.DataFrame(chart_data)
                
                # Create pie chart
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.pie(chart_df['Percentage'], labels=chart_df['Material'], autopct='%1.1f%%', shadow=False, startangle=90)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                
                st.pyplot(fig)
                
                # Material distribution by category
                st.markdown("### Material Distribution by Category")
                
                # Group by category
                category_data = chart_df.groupby('Category')['Percentage'].sum().reset_index()
                
                # Create bar chart using Altair
                category_chart = alt.Chart(category_data).mark_bar().encode(
                    x=alt.X('Category:N', sort=None, title='Material Category'),
                    y=alt.Y('Percentage:Q', title='Percentage by Weight (%)'),
                    color=alt.Color('Category:N', legend=None),
                    tooltip=['Category', 'Percentage']
                ).properties(
                    width=600,
                    height=400,
                    title='Material Distribution by Category (%)'
                )
                
                st.altair_chart(category_chart, use_container_width=True)
                
                # Download link for mix design report
                st.markdown("### Download Mix Design Report")
                
                # Create report content
                report_content = f"""# Geopolymer Concrete Mix Design Report (IS 17452:2020)

## Design Parameters
- Target Compressive Strength: {target_strength} MPa
- Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}

## Material Quantities (kg/m³)

### Binder Materials
"""
                
                for name, quantity in mix_design['binder_quantities'].items():
                    report_content += f"- {name}: {quantity:.1f} kg/m³\n"
                
                report_content += f"\nTotal Binder: {mix_design['total_binder']:.1f} kg/m³\n\n"
                
                report_content += "### Alkaline Activators\n"
                for name, quantity in mix_design['activator_quantities'].items():
                    report_content += f"- {name}: {quantity:.1f} kg/m³\n"
                
                report_content += f"\nTotal Activator: {mix_design['total_activator']:.1f} kg/m³\n\n"
                
                if mix_design['extra_water'] > 0:
                    report_content += f"### Additional Water\n- Extra Water: {mix_design['extra_water']:.1f} kg/m³\n\n"
                
                report_content += f"### Aggregates\n- Fine Aggregate: {mix_design['fine_aggregate']:.1f} kg/m³\n- Coarse Aggregate: {mix_design['coarse_aggregate']:.1f} kg/m³\n\n"
                
                report_content += f"## Concrete Properties\n- Estimated Concrete Density: {mix_design['concrete_density']:.1f} kg/m³\n- Water to Geopolymer Solids Ratio: {mix_design['water_geopolymer_solids_ratio']:.3f}\n\n"
                
                report_content += "## Mix Ratio (by weight)\n"
                mr = mix_design['mix_ratio']
                report_content += f"Binder : Activator : Fine Agg : Coarse Agg = 1 : {mr['activator']:.2f} : {mr['fine_agg']:.2f} : {mr['coarse_agg']:.2f}\n\n"
                
                report_content += "## Notes\n- This mix design follows the guidelines of IS 17452:2020.\n"
                report_content += "- Actual performance may vary based on material properties, mixing procedures, and curing conditions.\n"
                report_content += "- Laboratory trials are recommended before field application.\n"
                
                st.download_button(
                    label="Download Mix Design Report",
                    data=report_content,
                    file_name="geopolymer_mix_design.md",
                    mime="text/markdown"
                )

with tab2:
    st.markdown("## Technical Information on Geopolymer Concrete")
    
    st.markdown("""
    ### Key Components of Geopolymer Concrete
    
    **Precursor Materials:**
    - **Fly Ash:** A coal combustion by-product rich in aluminosilicates, typically Class F (low calcium) fly ash is preferred for geopolymer concrete.
    - **GGBFS (Ground Granulated Blast Furnace Slag):** A by-product from the iron and steel industry, high in calcium content. It accelerates setting time and improves early strength.
    - **Metakaolin:** Produced by calcining kaolin clay, it has high reactivity and produces geopolymers with excellent mechanical properties.
    - **Silica Fume:** An ultrafine by-product of silicon production, used to enhance mechanical properties and reduce permeability.
    
    **Alkaline Activators:**
    - **Sodium Silicate (Na₂SiO₃):** Provides soluble silica for the geopolymerization reaction and influences the SiO₂/Al₂O₃ ratio.
    - **Sodium Hydroxide (NaOH):** Dissolves the aluminosilicate precursors, enabling them to recombine into the geopolymer network.
    
    ### Mix Design Principles
    
    **Key Parameters Affecting Strength:**
    1. **Activator-to-Binder Ratio:** Similar to water-cement ratio in OPC concrete, this ratio influences the strength and workability of geopolymer concrete.
    2. **Na₂SiO₃/NaOH Ratio:** Typically varies between 1.0 and 2.5, with higher ratios generally providing better strength.
    3. **Alkali Concentration:** NaOH molarity typically ranges from 8M to 14M, with higher concentrations providing higher strength but potentially reducing workability.
    4. **Water-to-Geopolymer Solids Ratio:** Considers the total water content (from activator solutions and added water) relative to the total solids content (precursors and dissolved solids in activators).
    
    ### Curing Requirements
    
    Geopolymer concrete typically requires specific curing conditions for optimal strength development:
    
    1. **Heat Curing:** Often required for fly ash-based geopolymers, typically at 60-90°C for 24-48 hours.
    2. **Ambient Curing:** Possible for GGBFS-rich or hybrid mixtures, but strength development may be slower.
    3. **Sealed Curing:** Essential to prevent water evaporation during the geopolymerization process.
    
    ### Standards and Guidelines
    
    - **IS 17452:2020:** Indian Standard for Use of Alkali Activated Concrete for Precast Products
    - **RILEM TC 224-AAM:** Technical Committee on Alkali-Activated Materials
    - **ACI Committee 232:** Developing guidelines for geopolymer concrete
    
    ### Environmental Benefits
    
    - **CO₂ Reduction:** Up to 80% reduction compared to OPC concrete
    - **Industrial By-product Utilization:** Repurposes waste materials that might otherwise be landfilled
    - **Energy Savings:** Lower energy requirement during production compared to OPC
    
    ### Limitations and Challenges
    
    1. **Material Variability:** Inconsistent properties of industrial by-products
    2. **Handling of Alkaline Solutions:** Safety concerns with handling strong alkalis
    3. **Curing Requirements:** May require elevated temperature curing
    4. **Standardization:** Limited standards and guidelines for mix design and quality control
    """)

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 40px; padding: 20px; background-color: #f0f2f6; border-radius: 5px;">
<p style="margin-bottom: 5px;">Geopolymer Concrete Mix Design Calculator based on IS 17452:2020</p>
<p style="font-size: 0.8em; color: #666;">Disclaimer: This calculator is provided for educational and research purposes only. Users should validate the results through laboratory testing before application in construction projects.</p>
</div>
""", unsafe_allow_html=True)
