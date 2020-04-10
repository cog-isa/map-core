#
# This file is part of pyperplan.
#
# define the set of special characters
whiteSpace = set([' ', '\n', '\t'])
comment = set([';'])
reserved = set([':', ')', '(']).union(comment)
