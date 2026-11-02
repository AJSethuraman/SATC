import yaml,json,sys
d=yaml.safe_load(open(sys.argv[1]))
p=d['properties']['data']['properties']
out={k:{'title':v.get('title'),'description':v.get('description'),'map':v.get('x-source-mapping')} for k,v in p.items()}
json.dump(out,open(sys.argv[2],'w'),indent=1)
print(len(out))
