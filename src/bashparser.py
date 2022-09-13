import re


RE_PREFIX_EXPORT = re.compile( r'^\s*(?:export)?\s*', re.IGNORECASE | re.MULTILINE )

# parse linux bash variables
def parsebashvar( path_bash_script ):
    with open(path_bash_script) as fp:
        data = fp.read()

    data = RE_PREFIX_EXPORT.sub( "", data )

    d0 = {}
    exec( "", d0 )

    d1 = {}
    exec( data, d1 )

    d_diff = { k : d1[k] for k in set(d1) - set(d0) }
    # print (d_diff)
    return d_diff

