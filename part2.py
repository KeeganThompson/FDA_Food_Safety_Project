import sys
import re
import os
import glob
import json
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime
DATA_DIR = './data'

def process_data():
    start_year, end_year, product_filter = parse_arguments()

    if product_filter:
        product_filter = clean_text(product_filter)

    print(f"Processing data from {start_year} to {end_year} with product filter: {product_filter}")

    files = glob.glob(os.path.join(DATA_DIR, '*json'))
    if not files:
        print(f"No JSON files found in {DATA_DIR}.")
        sys.exit(1)

    # Counters
    filtered_records_count = 0
    yearly_counts = Counter()
    outcomes_counter = Counter()
    reactions_counter = Counter()
    suspect_products_counter = Counter()

    ages_total = []
    ages_female = []
    ages_male = []

    # Parse
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Skipping corrupted file {filepath}")
                continue
            records = data if isinstance(data, list) else data.get('results', [])
            for record in records:
                date_string = record.get('date_started') or record.get('date_created') or ""
                if len(date_string) >= 4 and date_string[:4].isdigit():
                    year = int(date_string[:4])
                else:
                    continue
                if not (start_year <= year <= end_year):
                    continue

                suspect_names = []
                match_found = product_filter is None

                # find suspects in products and check filter
                for p in record['products']:
                    if p['role'] == 'SUSPECT':
                        name = clean_text(p['name_brand'])
                        suspect_names.append(name)
                        if product_filter and product_filter in name:
                            match_found = True

                if not match_found:
                    continue

                # Match, log
                filtered_records_count += 1
                yearly_counts[year] += 1

                for name in suspect_names:
                    suspect_products_counter[name] += 1
                for outcome in record['outcomes']:
                    outcomes_counter[clean_text(outcome)] += 1
                for reaction in record['reactions']:
                    reactions_counter[clean_text(reaction)] += 1

                # Consumer or inner fields might not exist
                consumer = record.get('consumer', {})
                age_val = consumer.get('age')
                age_unit = consumer.get('age_unit')
                gender = str(consumer.get('gender', '')).upper()

                if age_val:
                    age_years = parse_age(age_val, age_unit)
                    if age_years is not None and 0 <= age_years <= 120:
                        ages_total.append(age_years)
                        if gender == 'FEMALE':
                            ages_female.append(age_years)
                        if gender == 'MALE':
                            ages_male.append(age_years)
    # return everything
    return {
        "count": filtered_records_count,
        "yearly_counts": yearly_counts,
        "outcomes": outcomes_counter,
        "reactions": reactions_counter,
        "products": suspect_products_counter,
        "ages": ages_total,
        "ages_f": ages_female,
        "ages_m": ages_male
    }


# out and vis
CHARTS_DIR = './charts'

def output_and_visualize(data_dict, start_year, end_year, product_filter):
    if data_dict["count"] == 0:
        print("No records matched")
        sys.exit(0)

    print(f"\nTotal Matching Records: {data_dict['count']:,}\n")

    avg_total = np.mean(data_dict["ages"]) if data_dict["ages"] else 0
    avg_female = np.mean(data_dict["ages_f"]) if data_dict["ages_f"] else 0
    avg_male = np.mean(data_dict["ages_m"]) if data_dict["ages_m"] else 0

    print(f"Average Age (Total):  {avg_total:.1f} years")
    print(f"Average Age (Female): {avg_female:.1f} years")
    print(f"Average Age (Male):   {avg_male:.1f} years\n")

    print(" TOP 25 OUTCOMES ")
    for term, count in data_dict["outcomes"].most_common(25):
        print(f"  {count:<6} {term}")

    print("\n TOP 25 REACTIONS ")
    for term, count in data_dict["reactions"].most_common(25):
        print(f"  {count:<6} {term}")

    print("\n TOP 25 SUSPECT PRODUCTS ")
    for term, count in data_dict["products"].most_common(25):
        print(f"  {count:<6} {term}")

    # Vis
    if not os.path.exists(CHARTS_DIR):
        os.makedirs(CHARTS_DIR)

    # 1x2 chart layout
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    filter_text = product_filter if product_filter else 'All Products'
    fig.suptitle(f"FDA Adverse Events Analysis\n({start_year}-{end_year}) - {filter_text}", fontsize=14)

    # Plot 1 -- Total Cases by Year
    if data_dict["yearly_counts"]:
        years, counts = zip(*sorted(data_dict["yearly_counts"].items()))
        ax1.bar(years, counts, color='steelblue', edgecolor='black')
        ax1.set_title("Total Cases By Year")
        ax1.set_xlabel("Year")
        ax1.set_ylabel("Number Of Cases")
        ax1.set_xticks(years)
        ax1.tick_params(axis='x', rotation = 45)

    # Plot 2: Histogram of Consumer Ages
    if data_dict["ages"]:
        # every age year in dataset
        ax2.hist(data_dict["ages"], bins=range(0, 122, 1), color='salmon', edgecolor='black', alpha=0.7)
        ax2.set_title("Distribution of Consumer Ages")
        ax2.set_xlabel("Age (Years)")
        ax2.set_ylabel("Frequency")
    else:
        ax2.text(0.5, 0.5, 'No Age Data Available', ha='center', va='center')

    plt.tight_layout()
    timestamp = datetime.now().strftime('%Y%m%d_%H%H%S')
    chart_path = os.path.join(CHARTS_DIR, f"{timestamp}.png")
    plt.savefig(chart_path)

    print("Visualization saved to {chart_path}")


