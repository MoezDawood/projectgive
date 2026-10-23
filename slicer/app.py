# BSD 3-Clause License

# Copyright (c) 2024, MoezDawood

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#streamlitwgstest60.py

import streamlit as st
import pandas as pd
from datetime import datetime
import re
import time
import os
import base64
import zipfile
import json
import glob

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("SLICER_DATA_DIR", APP_DIR)
STATE_DIR = os.environ.get("SLICER_STATE_DIR", os.path.join(APP_DIR, "state"))
os.makedirs(STATE_DIR, exist_ok=True)

# Set page configuration to wide mode
st.set_page_config(layout="wide")

# Function to list local CSV files in the script directory
def list_csv_files_in_directory(directory):
    try:
        files = os.listdir(directory)
        # Filter files to only include local data CSVs. annotatedcsvheaders.csv powers the UI.
        csv_files = [
            file for file in files
            if file.endswith('.csv')
            and file != "annotatedcsvheaders.csv"
            and os.path.isfile(os.path.join(directory, file))
        ]
        csv_files.sort()
        return csv_files
    except Exception as e:
        st.error(f"Failed to list CSV files: {e}")
        return None

def validate_input(value, expected_type):
    if expected_type == 'int':
        try:
            int(value)
            return True
        except ValueError:
            return False
    elif expected_type == 'float':
        try:
            float(value)
            return True
        except ValueError:
            return False
    elif expected_type == 'str':
        return isinstance(value, str)
    return False

def serve_file_for_download(local_path, label="Download ZIP file"):
    """Serve the file for automatic download."""
    with open(local_path, 'rb') as f:
        data = f.read()
        b64 = base64.b64encode(data).decode('utf-8')
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(local_path)}">{label}</a>'
        st.markdown(href, unsafe_allow_html=True)

def create_combined_zip(file_paths, zip_name):
    """Create a combined ZIP file from multiple individual ZIP files."""
    with zipfile.ZipFile(zip_name, 'w') as combined_zip:
        for file_path in file_paths:
            if os.path.exists(file_path):
                combined_zip.write(file_path, os.path.basename(file_path))
    return zip_name

def apply_filters_to_dataframe(df, fields, field_types):
    """Apply selected Streamlit filters to a dataframe."""
    filtered_df = df.copy()

    for field_data in fields:
        field = field_data.get('field')
        if not field or field not in filtered_df.columns:
            continue

        if field_data.get('is_multi_value', False) and field.lower() == 'hugo':
            gene_list = field_data.get('gene_list', [])
            if gene_list:
                mask = pd.Series(False, index=filtered_df.index)
                for gene in gene_list:
                    mask = mask | filtered_df[field].astype(str).str.contains(gene, na=False, regex=False)
                filtered_df = filtered_df[mask]
            continue

        value = field_data.get('value')
        operator = field_data.get('operator')
        if value in (None, "") or not operator:
            continue

        field_type = field_types.get(field, 'str')
        if field_type in ['int', 'float']:
            numeric_series = pd.to_numeric(filtered_df[field], errors='coerce')
            comparison_value = float(value) if field_type == 'float' else int(value)

            if operator == 'greater than':
                filtered_df = filtered_df[numeric_series > comparison_value]
            elif operator == 'less than':
                filtered_df = filtered_df[numeric_series < comparison_value]
            elif operator == 'equal to':
                filtered_df = filtered_df[numeric_series == comparison_value]
        else:
            text_series = filtered_df[field].astype(str)
            if operator == 'contains':
                filtered_df = filtered_df[text_series.str.contains(value, na=False, regex=False)]
            elif operator == 'does not contain':
                filtered_df = filtered_df[~text_series.str.contains(value, na=False, regex=False)]

    return filtered_df

