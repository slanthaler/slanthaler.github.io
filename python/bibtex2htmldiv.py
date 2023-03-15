"""
Author: Samuel Lanthaler

Remark: This module is adapted from https://github.com/ketch/tex2_rst_html

Convert bibtex files (.bib) to html code that can be included in website.

Usage (from Python or IPython prompt):

    >> import bibtex2htmldiv
    >> bibtex2htmldiv.bib2html('/path/to/myfile.bib')

"""
import os
import pybtex.database
import json
import ast


def bib2html(bibfile,htmlfile='bib.html'):
    publications=parsefile(bibfile)
    writebib(publications,htmlfile)
    insert_in_indexhtml()
    
def compile_name(person):
    first = ' '.join([x.render_as('text') for x in person.rich_first_names])
    middle = ' '.join([x.render_as('text') for x in person.rich_middle_names])
    last = ' '.join([x.render_as('text') for x in person.rich_last_names])
    return first+' '+middle+' '+last

def parsefile(filename):
    """
    Takes a file name (string, including path) and returns a list of dictionaries,
    one dictionary for each bibtex entry in the file.

    Uses the bibliograph.parsing package.
    """
    with open(filename) as f:
        db = pybtex.database.parse_string(f.read(),'bibtex')
    blist = [db.entries[key] for key in db.entries.keys()]
    publications = []
    for entry in blist:
        publications.append({x:entry.fields[x] for x in entry.fields.keys()})
        publications[-1]['pid'] = entry.key
        publications[-1]['reference_type'] = entry.type
        publications[-1]['author'] = [compile_name(p) for p in entry.persons['Author']]

    # Parsing errors give strings, so keep only dicts:
    #publications=[x for x in ents if x.__class__ is dict]
    return publications

def normalize_authors(authors):
    """
    Takes the authors string from a bibtex entry and rewrites it with
    first names first.
    """
    authorlist = authors
    authornames=[]
    for author in authorlist:
        if ',' in author:
            lastname, firstname = author.split(',')
            authornames.append(firstname.strip()+' '+lastname.strip())
        else:
            authornames.append(author.strip())
    if len(authorlist)>1:
        # add " and " before last author
        authornames[-1] = 'and '+authornames[-1]
    if len(authorlist)>2:
        commasep = ', '.join(authornames[:-1])
        return ' '.join((commasep,authornames[-1]))
    else:
        return ' '.join(authornames)

def bibtexify_authors(authors):
    """
    Takes the authors string in format 
    Sam P. Lan, Hans E. Ban and Dan Can
    and converts it to
    Lan, Sam P. and Ban, Hans E. and Can, Dan
    """
    if len(authors.split('and'))<2:
        return authors
    # determine the authorlist in format firstname(s) + lastname
    commsep,last = authors.split('and')
    commsep = commsep.split(',')
    authorlist = [x.strip() for x in commsep] + [last.strip()]
    # rewrite as and-separated list of lastname, firstname(s)
    texlist = []
    for x in authorlist:
        firstnames,lastname = x.rsplit(' ',1)
        x = ', '.join((lastname,firstnames))
        texlist.append(x)
        
    return ' and '.join(texlist)

def writebib(publications,filename='bib.rst'):
    """
    Writes html citation entries.
    This only works well for articles so far; for other citation types,
    it merely writes the author, title, and year.  It should be easy to
    add better functionality for other types.
    """
    f=open(filename,'w')

    pubs = sort_by_year(publications)
    for pub in pubs:
        write_entry(pub,f)
        
#    write_section('Submitted preprints','unpublished',publications,f)
#    write_section('Refereed Journal Articles','article',publications,f)
#    write_section('Books','book',publications,f)
#    write_section('Conference Proceedings','inproceedings',publications,f)
#    write_section('Technical Reports','techreport',publications,f)
#    write_section('Theses','phdthesis',publications,f)

    f.close()


def write_section(title,reference_type,publications,f):
    """
    Write out all entries of type reference_type, in reverse chronological order
    """
    these_pubs = [pub for pub in publications if pub['reference_type']==reference_type]
    these_pubs=sort_by_year(these_pubs)
    if len(these_pubs)>0:
        f.write('<h4>'+title+'</h4>\n')
        for pub in these_pubs: write_entry(pub,f)

