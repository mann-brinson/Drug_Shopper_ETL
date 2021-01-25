from lxml import etree
import time
import json

def extract_drugs(drugbank_file, j_prods, k_intrx):
    '''From the big DrugBank data-dump xml file, extract all drugs, their products, and interactions.
    drugbank_file - the big 1.45GB data dump file from drugbank.
    j_prods - a filtering number of products per drug
    k_intrx - a filtered number of interactions per drug
    '''
    start = time.time()
    context = etree.iterparse(drugbank_file, events=('start', 'end'), attribute_defaults=True)
    end = time.time()
    print('context read time: ', end-start)

    output_file = 'drugbank_data.jl'
    # output_file = 'drugbank_drug.jl'
    fd = open(output_file, "w")
    
    start = time.time()
    for event, elem in context:
    
        #Find the drug header
        items = elem.items()
        if event == 'end' and len(items) > 0 and elem.tag == '{http://www.drugbank.ca}drug':

            if items[0][1] in ['biotech', 'small molecule']:
                drug_name = elem.findtext('{http://www.drugbank.ca}name') #Name

                drug_ids = elem.findall('{http://www.drugbank.ca}drugbank-id') #Drugbank_id
                for did in drug_ids:
                    attrs = did.items()
                    if len(did.items()) > 0:
                        if did.items()[0][1] == 'true':
                            drug_ent = {drug_name: {'drugbank_id': did.text}}
                            break

                products = elem.findall('{http://www.drugbank.ca}products') #Products
                prods = products[0].getchildren()

                if len(prods) > 0:
                    drug_ent[drug_name]['products'] = dict()
                    
                    if j_prods > len(prods): n_iters = range(len(prods))
                    else: n_iters = range(j_prods)
                    
                    for i in n_iters:
                        prod_name = prods[i].findtext('{http://www.drugbank.ca}name')
                        prod_labeller = prods[i].findtext('{http://www.drugbank.ca}labeller')
                        if prod_name not in drug_ent[drug_name]['products']:
                            drug_ent[drug_name]['products'][prod_name] = {prod_labeller}
                        else:
                            drug_ent[drug_name]['products'][prod_name].add(prod_labeller)

                    for prod_name in drug_ent[drug_name]['products']:
                        drug_ent[drug_name]['products'][prod_name] = list(drug_ent[drug_name]['products'][prod_name])

                intrx = elem.findall('{http://www.drugbank.ca}drug-interactions') #Interactions
                intrx_children = intrx[0].getchildren()
                if len(intrx_children) > 0:
                    drug_ent[drug_name]['interactions'] = dict()

                    if k_intrx > len(intrx_children): n_iters = range(len(intrx_children))
                    else: n_iters = range(k_intrx)

                    for i in n_iters:
                        intrx_drug = intrx_children[i].findtext('{http://www.drugbank.ca}name')
                        intrx_dbid = intrx_children[i].findtext('{http://www.drugbank.ca}drugbank-id')
                        drug_ent[drug_name]['interactions'][intrx_dbid] = intrx_drug

                data = json.dumps(drug_ent, ensure_ascii=False)
                fd.write(data)
                fd.write('\n')
            elem.clear(keep_tail=True)
    fd.close()
    end = time.time()
    print('extract time: ', end-start)

#DRIVER
j_prods = 20 #number products per drug
k_intrx = 100 #number interactions per drug

drugbank_file = 'full database.xml'
extract_drugs(drugbank_file, j_prods, k_intrx)