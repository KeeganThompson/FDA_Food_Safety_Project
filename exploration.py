import os
import glob
import json
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = './data'
EXPLORE_DIR = './exploration'

# Ensure the exploration output directory exists
if not os.path.exists(EXPLORE_DIR):
    os.makedirs(EXPLORE_DIR)

def explore_data(sample_size=5):
    """
    Reads a small sample of JSON files to explore the schema and data completeness.
    """
    print(f"Gathering a sample of up to {sample_size} files for exploration...\n")
    
    files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    if not files:
        print("No JSON files found in ./data! Please run part1.js first.")
        return

    sample_files = files[:sample_size]
    all_records = []

    # 1. Load the sample records
    for filepath in sample_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Handle both naked arrays and openFDA's typical {"results": [...]} wrapper
                records = data if isinstance(data, list) else data.get('results', [])
                all_records.extend(records)
            except json.JSONDecodeError:
                print(f"Could not read {filepath}")

    print(f"Successfully loaded {len(all_records)} sample records.\n")

    # 2. Print the raw schema of the very first record
    if all_records:
        print("--- SCHEMA OF A SINGLE RECORD ---")
        # We use json.dumps with indent=2 to pretty-print the dictionary
        print(json.dumps(all_records[0], indent=2))
        print("---------------------------------\n")

    # 3. Flatten the data to analyze completeness (how much data is missing?)
    # We will extract the exact paths we know we need for Part 2
    flattened_data = []
    for r in all_records:
        flat_record = {
            'has_date_started': 1 if r.get('date_started') else 0,
            'has_date_created': 1 if r.get('date_created') else 0,
            'has_outcomes': 1 if r.get('outcomes') else 0,
            'has_reactions': 1 if r.get('reactions') else 0,
            
            # Consumer is a nested dictionary
            'has_consumer_age': 1 if r.get('consumer', {}).get('age') else 0,
            'has_consumer_gender': 1 if r.get('consumer', {}).get('gender') else 0,
            
            # Products is a list of dictionaries
            'has_products': 1 if r.get('products') else 0,
        }
        flattened_data.append(flat_record)

    df = pd.DataFrame(flattened_data)

    # 4. Calculate the percentage of records that actually have these fields
    completeness = (df.sum() / len(df)) * 100

    # 5. Generate and save a Data Completeness Chart
    plt.figure(figsize=(10, 6))
    completeness.sort_values().plot(kind='barh', color='skyblue', edgecolor='black')
    
    plt.title('Data Completeness: Percentage of Records with Field Populated')
    plt.xlabel('Percentage (%)')
    plt.ylabel('Field')
    plt.xlim(0, 100)
    
    # Add the exact percentage text to the end of each bar
    for index, value in enumerate(completeness.sort_values()):
        plt.text(value + 1, index, f'{value:.1f}%', va='center')

    plt.tight_layout()
    chart_path = os.path.join(EXPLORE_DIR, 'data_completeness.png')
    plt.savefig(chart_path)
    
    print(f"✅ Data completeness chart saved to: {chart_path}")

if __name__ == "__main__":
    explore_data()