def write_entry(pub,f):
    pub['author'] = normalize_authors(pub['author'])

    f.write('<li>\n')
    f.write("{0}, </br> \n".format(pub['author']))
    f.write("{0}. </br>\n".format(pub['title']).replace('{','').replace('}',''))
    ### journal article
    if 'journal' in pub.keys():
        f.write("<em>{0}".format(pub['journal']))
        if 'volume' in pub.keys():
            f.write(", <strong>{0}</strong>".format(pub['volume']))
            if 'number' in pub.keys():
                f.write("({0})".format(pub['number'].lstrip("0")))
            if 'pages' in pub.keys():
                f.write(":{0}".format(pub['pages'].replace('&ndash;','-').replace('--','-')))
        f.write('</em>\n')
    #### conference proceedings
    elif (pub['reference_type'] == 'inproceedings'):
        f.write("In <em>{0}".format(pub['booktitle']))
        f.write('</em>\n')
    #### preprint article
    elif 'eprint' in pub.keys():
        f.write("<em>Preprint, arXiv:" + pub['eprint'] + "</em>")
    if pub['year'] != '':
        f.write(" ({0})".format(pub['year']))

    # Write links line
    linkstring = ''
    # add DOI
    if 'doi' in pub.keys():
        linkstring += '<a href="https://doi.org/'+pub['doi']+'" target="_blank">url</a>'
    elif 'url' in pub.keys():
        linkstring += '<a href="'+pub['url']+'" target="_blank">url</a>'
    # add PDF direct link
    if 'pdf' in pub.keys():
        if len(linkstring)>0:
            linkstring += ' | '
        linkstring += '<a href="'+pub['pdf']+'" target="_blank">pdf</a>'
    # add arXiv link
    if 'eprint' in pub.keys():
        if len(linkstring)>0:
            linkstring += ' | '
        linkstring += '<a href="http://arxiv.org/abs/'+pub['eprint']+'" target="_blank">preprint</a>'
    if len(linkstring)>0:
        # add bib to the linkstring
        linkstring += " | \n<a role=\"button\" data-bs-toggle=\"collapse\" href=\"#{0}\" aria-expanded=\"false\" aria-controls=\"{1}\">bib</a> ".format(pub['pid'],pub['pid'])
        f.write('<br>\n[\n')
        f.write(linkstring)
        f.write(']\n')

        # add the bib-entry (unfolds upon click)
        # make a and-separated list of lastname, firstname(s)
        pub['author'] = bibtexify_authors(pub['author'])
        # create entry with pybtex
        bibz = pybtex.database.Entry(
            pub['reference_type'], [
                (key,pub[key]) for key in pub.keys() if key!='reference_type' and key!='pid'
                ])
        bib_data = pybtex.database.BibliographyData({
            pub['pid']: bibz
            })
        # create html code for this entry
        bib_entry = """
	<div class="collapse" id="{0}">
	<pre>
{1}
        </pre>
        </div>
        """.format(pub['pid'], bib_data.to_string('bibtex').strip())
        f.write(bib_entry)
        
    f.write('\n</li>\n\n')

def sort_by_year(publications):
    """Takes a list of publications and return it sorted in reverse chronological order."""
    return sorted(publications, key=lambda p: p.setdefault('year',''),reverse=True)


def insert_in_indexhtml(index='index.html',bib='bib.html'):

    os.system('cp index.html index.backup')
    
    with open(index, 'r') as find:
        ind = find.read()
    with open(bib, 'r') as fbib:
        bib = fbib.read()

    start_str = '<!-- BIB START -->'
    end_str = '<!-- BIB END'
    bib_start = ind.find(start_str) + len(start_str)
    bib_end = ind.find(end_str)

    if bib_start<0 or bib_end<0:
        print('NO START STRING OR END STRING FOUND!')
        print('bib_start: ',bib_start)
        print('bib_end:   ',bib_end)
        sys.exit(1)

    ind_new = ind[:bib_start] + '\n' + '<ol reversed class="ol_refs">'
    ind_new += bib
    ind_new += '\n' + '</ol> \n' + ind[bib_end:]

    with open(index,'w') as find_new:
        find_new.write(ind_new)
