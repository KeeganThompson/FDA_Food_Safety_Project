import sys
import re
from datetime import datetime
import os
import glob
from collections import Counter
import json

DATA_DIR = './data'

def process_data():
    start_year, end_year, product_filter = parse_arguments()

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
            data = json.load(f)
            records = data['results']
            for record in records:
                year = int(record['date_started'][:4])
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

    # Strip not A-Z, 0-9, or space
    text = re.sub(r'[^A-Z0-9 ]', ' ', text)

    # Collapse mult spaces
    text = re.sub(r'\s+', ' ', text)

    # Probable Dupes
    text = re.sub(r'\bVITAMIN D3\b', 'VITAMIN D', text)
    text = re.sub(r'\bVITAMINS\b', 'VITAMIN', text)
    text = re.sub(r'\bMULTIVITAMINS\b', 'MULTIVITAMIN', text)
    text = re.sub(r'\bMULTI VITAMIN\b', 'MULTIVITAMIN', text)
    text = re.sub(r'\bOMEGA 3\b', 'OMEGA3', text)
    return text.strip()

# fractional age
def parse_age(age_val, unit):
    try:
        val = float(age_val)
        unit = str(unit).lower()

        if 'year' in unit: return val
        if 'month' in unit: return val / 12
        if 'week' in unit: return val / 52.14
        if 'day' in unit: return val /365.25
        if 'decade' in unit: return val * 10

        # if blank but num 0-120, probably years
        if not unit or unit == 'none':
            if 0 <= val <= 120:
                return val
        return None
    except (ValueError, TypeError):
        return None

if __name__ == "__main__":
    print("--- Text Cleaning Test ---")
    print(f"Raw: '  Vitamin   D3, (liquid) ' -> Cleaned: '{clean_text('  Vitamin   D3, (liquid) ')}'")
    print(f"Raw: 'ICE-CREAM!!!' -> Cleaned: '{clean_text('ICE-CREAM!!!')}'")
    
    print("\n--- Age Parsing Test ---")
    print(f"18 Year(s) -> {parse_age('18', 'Year(s)')} years")
    print(f"6 Month(s) -> {parse_age('6', 'Month(s)')} years")
    print(f"900 Day(s) -> {parse_age('900', 'Day(s)'):.2f} years")