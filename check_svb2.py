import edgar
edgar.set_identity('Unsaid/1.0 tobiojebiyi@gmail.com')
entity = edgar.get_entity(719739)
filings = entity.get_filings(form='10-K')
f2021 = next(f for f in filings if str(f.period_of_report).startswith('2021'))
f2022 = next(f for f in filings if str(f.period_of_report).startswith('2022'))

item7a_2021 = str(f2021.obj()['Item 7A'])
item7a_2022 = str(f2022.obj()['Item 7A'])

print("=== FULL FY2021 Item 7A ===")
print(item7a_2021)
print()
print("=== FULL FY2022 Item 7A ===")
print(item7a_2022)
