import sys, csv, html
fn = sys.argv[1]; want = set(sys.argv[2].split(',')); full = len(sys.argv) > 3
csv.field_size_limit(10**9)
with open(fn, encoding='utf-8', errors='replace', newline='') as fh:
    next(fh)
    for row in csv.DictReader(fh):
        k = row['Mnemonic'] + row['Item Code']
        if k in want:
            print(k, '|', row['Start Date'].split(' ')[0], '|', row['End Date'].split(' ')[0], '|', row['Item Name'], '|', row['Reporting Form'], '|', row['Confidentiality'])
            if full: print('   DESC:', html.unescape(row['Description']).replace('\r', ' ').replace('\n', ' ')[:1500])