# flexible CLI arguments, 4-dig years for range and rest into product filter
def parse_arguments():
    # command line args, skip part2.py
    args = sys.argv[1:]

    years = []
    product_parts = []

    for arg in args:
        # does string start and end w 4 digits
        if re.match(r'^\d{4}$', arg):
            years.append(int(arg))
        else:
            product_parts.append(arg)

    years = sorted(years)
    product_filter = " ".join(product_parts).upper() if product_parts else None
    current_year = datetime.now().year

    if len(years) == 0:
        start_year, end_year = 2002, current_year
    elif len(years) == 1:
        start_year, end_year = years[0], current_year
    else:
        start_year, end_year = years[0], years[1]

    return start_year, end_year, product_filter

# Normalize text -- No punctuation, standard whitespaces, dupes
def clean_text(text):
    if not isinstance(text, str):
        return ""

    # Upper abd no lead/trail whitespace
    text = text.upper().strip()

    # Apostrophes leave no space
    text = text.replace("'", "").replace("`", "").replace("’", "")

    # Strip not A-Z, 0-9, or space
    text = re.sub(r'[^A-Z0-9 ]', ' ', text)

    # Collapse mult spaces
    text = re.sub(r'\s+', ' ', text)

    # Dupe Handling
    text = re.sub(r'\bDIARRHOEA\b', 'DIARRHEA', text)
    text = re.sub(r'\bHAEMORRHAGE\b', 'HEMORRHAGE', text)
    text = re.sub(r'\bVITAMIN D3\b', 'VITAMIN D', text)
    text = re.sub(r'\bVITAMINS\b', 'VITAMIN', text)
    text = re.sub(r'\bMULTIVITAMINS\b', 'MULTIVITAMIN', text)
    text = re.sub(r'\bMULTI VITAMIN\b', 'MULTIVITAMIN', text)
    text = re.sub(r'\bOMEGA 3\b', 'OMEGA3', text)
    text = re.sub(r'\bHOSPITALISATION\b', 'HOSPITALIZATION', text)
    text = re.sub(r'\bEMERGENCY CARE\b', 'VISITED EMERGENCY ROOM', text)
    return text.strip()

# fractional age
def parse_age(age_val, unit):
    try:
        val = float(age_val)
        unit = str(unit).lower()

        # filter out missing unites or 0 years exact
        if val == 0 and ('year' in unit or not unit or unit == 'none'):
            return None

        if 'year' in unit: return val
        if 'month' in unit: return val / 12
        if 'week' in unit: return val / 52.14
        if 'day' in unit: return val /365.25
        if 'decade' in unit: return val * 10

        # if blank but num 0-120, probably years
        if not unit or unit == 'none':
            if 0 < val <= 120:
                return val
        return None
    except (ValueError, TypeError):
        return None

if __name__ == "__main__":
    # 1. Parse user inputs
    start_y, end_y, prod_filter = parse_arguments()
    
    # 2. Extract and count data (Step 3)
    results_dict = process_data()
    
    # 3. Output stats and charts (Step 4)
    output_and_visualize(results_dict, start_y, end_y, prod_filter)