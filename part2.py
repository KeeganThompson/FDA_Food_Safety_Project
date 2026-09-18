import sys
import re
from datetime import datetime

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

if __name__ == "__main__":
    start, end, prod = parse_arguments()
    print(f"Start Year: {start}, End Year: {end}, Product Filter: {prod}")