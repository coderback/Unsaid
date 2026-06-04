import edgar
edgar.set_identity('Unsaid/1.0 tobiojebiyi@gmail.com')
entity = edgar.get_entity(719739)
filings = entity.get_filings(form='10-K')
f2021 = next(f for f in filings if str(f.period_of_report).startswith('2021'))
f2022 = next(f for f in filings if str(f.period_of_report).startswith('2022'))

item7a_2021 = str(f2021.obj()['Item 7A'])
item7a_2022 = str(f2022.obj()['Item 7A'])

print("FY2021 Item 7A length:", len(item7a_2021))
print("FY2022 Item 7A length:", len(item7a_2022))

# Check for EVE sensitivity / quantitative data
keywords_2021 = {}
for kw in ['5.7', 'basis point', '+200', 'sensitivity', 'EVE', 'last-of-layer', 'hedge', 'terminated']:
    keywords_2021[kw] = kw.lower() in item7a_2021.lower()

keywords_2022 = {}
for kw in ['5.7', 'basis point', '+200', 'sensitivity', 'EVE', 'last-of-layer', 'hedge', 'terminated']:
    keywords_2022[kw] = kw.lower() in item7a_2022.lower()

print("\nKeyword presence:")
print(f"{'Keyword':<20} {'FY2021':>8} {'FY2022':>8}")
for kw in keywords_2021:
    print(f"{kw:<20} {str(keywords_2021[kw]):>8} {str(keywords_2022[kw]):>8}")

print("\n=== FY2021 Item 7A (first 2000 chars) ===")
print(item7a_2021[:2000])
print("\n=== FY2022 Item 7A (first 2000 chars) ===")
print(item7a_2022[:2000])