def process_local_csv_file(input_path, output_directory, fields, field_types):
    """Filter a local CSV file and package the filtered CSV plus summary as a ZIP."""
    os.makedirs(output_directory, exist_ok=True)

    input_filename = os.path.basename(input_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = f"{timestamp}_{input_filename.replace('.csv', '')}_filtered"
    csvfile_path = os.path.join(output_directory, f"{output_base}.csv")
    txtfile_path = os.path.join(output_directory, f"{output_base}_summary.txt")
    zipfile_path = os.path.join(output_directory, f"{output_base}.zip")

    df = pd.read_csv(input_path)
    filtered_df = apply_filters_to_dataframe(df, fields, field_types)
    filtered_df.to_csv(csvfile_path, index=False)

    variant_count = len(filtered_df)
    with open(txtfile_path, 'w') as summary_file:
        summary_file.write(f"Input file: {input_filename}\n")
        summary_file.write(f"Filtered variants: {variant_count}\n")
        summary_file.write(f"Created: {datetime.now().isoformat()}\n")

    with zipfile.ZipFile(zipfile_path, 'w') as result_zip:
        result_zip.write(csvfile_path, os.path.basename(csvfile_path))
        result_zip.write(txtfile_path, os.path.basename(txtfile_path))

    return {
        'csvfile_path': csvfile_path,
        'txtfile_path': txtfile_path,
        'zipfile_path': zipfile_path,
        'variant_count': variant_count,
        'status': 'success'
    }

def save_filter_set(filter_name, fields):
    """Save current filter configuration to a JSON file."""
    try:
        filename = f"SavedSlicerFilterSet_{filter_name}.json"
        filepath = os.path.join(STATE_DIR, filename)
        
        # Prepare filter data
        filter_data = {
            'filter_name': filter_name,
            'created_date': datetime.now().isoformat(),
            'fields': fields
        }
        
        # Save to JSON file
        with open(filepath, 'w') as f:
            json.dump(filter_data, f, indent=2)
        
        return True, filepath
    except Exception as e:
        return False, str(e)

def load_saved_filter_sets():
    """Load all saved filter sets from the script directory."""
    try:
        pattern = os.path.join(STATE_DIR, "SavedSlicerFilterSet_*.json")
        filter_files = glob.glob(pattern)
        
        saved_filters = {}
        for file_path in filter_files:
            try:
                with open(file_path, 'r') as f:
                    filter_data = json.load(f)
                    filter_name = filter_data.get('filter_name', os.path.basename(file_path))
                    saved_filters[filter_name] = filter_data
            except Exception as e:
                st.warning(f"Could not load filter file {os.path.basename(file_path)}: {e}")
        
        return saved_filters
    except Exception as e:
        st.error(f"Error loading saved filters: {e}")
        return {}

def load_filter_set(filter_data):
    """Load a filter set into session state."""
    if 'fields' in filter_data:
        st.session_state.fields = filter_data['fields']
        return True
    return False

def parse_gene_list(gene_input):
    """Parse gene names from various input formats."""
    if not gene_input:
        return []
    
    # Split by common delimiters and clean up
    genes = re.split(r'[,;\n\r\t]+', gene_input)
    cleaned_genes = []
    
    for gene in genes:
        gene = gene.strip()
        if gene:
            cleaned_genes.append(gene)
    
    return cleaned_genes

def format_gene_list_for_display(gene_list):
    """Format gene list for display in UI."""
    if not gene_list:
        return ""
    return ", ".join(gene_list)

# Streamlit app
def main():
    st.title("Project GIVE SLICER")
    st.write("Written by Moez Dawood (mdawood@bcm.edu)")
    st.write(
        "This Project GIVE Slicer filters OpenCRAVAT-style variant CSV files from the mounted data folder "
        f"(`{DATA_DIR}`)."
    )
    st.write("The point of this application is to allow analysts to filter and download 'slices' of WGS data. Since the number of variants in a genome (typically greater than 5 million) far exceeds the number of allowable rows (typically 1 million rows) in conventional spreadsheet softwares (eg Excel), this interface allows the user to parse the variants found in a genome down to 50,000 variants or less.")
    st.write("How to use the slicer:")
    st.write("1. Using the multi-select dropdown, choose multiple CSV files to process with the same filter criteria.")
    st.write("2. Optionally load a saved filter set, or create new filter criteria using the dropdown menus based on available annotations. To learn more about each annotation, please reference the Glossary: https://tinyurl.com/SlicerGlossary")
    st.write("3. **NEW:** For the 'hugo' field (gene names), you can now enter multiple gene names separated by commas, semicolons, or new lines. The filter will match rows containing ANY of the specified genes.")
    st.write("4. Save your filter criteria for future use with the 'Save Filters' button.")
    st.write("5. Click the Count button. This will process each selected file individually and show you how many variants would remain after implementing the set filter criteria for each file.")
    st.write("6. Download links will only show up if ALL selected files have variant counts less than 50,000.")
    st.write("7. If any file has more than 50,000 remaining variants, you will be prompted to redo the filter criteria.")
    st.write("8. If all files have less than 50,000 remaining variants, individual ZIP files for each processed file will be available for download, plus a combined ZIP file containing all results.")
    st.write("Please note counting and/or filtering may take up to a few minutes especially if the criteria does not filter out many variants.")

    temp_directory = os.path.join(DATA_DIR, "filtered_results")
    os.makedirs(temp_directory, exist_ok=True)

    # Load the annotatedcsvheaders CSV file
    try:
        csv_headers_df = pd.read_csv(os.path.join(APP_DIR, "annotatedcsvheaders.csv"))
        # Extract fields from the CSV
        csv_fields = csv_headers_df['CSVHeaders'].tolist()
        field_types = dict(zip(csv_headers_df['CSVHeaders'], csv_headers_df['Type']))
        field_descriptions = dict(zip(csv_headers_df['CSVHeaders'], csv_headers_df['BriefDescription']))
    except FileNotFoundError:
        st.error("annotatedcsvheaders.csv file not found. Please ensure it's in the same directory as this script.")
        st.stop()
    
    # Session state to keep track of fields and local results
    if 'fields' not in st.session_state:
        st.session_state.fields = []
    if 'file_results' not in st.session_state:
        st.session_state.file_results = {}
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'show_save_dialog' not in st.session_state:
        st.session_state.show_save_dialog = False

    files = list_csv_files_in_directory(DATA_DIR)
    if not files:
        st.warning(f"No data CSV files were found in `{DATA_DIR}`. Mount or copy `.csv` files into the data folder.")
        st.stop()

    st.write("You are now accessing the Project GIVE Slicer.")

    # Multi-select for CSV files
    selected_files = st.multiselect(
        "Select CSV files to process (you can select multiple files)",
        files,
        help="Start typing to search for files. All selected files will be processed with the same filter criteria.",
    )
    
    if selected_files:
        st.write(f"You selected {len(selected_files)} file(s):")
        for file in selected_files:
            st.write(f"• {file}")

        # Load saved filter sets section
        st.subheader("🔄 Load Saved Filter Set (Optional)")
        saved_filters = load_saved_filter_sets()
        
        if saved_filters:
            filter_options = [""] + list(saved_filters.keys())
            selected_filter = st.selectbox(
                "Choose a saved filter set to load:",
                options=filter_options,
                help="Select a previously saved filter configuration to automatically populate the fields below."
            )
            
            if selected_filter:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Load Selected Filter Set"):
                        if load_filter_set(saved_filters[selected_filter]):
                            st.success(f"✅ Loaded filter set: {selected_filter}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to load filter set")
                
                with col2:
                    if selected_filter in saved_filters:
                        filter_info = saved_filters[selected_filter]
                        st.info(f"📅 Created: {filter_info.get('created_date', 'Unknown')}")
                        st.info(f"🔧 Contains {len(filter_info.get('fields', []))} filter criteria")
        else:
            st.info("No saved filter sets found. Create and save filter criteria below to reuse them later.")

        # Display fields for filtering
        used_fields = [field_data['field'] for field_data in st.session_state.fields if field_data['field']]

        st.subheader("🔍 Filter Criteria (will be applied to all selected files)")
        
        for i, field_data in enumerate(st.session_state.fields):
            available_fields = [""] + [field for field in csv_fields if field not in used_fields or field == field_data['field']]
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                selected_field = st.selectbox(
                    f"Select field {i+1}",
                    options=available_fields,
                    index=available_fields.index(field_data['field']) if field_data['field'] else 0,
                    help="Select a field from the CSV file",
                    format_func=lambda x: "" if x == "" else f"{x} ({field_descriptions[x]})",
                    key=f"selectbox_{i}"
                )
            with col2:
                if selected_field:
                    field_type = field_types[selected_field]
                    
                    # Special handling for 'hugo' field
                    if selected_field.lower() == 'hugo':
                        st.write("🧬 **Multi-Gene Search**")
                        gene_input = st.text_area(
                            f"Enter gene names (one per line or separated by commas/semicolons):",
                            value=format_gene_list_for_display(field_data.get('gene_list', [])),
                            height=100,
                            key=f"hugo_input_{i}",
                            help="Enter multiple gene names like: BRCA1, BRCA2, TP53 or one per line"
                        )
                        
                        gene_list = parse_gene_list(gene_input)
                        
                        if gene_list:
                            st.write(f"**Genes to search:** {', '.join(gene_list[:5])}{'...' if len(gene_list) > 5 else ''}")
                            st.write(f"**Total genes:** {len(gene_list)}")
                        
                        # Store multi-value hugo data
                        st.session_state.fields[i] = {
                            'field': selected_field,
                            'value': gene_input,  # Store original input
                            'gene_list': gene_list,  # Store parsed list
                            'is_multi_value': True,
                            'operator': 'multi_contains',
                            'operator_index': 0
                        }
                        
                    elif field_type in ['int', 'float']:
                        value = st.text_input(
                            f"Enter value for {selected_field} ({field_type})",
                            value=field_data['value'] if field_data['value'] else "",
                            key=f"value_input_{i}"
                        )
                        operator = st.selectbox(
                            f"Select operator for {selected_field}",
                            options=['greater than', 'less than', 'equal to'],
                            index=field_data.get('operator_index', 0),
                            key=f"operator_{i}"
                        )
                        operator_index = ['greater than', 'less than', 'equal to'].index(operator)
                        
                        if value and not validate_input(value, field_type):
                            st.error(f"Invalid value for {field_type}. Please enter a valid {field_type}.")

                        st.session_state.fields[i] = {
                            'field': selected_field, 
                            'value': value, 
                            'operator': operator,
                            'operator_index': operator_index,
                            'is_multi_value': False
                        }
                    else:
                        value = st.text_input(
                            f"Enter value for {selected_field} ({field_type})",
                            value=field_data['value'] if field_data['value'] else "",
                            key=f"value_input_{i}"
                        )
                        operator = st.selectbox(
                            f"Select operator for {selected_field}",
                            options=['contains', 'does not contain'],
                            index=field_data.get('operator_index', 0),
                            key=f"operator_{i}"
                        )
                        operator_index = ['contains', 'does not contain'].index(operator)

                        if value and not validate_input(value, field_type):
                            st.error(f"Invalid value for {field_type}. Please enter a valid {field_type}.")

                        st.session_state.fields[i] = {
                            'field': selected_field, 
                            'value': value, 
                            'operator': operator,
                            'operator_index': operator_index,
                            'is_multi_value': False
                        }
            with col4:
                if st.button(f"Remove", key=f"remove_{i}"):
                    del st.session_state.fields[i]
                    st.rerun()

        # Filter management buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Add Field"):
                st.session_state.fields.append({'field': "", 'value': "", 'operator': None, 'operator_index': 0, 'is_multi_value': False})
                st.rerun()
        
        with col2:
            # Only show Save Filters button if there are active filters
            active_filters = [f for f in st.session_state.fields if f.get('field') and (f.get('value') or f.get('gene_list'))]
            if active_filters and st.button("💾 Save Filters"):
                st.session_state.show_save_dialog = True
                st.rerun()

        # Save filter dialog
        if st.session_state.show_save_dialog:
            with st.expander("💾 Save Current Filter Set", expanded=True):
                filter_name = st.text_input(
                    "Enter a name for this filter set:",
                    placeholder="e.g., BRCA_Panel_Genes",
                    help="This name will be used to identify and load this filter set later."
                )
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("Save") and filter_name:
                        # Validate filter name
                        if re.match(r'^[a-zA-Z0-9_-]+$', filter_name):
                            success, result = save_filter_set(filter_name, st.session_state.fields)
                            if success:
                                st.success(f"✅ Filter set '{filter_name}' saved successfully!")
                                st.session_state.show_save_dialog = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to save filter set: {result}")
                        else:
                            st.error("❌ Filter name can only contain letters, numbers, hyphens, and underscores.")
                
                with col2:
                    if st.button("Cancel"):
                        st.session_state.show_save_dialog = False
                        st.rerun()

        # Count variants based on filters for all selected files
        if st.button("🔢 Count Variants for All Selected Files"):
            st.session_state.file_results = {}
            st.session_state.processing_complete = False
            
            try:
                st.write(f"Processing {len(selected_files)} files with the same filter criteria...")
                
                # Process each file individually
                for idx, selected_file in enumerate(selected_files):
                    st.write(f"Processing file {idx + 1} of {len(selected_files)}: {selected_file}")
                    progress = st.progress(0)

                    input_path = os.path.join(DATA_DIR, selected_file)
                    result = process_local_csv_file(input_path, temp_directory, st.session_state.fields, field_types)

                    progress.progress(100)
                    st.session_state.file_results[selected_file] = result
                    st.write(f"✅ {selected_file}: {result['variant_count']} variants remaining")

                st.session_state.processing_complete = True

            except Exception as e:
                st.error(f"Failed to process files: {e}")

        # Display results if processing is complete
        if st.session_state.processing_complete and st.session_state.file_results:
            st.subheader("📊 Processing Results")
            
            all_under_limit = True
            successful_files = []
            
            for file_name, result in st.session_state.file_results.items():
                if result['status'] == 'success':
                    variant_count = result['variant_count']
                    if variant_count > 50000:
                        st.warning(f"🔴 {file_name}: {variant_count} variants (exceeds 50,000 limit)")
                        all_under_limit = False
                    else:
                        st.success(f"🟢 {file_name}: {variant_count} variants (within limit)")
                        successful_files.append(file_name)
                else:
                    st.error(f"❌ {file_name}: Processing failed")
                    all_under_limit = False

            if not all_under_limit:
                st.warning("⚠️ Some files exceed the 50,000 variant limit. Please adjust your filter criteria.")
            else:
                st.success("🎉 All files are within the 50,000 variant limit! Ready for download.")
                
                # Download section
                if successful_files:
                    st.subheader("📥 Download Results")
                    downloaded_files = []
                    
                    for file_name in successful_files:
                        result = st.session_state.file_results[file_name]
                        if 'zipfile_path' in result:
                            downloaded_files.append(result['zipfile_path'])
                            st.write(f"📥 Individual download for {file_name}:")
                            serve_file_for_download(result['zipfile_path'], f"Download {file_name.replace('.csv', '')}_filtered.zip")
                    
                    # Create combined ZIP file
                    if len(downloaded_files) > 1:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        combined_zip_name = f"combined_results_{timestamp}.zip"
                        combined_zip_path = os.path.join(temp_directory, combined_zip_name)
                        
                        create_combined_zip(downloaded_files, combined_zip_path)
                        st.write("📦 Combined download (all results):")
                        serve_file_for_download(combined_zip_path, f"Download {combined_zip_name}")
    else:
        st.info("Select one or more CSV files above to begin.")

if __name__ == "__main__":
    main()
